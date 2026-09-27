import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    messages_from_dict,
    messages_to_dict,
)

from .tools import TOOLS

SYSTEM_PROMPT = """You are the front-of-house assistant for Trattoria Orchai, \
a small Italian restaurant.

Restaurant facts you can answer directly, without using a tool:
- Hours: Tuesday-Sunday, 5:00 PM - 10:00 PM. Closed Mondays.
- Location: 123 Main Street.
- We take walk-ins, but reservations are recommended on weekends.

Use your tools when the guest wants to see the menu, book a table, or check \
an existing reservation. For anything else (hours, location, general \
questions, small talk), just answer directly. Keep replies short and \
friendly, like a real host would speak."""


def _now() -> datetime.datetime:
    """The current time in the restaurant's own time zone.

    Its own function so tests (and evals) can pin "now" with a patch.
    """
    return timezone.now().astimezone(ZoneInfo(settings.RESTAURANT_TIME_ZONE))


def build_system_prompt(now: datetime.datetime) -> str:
    """SYSTEM_PROMPT plus the current date and time.

    Without this the model has no idea what day it is, so "tomorrow" or
    "this Friday" get resolved against whatever date it guesses - usually
    one from its training data. Day-of-week is included too, since that's
    how guests talk ("next Tuesday") and how our hours are written.
    """
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Right now it is {now:%A, %B %-d, %Y, %H:%M} restaurant time "
        f"(today's date is {now:%Y-%m-%d}). Use this to turn relative dates "
        f'like "tonight", "tomorrow", or "next Friday" into exact dates.'
    )


@dynamic_prompt
def _system_prompt_with_current_time(request: ModelRequest) -> str:
    """Middleware that rebuilds the system prompt on every model call.

    A plain `system_prompt=` string is fixed when the agent is built - and
    the agent is built once per process - so it would freeze the date at
    server start. dynamic_prompt runs just before each model call instead.
    """
    return build_system_prompt(_now())


_agent = None


def _get_agent():
    """Build the agent once and reuse it across turns.

    Unlike the old AgentExecutor, a create_agent graph holds no per-turn
    state of its own - all of that lives in the messages list passed to
    invoke()/astream_events() - so it's safe to build once and share across
    requests instead of reconstructing it every call.
    """
    global _agent
    if _agent is None:
        llm = ChatAnthropic(
            model=settings.ANTHROPIC_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
        )
        _agent = create_agent(
            model=llm,
            tools=TOOLS,
            middleware=[_system_prompt_with_current_time],
        )
    return _agent


def _history_to_messages(messages):
    """Rebuild the LangChain message list from persisted Message rows.

    Assistant rows saved with turn_messages are replayed in full - including
    the AIMessage that requested each tool and the ToolMessage holding its
    result - so on a follow-up like "book the second one" the model can
    still see the menu list_menu returned last turn. Rows from before
    turn_messages existed fall back to just their final text.
    """
    history = []
    for msg in messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        elif msg.turn_messages:
            history.extend(messages_from_dict(msg.turn_messages))
        else:
            history.append(AIMessage(content=msg.content))
    return history


def _summarize_turn(new_messages) -> dict:
    """Turn the messages the agent appended this turn into what we persist.

    Shared by run_agent and stream_agent_reply so both paths agree on what
    "the reply" and "the tools used" were for a given turn.
    """
    tool_calls = [
        {"name": call["name"], "args": call["args"]}
        for msg in new_messages
        for call in getattr(msg, "tool_calls", None) or []
    ]
    return {
        # Claude Opus 5 thinks by default, so content is often a block list
        # (thinking, text, ...) rather than a string - .text keeps only the
        # text blocks.
        "reply": new_messages[-1].text,
        "tool_calls": tool_calls,
        "turn_messages": messages_to_dict(new_messages),
    }


def run_agent(user_input: str, prior_messages) -> dict:
    """Run the LangChain agent for one turn.

    Returns a dict with the assistant's reply text, every tool it called
    (`[{"name", "args"}]`, empty if it answered directly), and the turn's
    full serialized message sequence for the caller to persist.
    """
    agent = _get_agent()
    input_messages = [*_history_to_messages(prior_messages), HumanMessage(content=user_input)]

    result = agent.invoke({"messages": input_messages})

    # Everything at or after this index is new this turn - input_messages is
    # itself a prefix of result["messages"], since create_agent appends
    # rather than replacing.
    return _summarize_turn(result["messages"][len(input_messages):])


async def stream_agent_reply(user_input: str, prior_messages):
    """Run the agent for one turn, yielding incremental events as they occur.

    Yields dicts of the form {"type": "token" | "tool_start" | "done", ...}.
    A "done" event is always yielded last, with the same shape run_agent
    returns (reply/tool_calls/turn_messages), for the caller to persist.

    Every generated token is streamed live as it arrives, including a "let
    me check that for you" preamble the model writes before deciding to call
    a tool - once a token has gone out over SSE there's no taking it back,
    so this doesn't try to guess in advance whether the current turn will
    end up calling a tool.

    The *persisted* reply is decided at the end instead, from the graph's
    final state: the root run's on_chain_end event carries the same
    messages list agent.invoke() would have returned, so it goes through
    the same _summarize_turn as run_agent. The reply is therefore only the
    final AIMessage's text - a tool-decision preamble is real-time flavor
    text, not part of the answer (though it is kept in turn_messages, since
    it's part of what the model actually said).
    """
    agent = _get_agent()
    input_messages = [*_history_to_messages(prior_messages), HumanMessage(content=user_input)]

    final_state = None

    async for event in agent.astream_events({"messages": input_messages}, version="v2"):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            # .text keeps only text blocks, so thinking and tool_use deltas
            # never reach the client.
            text = event["data"]["chunk"].text
            if text:
                yield {"type": "token", "text": text}

        elif kind == "on_tool_start":
            yield {"type": "tool_start", "tool": event["name"]}

        elif kind == "on_chain_end" and not event["parent_ids"]:
            # No parent means this is the whole agent graph finishing, not
            # one of its nodes - its output is the final agent state.
            final_state = event["data"]["output"]

    if final_state is None:
        raise RuntimeError("Agent stream ended without a final state")

    yield {
        "type": "done",
        **_summarize_turn(final_state["messages"][len(input_messages):]),
    }
