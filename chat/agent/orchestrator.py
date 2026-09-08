import time

from django.conf import settings
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage

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
        _agent = create_agent(model=llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
    return _agent


def _extract_reply_text(output) -> str:
    """Normalize the agent's final message content to plain text.

    Claude Opus 5 thinks by default, so a turn's final AIMessage often has
    non-string content: a list of blocks (thinking, text, ...) instead of a
    single string.
    """
    if isinstance(output, str):
        return output
    parts = []
    for block in output:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block["text"])
    return "".join(parts)


def _collect_tool_calls(messages) -> list:
    """Every tool call made across a list of messages, in order.

    Unlike the single tool_used/tool_input orchai has always surfaced (the
    *first* tool call), this keeps all of them - needed to monitor turns
    where the model calls more than one tool.
    """
    calls = []
    for msg in messages:
        for call in getattr(msg, "tool_calls", None) or []:
            calls.append({"name": call["name"], "args": call["args"]})
    return calls


def _sum_token_usage(messages) -> tuple[int, int, int]:
    """Sum usage_metadata (input/output/total tokens) across messages.

    Only AIMessages carry usage_metadata, and only when the provider
    reports it (Anthropic does) - getattr defaults protect against both
    the attribute being absent and it being None.
    """
    input_tokens = output_tokens = total_tokens = 0
    for msg in messages:
        usage = getattr(msg, "usage_metadata", None)
        if not usage:
            continue
        input_tokens += usage.get("input_tokens", 0)
        output_tokens += usage.get("output_tokens", 0)
        total_tokens += usage.get("total_tokens", 0)
    return input_tokens, output_tokens, total_tokens


def _estimate_cost_usd(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from settings.ANTHROPIC_PRICING. 0.0 for an unknown
    model rather than guessing - see the settings.py comment on that table.
    """
    rates = settings.ANTHROPIC_PRICING.get(model_name)
    if not rates:
        return 0.0
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


def _history_to_messages(messages):
    history = []
    for msg in messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))
    return history


def run_agent(user_input: str, prior_messages) -> dict:
    """Run the LangChain agent for one turn.

    Returns a dict with the assistant's reply text; the name/input of the
    first tool it invoked (empty if it answered directly); and monitoring
    data for chat.AgentRun - every tool call made, the number of LLM calls
    this turn took (workflow steps), token usage, an estimated cost,
    latency, and (on failure) an error message instead of a raised
    exception, so the caller can always log a row.
    """
    agent = _get_agent()
    input_messages = [*_history_to_messages(prior_messages), HumanMessage(content=user_input)]
    model_name = settings.ANTHROPIC_MODEL
    started = time.monotonic()

    try:
        result = agent.invoke({"messages": input_messages})
    except Exception as exc:
        return {
            "reply": "",
            "tool_used": "",
            "tool_input": {},
            "tool_calls": [],
            "model_call_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "latency_ms": round((time.monotonic() - started) * 1000),
            "model": model_name,
            "error": str(exc),
        }

    latency_ms = round((time.monotonic() - started) * 1000)

    # Everything at or after this index is new this turn - input_messages is
    # itself a prefix of result["messages"], since create_agent appends
    # rather than replacing.
    new_messages = result["messages"][len(input_messages):]

    tool_calls = _collect_tool_calls(new_messages)
    tool_used = tool_calls[0]["name"] if tool_calls else ""
    tool_input = tool_calls[0]["args"] if tool_calls else {}
    model_call_count = sum(1 for msg in new_messages if isinstance(msg, AIMessage))
    input_tokens, output_tokens, total_tokens = _sum_token_usage(new_messages)

    reply = _extract_reply_text(result["messages"][-1].content)

    return {
        "reply": reply,
        "tool_used": tool_used,
        "tool_input": tool_input,
        "tool_calls": tool_calls,
        "model_call_count": model_call_count,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": _estimate_cost_usd(model_name, input_tokens, output_tokens),
        "latency_ms": latency_ms,
        "model": model_name,
        "error": None,
    }


def _text_from_chunk_content(content) -> str:
    """Pull visible text out of one streamed AIMessageChunk's `.content`.

    Anthropic streams content as a list of typed blocks (text, tool_use,
    and - when the model thinks - thinking), so this filters to `text`
    blocks only. That also protects against ever streaming a thinking
    block's contents to the client.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


async def stream_agent_reply(user_input: str, prior_messages):
    """Run the agent for one turn, yielding incremental events as they occur.

    Yields dicts of the form {"type": "token" | "tool_start" | "done", ...}.
    A "done" event is always yielded last, with the same monitoring shape
    run_agent returns (reply/tool_used/tool_input/tool_calls/
    model_call_count/token usage/cost/latency/model/error), for the caller
    to persist - including on failure, where "error" is set instead of the
    generator raising, so a row can still be logged.

    Every generated token is streamed live as it arrives, including a "let
    me check that for you" preamble the model writes before deciding to call
    a tool - once a token has gone out over SSE there's no taking it back,
    so this doesn't try to guess in advance whether the current turn will
    end up calling a tool.

    What DOES get filtered is the *persisted* reply (the "done" event, and
    what the caller saves to the DB): only text from a model call whose
    final message has no tool_calls counts as the model's actual answer -
    which is decided retroactively at on_chat_model_end, matching what
    run_agent's last message would have contained. A tool-decision preamble
    is real-time flavor text, not part of the answer, and dropping it here
    keeps the streamed and non-streamed code paths agreeing on what "the
    reply" was for a given turn.
    """
    agent = _get_agent()
    input_messages = [*_history_to_messages(prior_messages), HumanMessage(content=user_input)]
    model_name = settings.ANTHROPIC_MODEL
    started = time.monotonic()

    tool_used = ""
    tool_input = {}
    tool_calls = []
    turn_buffer = []
    final_reply_parts = []
    model_call_count = 0
    input_tokens = output_tokens = total_tokens = 0

    def done_event(error=None):
        return {
            "type": "done",
            "reply": "".join(final_reply_parts),
            "tool_used": tool_used,
            "tool_input": tool_input,
            "tool_calls": tool_calls,
            "model_call_count": model_call_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": _estimate_cost_usd(model_name, input_tokens, output_tokens),
            "latency_ms": round((time.monotonic() - started) * 1000),
            "model": model_name,
            "error": error,
        }

    try:
        async for event in agent.astream_events({"messages": input_messages}, version="v2"):
            kind = event["event"]

            if kind == "on_chat_model_start":
                turn_buffer = []
                model_call_count += 1

            elif kind == "on_chat_model_stream":
                text = _text_from_chunk_content(event["data"]["chunk"].content)
                if text:
                    turn_buffer.append(text)
                    yield {"type": "token", "text": text}

            elif kind == "on_chat_model_end":
                output = event["data"]["output"]
                if not output.tool_calls:
                    final_reply_parts.extend(turn_buffer)
                usage = getattr(output, "usage_metadata", None)
                if usage:
                    input_tokens += usage.get("input_tokens", 0)
                    output_tokens += usage.get("output_tokens", 0)
                    total_tokens += usage.get("total_tokens", 0)

            elif kind == "on_tool_start":
                name = event["name"]
                args = event["data"].get("input", {})
                tool_used = name
                tool_input = args
                tool_calls.append({"name": name, "args": args})
                yield {"type": "tool_start", "tool": name}
    except Exception as exc:
        yield done_event(error=str(exc))
        return

    yield done_event()
