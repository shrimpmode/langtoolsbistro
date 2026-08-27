"""Unit tests for the agent wiring in orchestrator.py.

These mock the LangChain AgentExecutor entirely, so they run with no
network access and no Anthropic API key - they test our glue code
(history conversion, result unpacking), not Claude's behavior. Whether the
agent actually picks the right tool for a given message is what the evals
in chat/agent/eval_cases.py + `manage.py run_evals` check instead.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from langchain_core.messages import AIMessage, HumanMessage

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
        # Claude Opus 5 thinks by default, so LangChain's tool-calling output
        # parser can hand back the raw block list instead of a plain string.
        output = [
            {"type": "thinking", "thinking": "the user wants hours"},
            {"type": "text", "text": "We're open 5-10pm."},
        ]
        self.assertEqual(_extract_reply_text(output), "We're open 5-10pm.")

    def test_multiple_text_blocks_are_concatenated(self):
        output = [{"type": "text", "text": "Part one. "}, {"type": "text", "text": "Part two."}]
        self.assertEqual(_extract_reply_text(output), "Part one. Part two.")


class RunAgentTests(SimpleTestCase):
    @patch("chat.agent.orchestrator._build_agent_executor")
    def test_direct_answer_has_no_tool(self, mock_build):
        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {
            "output": "We're open Tuesday-Sunday, 5-10pm.",
            "intermediate_steps": [],
        }
        mock_build.return_value = mock_executor

        result = run_agent("What are your hours?", [])

        self.assertEqual(result["reply"], "We're open Tuesday-Sunday, 5-10pm.")
        self.assertEqual(result["tool_used"], "")
        self.assertEqual(result["tool_input"], {})

    @patch("chat.agent.orchestrator._build_agent_executor")
    def test_tool_call_is_surfaced(self, mock_build):
        fake_action = MagicMock(tool="list_menu", tool_input={"category": "dessert"})
        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {
            "output": "Here's our dessert menu: Tiramisu.",
            "intermediate_steps": [(fake_action, "Tiramisu")],
        }
        mock_build.return_value = mock_executor

        result = run_agent("Any desserts?", [])

        self.assertEqual(result["tool_used"], "list_menu")
        self.assertEqual(result["tool_input"], {"category": "dessert"})

    @patch("chat.agent.orchestrator._build_agent_executor")
    def test_passes_converted_history_and_input_to_executor(self, mock_build):
        mock_executor = MagicMock()
        mock_executor.invoke.return_value = {"output": "ok", "intermediate_steps": []}
        mock_build.return_value = mock_executor
        prior = [MagicMock(role="user", content="hi")]

        run_agent("follow-up", prior)

        call_kwargs = mock_executor.invoke.call_args[0][0]
        self.assertEqual(call_kwargs["input"], "follow-up")
        self.assertEqual(len(call_kwargs["chat_history"]), 1)
        self.assertIsInstance(call_kwargs["chat_history"][0], HumanMessage)
