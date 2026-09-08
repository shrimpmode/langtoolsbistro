"""Unit tests for the agent wiring in orchestrator.py.

These mock the LangChain agent entirely, so they run with no network access
and no Anthropic API key - they test our glue code (history conversion,
result unpacking), not Claude's behavior. Whether the agent actually picks
the right tool for a given message is what the evals in
chat/agent/eval_cases.py + `manage.py run_evals` check instead.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from chat.agent.orchestrator import _extract_reply_text, _history_to_messages, run_agent


class HistoryToMessagesTests(SimpleTestCase):
    def test_converts_roles_in_order(self):
        history = [
            MagicMock(role="user", content="hi"),
            MagicMock(role="assistant", content="hello"),
        ]
        result = _history_to_messages(history)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], HumanMessage)
        self.assertEqual(result[0].content, "hi")
        self.assertIsInstance(result[1], AIMessage)
        self.assertEqual(result[1].content, "hello")

    def test_empty_history(self):
        self.assertEqual(_history_to_messages([]), [])


class ExtractReplyTextTests(SimpleTestCase):
    def test_plain_string_output_is_returned_as_is(self):
        self.assertEqual(_extract_reply_text("Hello there"), "Hello there")

    def test_content_block_list_is_flattened_to_text(self):
        # Claude Opus 5 thinks by default, so the final AIMessage's content
        # can be the raw block list instead of a plain string.
        output = [
            {"type": "thinking", "thinking": "the user wants hours"},
            {"type": "text", "text": "We're open 5-10pm."},
        ]
        self.assertEqual(_extract_reply_text(output), "We're open 5-10pm.")

    def test_multiple_text_blocks_are_concatenated(self):
        output = [{"type": "text", "text": "Part one. "}, {"type": "text", "text": "Part two."}]
        self.assertEqual(_extract_reply_text(output), "Part one. Part two.")


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
        self.assertEqual(result["tool_used"], "")
        self.assertEqual(result["tool_input"], {})

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

        self.assertEqual(result["tool_used"], "list_menu")
        self.assertEqual(result["tool_input"], {"category": "dessert"})

    @patch("chat.agent.orchestrator._get_agent")
    def test_reports_model_call_count_and_token_usage(self, mock_get_agent):
        mock_agent = MagicMock()
        tool_call_message = AIMessage(
            content="",
            tool_calls=[{"name": "list_menu", "args": {}, "id": "call_1"}],
            usage_metadata={"input_tokens": 50, "output_tokens": 10, "total_tokens": 60},
        )
        final_message = AIMessage(
            content="Here you go.",
            tool_calls=[],
            usage_metadata={"input_tokens": 70, "output_tokens": 20, "total_tokens": 90},
        )
        mock_agent.invoke.return_value = {
            "messages": [
                HumanMessage(content="Any desserts?"),
                tool_call_message,
                ToolMessage(content="Tiramisu", tool_call_id="call_1"),
                final_message,
            ]
        }
        mock_get_agent.return_value = mock_agent

        result = run_agent("Any desserts?", [])

        self.assertEqual(result["model_call_count"], 2)
        self.assertEqual(result["input_tokens"], 120)
        self.assertEqual(result["output_tokens"], 30)
        self.assertEqual(result["total_tokens"], 150)
        self.assertEqual(result["tool_calls"], [{"name": "list_menu", "args": {}}])
        self.assertIsNone(result["error"])

    @patch("chat.agent.orchestrator._get_agent")
    def test_agent_exception_is_returned_as_an_error_result_not_raised(self, mock_get_agent):
        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = RuntimeError("upstream is down")
        mock_get_agent.return_value = mock_agent

        result = run_agent("Any desserts?", [])

        self.assertEqual(result["error"], "upstream is down")
        self.assertEqual(result["reply"], "")
        self.assertEqual(result["model_call_count"], 0)
        self.assertGreaterEqual(result["latency_ms"], 0)

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
