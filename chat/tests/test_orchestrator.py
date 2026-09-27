"""Unit tests for the agent wiring in orchestrator.py.

These mock the LangChain agent entirely, so they run with no network access
and no Anthropic API key - they test our glue code (history conversion,
result unpacking), not Claude's behavior. Whether the agent actually picks
the right tool for a given message is what the evals in
chat/agent/eval_cases.py + `manage.py run_evals` check instead.
"""
import datetime
import json
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    ToolMessage,
    messages_to_dict,
)

from chat.agent.tools import GuestContext
from chat.agent.orchestrator import (
    _history_to_messages,
    build_system_prompt,
    run_agent,
    stream_agent_reply,
)


def _menu_then_book_turn():
    """The messages an agent appends for a turn that calls two tools."""
    return [
        AIMessage(
            content="Let me check.",
            tool_calls=[
                {"name": "list_menu", "args": {"category": "dessert"}, "id": "call_1"},
                {"name": "create_reservation", "args": {"customer_name": "Alex"}, "id": "call_2"},
            ],
        ),
        ToolMessage(content="- Tiramisu ($8.00)", tool_call_id="call_1"),
        ToolMessage(content="Reservation confirmed (#7).", tool_call_id="call_2"),
        AIMessage(content="Booked! We have Tiramisu for dessert.", tool_calls=[]),
    ]


class BuildSystemPromptTests(SimpleTestCase):
    def test_includes_weekday_date_and_time(self):
        now = datetime.datetime(2026, 9, 26, 18, 30, tzinfo=ZoneInfo("America/New_York"))

        prompt = build_system_prompt(now)

        self.assertIn("Saturday, September 26, 2026, 18:30", prompt)
        self.assertIn("2026-09-26", prompt)
        self.assertIn("Trattoria Orchai", prompt)

    def test_says_when_guest_is_signed_in(self):
        now = datetime.datetime(2026, 9, 26, 18, 30, tzinfo=ZoneInfo("America/New_York"))

        self.assertIn("signed in as dana@example.com", build_system_prompt(now, "dana@example.com"))
        self.assertIn("not signed in", build_system_prompt(now))


class HistoryToMessagesTests(SimpleTestCase):
    def test_converts_roles_in_order(self):
        history = [
            MagicMock(role="user", content="hi"),
            MagicMock(role="assistant", content="hello", turn_messages=[]),
        ]
        result = _history_to_messages(history)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], HumanMessage)
        self.assertEqual(result[0].content, "hi")
        self.assertIsInstance(result[1], AIMessage)
        self.assertEqual(result[1].content, "hello")

    def test_empty_history(self):
        self.assertEqual(_history_to_messages([]), [])

    def test_assistant_turn_messages_are_replayed_in_full(self):
        turn = _menu_then_book_turn()
        history = [
            MagicMock(role="user", content="desserts, and book me in"),
            MagicMock(
                role="assistant",
                content="Booked! We have Tiramisu for dessert.",
                turn_messages=messages_to_dict(turn),
            ),
        ]

        result = _history_to_messages(history)

        self.assertEqual(
            [type(m) for m in result],
            [HumanMessage, AIMessage, ToolMessage, ToolMessage, AIMessage],
        )
        self.assertEqual(result[1].tool_calls[0]["name"], "list_menu")
        self.assertEqual(result[2].content, "- Tiramisu ($8.00)")

    def test_assistant_row_without_turn_messages_falls_back_to_text(self):
        # Rows saved before turn_messages existed.
        history = [MagicMock(role="assistant", content="hello", turn_messages=[])]

        result = _history_to_messages(history)

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], AIMessage)
        self.assertEqual(result[0].content, "hello")


class RunAgentTests(SimpleTestCase):
    @patch("chat.agent.orchestrator._get_agent")
    def test_direct_answer_has_no_tool(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="What are your hours?"),
                AIMessage(content="We're open Tuesday-Sunday, 5-10pm.", tool_calls=[]),
            ]
        }
        mock_get_agent.return_value = mock_agent

        result = run_agent("What are your hours?", [])

        self.assertEqual(result["reply"], "We're open Tuesday-Sunday, 5-10pm.")
        self.assertEqual(result["tool_calls"], [])

    @patch("chat.agent.orchestrator._get_agent")
    def test_reply_keeps_only_text_blocks(self, mock_get_agent):
        # Claude Opus 5 thinks by default, so the final AIMessage's content
        # can be a block list instead of a plain string.
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="What are your hours?"),
                AIMessage(
                    content=[
                        {"type": "thinking", "thinking": "the user wants hours"},
                        {"type": "text", "text": "We're open "},
                        {"type": "text", "text": "5-10pm."},
                    ],
                    tool_calls=[],
                ),
            ]
        }
        mock_get_agent.return_value = mock_agent

        result = run_agent("What are your hours?", [])

        self.assertEqual(result["reply"], "We're open 5-10pm.")

    @patch("chat.agent.orchestrator._get_agent")
    def test_tool_call_is_surfaced(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="Any desserts?"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "list_menu", "args": {"category": "dessert"}, "id": "call_1"}
                    ],
                ),
                ToolMessage(content="Tiramisu", tool_call_id="call_1"),
                AIMessage(content="Here's our dessert menu: Tiramisu.", tool_calls=[]),
            ]
        }
        mock_get_agent.return_value = mock_agent

        result = run_agent("Any desserts?", [])

        self.assertEqual(
            result["tool_calls"],
            [{"name": "list_menu", "args": {"category": "dessert"}, "artifact": None}],
        )

    @patch("chat.agent.orchestrator._get_agent")
    def test_every_tool_call_is_recorded_not_just_the_first(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [HumanMessage(content="desserts, and book me in"), *_menu_then_book_turn()]
        }
        mock_get_agent.return_value = mock_agent

        result = run_agent("desserts, and book me in", [])

        self.assertEqual(
            [call["name"] for call in result["tool_calls"]],
            ["list_menu", "create_reservation"],
        )
        self.assertEqual(result["reply"], "Booked! We have Tiramisu for dessert.")

    @patch("chat.agent.orchestrator._get_agent")
    def test_turn_messages_exclude_history_and_are_json_serializable(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [HumanMessage(content="desserts, and book me in"), *_menu_then_book_turn()]
        }
        mock_get_agent.return_value = mock_agent

        result = run_agent("desserts, and book me in", [])

        # They go into a JSONField, so they must survive a JSON round trip.
        self.assertEqual(json.loads(json.dumps(result["turn_messages"])), result["turn_messages"])
        self.assertEqual(
            [m["type"] for m in result["turn_messages"]], ["ai", "tool", "tool", "ai"]
        )

    @patch("chat.agent.orchestrator._get_agent")
    def test_passes_converted_history_and_input_to_agent(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="hi"),
                HumanMessage(content="follow-up"),
                AIMessage(content="ok", tool_calls=[]),
            ]
        }
        mock_get_agent.return_value = mock_agent
        prior = [MagicMock(role="user", content="hi")]

        run_agent("follow-up", prior)

        call_kwargs = mock_agent.invoke.call_args[0][0]
        messages = call_kwargs["messages"]
        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[0], HumanMessage)
        self.assertEqual(messages[0].content, "hi")
        self.assertEqual(messages[1].content, "follow-up")


class ToolArtifactTests(SimpleTestCase):
    @patch("chat.agent.orchestrator._get_agent")
    def test_each_tool_call_gets_its_own_artifact_by_tool_call_id(self, mock_get_agent):
        card = {"kind": "reservation_created", "reservations": [{"code": "K7Q-4MX"}]}
        turn = [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "list_menu", "args": {}, "id": "call_1"},
                    {"name": "create_reservation", "args": {}, "id": "call_2"},
                ],
            ),
            # Results deliberately out of order: matching is by id, not position.
            ToolMessage(content="Booked", tool_call_id="call_2", artifact=card),
            ToolMessage(content="- Tiramisu", tool_call_id="call_1"),
            AIMessage(content="Done!"),
        ]
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {"messages": [HumanMessage(content="hi"), *turn]}
        mock_get_agent.return_value = mock_agent

        result = run_agent("hi", [])

        self.assertEqual(
            [(c["name"], c["artifact"]) for c in result["tool_calls"]],
            [("list_menu", None), ("create_reservation", card)],
        )


class RunAgentContextTests(SimpleTestCase):
    @patch("chat.agent.orchestrator._get_agent")
    def test_signed_in_guest_is_passed_as_runtime_context(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = {
            "messages": [HumanMessage(content="my bookings?"), AIMessage(content="ok")]
        }
        mock_get_agent.return_value = mock_agent

        run_agent("my bookings?", [], guest_email="dana@example.com")

        self.assertEqual(
            mock_agent.invoke.call_args.kwargs["context"],
            GuestContext(guest_email="dana@example.com"),
        )


class StreamAgentReplyTests(SimpleTestCase):
    """Feeds stream_agent_reply a hand-written astream_events sequence, in
    the shape LangGraph emits it, rather than a real model."""

    @staticmethod
    def _collect(user_input, prior, guest_email=""):
        async def run():
            return [
                event async for event in stream_agent_reply(user_input, prior, guest_email)
            ]

        return async_to_sync(run)()

    @patch("chat.agent.orchestrator._get_agent")
    def test_streams_tokens_and_tools_then_done_matches_final_state(self, mock_get_agent):
        user_input = "desserts, and book me in"
        final_messages = [HumanMessage(content=user_input), *_menu_then_book_turn()]

        def chunk(content):
            return {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(content=content)}, "parent_ids": ["root"]}

        async def fake_events(*args, **kwargs):
            # A thinking delta - must never be streamed to the client.
            yield chunk([{"type": "thinking", "thinking": "they want dessert", "index": 0}])
            yield chunk("Let me check.")
            yield {"event": "on_tool_start", "name": "list_menu", "data": {}, "parent_ids": ["root"]}
            yield {"event": "on_tool_start", "name": "create_reservation", "data": {}, "parent_ids": ["root"]}
            yield chunk("Booked! ")
            yield chunk("We have Tiramisu for dessert.")
            # A node finishing - has a parent, so must be ignored.
            yield {"event": "on_chain_end", "name": "model", "data": {"output": {"messages": []}}, "parent_ids": ["root"]}
            yield {"event": "on_chain_end", "name": "LangGraph", "data": {"output": {"messages": final_messages}}, "parent_ids": []}

        mock_agent = MagicMock()
        mock_agent.astream_events = fake_events
        mock_get_agent.return_value = mock_agent

        events = self._collect(user_input, [])

        self.assertEqual(
            [e["type"] for e in events],
            ["token", "tool_start", "tool_start", "token", "token", "done"],
        )
        done = events[-1]
        # The "Let me check." preamble streamed live but isn't the reply.
        self.assertEqual(done["reply"], "Booked! We have Tiramisu for dessert.")
        self.assertEqual(
            [call["name"] for call in done["tool_calls"]], ["list_menu", "create_reservation"]
        )
        self.assertEqual(len(done["turn_messages"]), 4)

    @patch("chat.agent.orchestrator._get_agent")
    def test_signed_in_guest_is_passed_as_runtime_context(self, mock_get_agent):
        seen = {}
        final = [HumanMessage(content="my bookings?"), AIMessage(content="ok")]

        async def fake_events(*args, **kwargs):
            seen.update(kwargs)
            yield {"event": "on_chain_end", "name": "LangGraph", "data": {"output": {"messages": final}}, "parent_ids": []}

        mock_agent = MagicMock()
        mock_agent.astream_events = fake_events
        mock_get_agent.return_value = mock_agent

        self._collect("my bookings?", [], guest_email="dana@example.com")

        self.assertEqual(seen["context"], GuestContext(guest_email="dana@example.com"))

    @patch("chat.agent.orchestrator._get_agent")
    def test_tool_end_event_carries_the_artifact(self, mock_get_agent):
        card = {"kind": "reservation_list", "reservations": []}
        final = [HumanMessage(content="hi"), AIMessage(content="ok")]

        async def fake_events(*args, **kwargs):
            yield {
                "event": "on_tool_end",
                "name": "check_reservation",
                "data": {"output": ToolMessage(content="x", tool_call_id="c1", artifact=card)},
                "parent_ids": ["root"],
            }
            yield {"event": "on_chain_end", "name": "LangGraph", "data": {"output": {"messages": final}}, "parent_ids": []}

        mock_agent = MagicMock()
        mock_agent.astream_events = fake_events
        mock_get_agent.return_value = mock_agent

        events = self._collect("hi", [])

        self.assertEqual(
            events[0], {"type": "tool_end", "tool": "check_reservation", "artifact": card}
        )
