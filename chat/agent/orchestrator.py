from django.conf import settings
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

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


def _build_agent_executor() -> AgentExecutor:
    llm = ChatAnthropic(
        model=settings.ANTHROPIC_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=TOOLS, return_intermediate_steps=True)


def _extract_reply_text(output) -> str:
    """Normalize the agent's final output to plain text.

    Claude Opus 5 thinks by default, so a turn's underlying AIMessage often
    has non-string content: a list of blocks (thinking, text, ...) instead
    of a single string. LangChain's tool-calling output parser passes that
    list straight through as `output`, so we can't assume it's a string.
    """
    if isinstance(output, str):
        return output
    parts = []
    for block in output:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block["text"])
    return "".join(parts)


def _history_to_messages(messages):
    history = []
    for msg in messages:
        if msg.role == "user":
            history.append(HumanMessage(content=msg.content))
        else:
            history.append(AIMessage(content=msg.content))
    return history


def run_agent(user_input: str, prior_messages) -> dict:
    """Run the LangChain tool-calling agent for one turn.

    Returns a dict with the assistant's reply text, the name of the tool it
    invoked (empty string if it answered directly), and the input passed to
    that tool (empty dict if none).
    """
    executor = _build_agent_executor()
    chat_history = _history_to_messages(prior_messages)

    result = executor.invoke({"input": user_input, "chat_history": chat_history})

    tool_used = ""
    tool_input = {}
    intermediate_steps = result.get("intermediate_steps", [])
    if intermediate_steps:
        first_action, _ = intermediate_steps[0]
        tool_used = first_action.tool
        tool_input = first_action.tool_input

    reply = _extract_reply_text(result["output"])

    return {"reply": reply, "tool_used": tool_used, "tool_input": tool_input}


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
    A "done" event is always yielded last, with the same shape run_agent
    returns (reply/tool_used/tool_input), for the caller to persist.

    Every generated token is streamed live as it arrives, including a "let
    me check that for you" preamble the model writes before deciding to call
    a tool - once a token has gone out over SSE there's no taking it back,
    so this doesn't try to guess in advance whether the current turn will
    end up calling a tool.

    What DOES get filtered is the *persisted* reply (the "done" event, and
    what the caller saves to the DB): only text from a turn whose final
    message has no tool_calls counts as the model's actual answer - which
    is decided retroactively at on_chat_model_end, matching what
    run_agent's non-streaming AgentFinish output would have contained. A
    tool-decision preamble is real-time flavor text, not part of the
    answer, and dropping it here keeps the streamed and non-streamed code
    paths agreeing on what "the reply" was for a given turn.
    """
    executor = _build_agent_executor()
    chat_history = _history_to_messages(prior_messages)

    tool_used = ""
    tool_input = {}
    turn_buffer = []
    final_reply_parts = []

    async for event in executor.astream_events(
        {"input": user_input, "chat_history": chat_history}, version="v2"
    ):
        kind = event["event"]

        if kind == "on_chat_model_start":
            turn_buffer = []

        elif kind == "on_chat_model_stream":
            text = _text_from_chunk_content(event["data"]["chunk"].content)
            if text:
                turn_buffer.append(text)
                yield {"type": "token", "text": text}

        elif kind == "on_chat_model_end":
            if not event["data"]["output"].tool_calls:
                final_reply_parts.extend(turn_buffer)

        elif kind == "on_tool_start":
            tool_used = event["name"]
            tool_input = event["data"].get("input", {})
            yield {"type": "tool_start", "tool": tool_used}

    yield {
        "type": "done",
        "reply": "".join(final_reply_parts),
        "tool_used": tool_used,
        "tool_input": tool_input,
    }
