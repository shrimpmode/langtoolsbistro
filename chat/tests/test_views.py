"""API-level tests for the chat endpoints.

run_agent is mocked here - these test persistence and HTTP contract
(status codes, payload shape, ordering), not agent behavior.
"""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from chat.models import AgentRun, Conversation, Message


def _agent_result(**overrides):
    result = {
        "reply": "ok",
        "tool_used": "",
        "tool_input": {},
        "tool_calls": [],
        "model_call_count": 1,
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
        "estimated_cost_usd": 0.0001,
        "latency_ms": 42,
        "model": "claude-haiku-4-5",
        "error": None,
    }
    result.update(overrides)
    return result


class ConversationCreateViewTests(TestCase):
    def test_creates_conversation(self):
        response = self.client.post(reverse("conversation-create"))
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.data)
        self.assertTrue(Conversation.objects.filter(id=response.data["id"]).exists())


class MessageListCreateViewTests(TestCase):
    def setUp(self):
        self.conversation = Conversation.objects.create()
        self.url = reverse(
            "message-list-create", kwargs={"conversation_id": self.conversation.id}
        )

    @patch("chat.views.run_agent")
    def test_posting_a_message_persists_both_turns(self, mock_run_agent):
        mock_run_agent.return_value = _agent_result(
            reply="We're open 5-10pm Tuesday-Sunday."
        )

        response = self.client.post(
            self.url, {"content": "What are your hours?"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["content"], "We're open 5-10pm Tuesday-Sunday.")
        self.assertEqual(response.data["tool_used"], "")

        messages = list(self.conversation.messages.all())
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, Message.Role.USER)
        self.assertEqual(messages[0].content, "What are your hours?")
        self.assertEqual(messages[1].role, Message.Role.ASSISTANT)

    @patch("chat.views.run_agent")
    def test_tool_used_is_recorded_on_the_assistant_message(self, mock_run_agent):
        mock_run_agent.return_value = _agent_result(
            reply="Booked!",
            tool_used="create_reservation",
            tool_input={"customer_name": "Alex"},
            tool_calls=[{"name": "create_reservation", "args": {"customer_name": "Alex"}}],
        )

        self.client.post(
            self.url, {"content": "Book a table for 2"}, content_type="application/json"
        )

        assistant_message = self.conversation.messages.get(role=Message.Role.ASSISTANT)
        self.assertEqual(assistant_message.tool_used, "create_reservation")

    @patch("chat.views.run_agent")
    def test_run_agent_receives_prior_messages_before_the_new_one_is_saved(
        self, mock_run_agent
    ):
        mock_run_agent.return_value = _agent_result()
        Message.objects.create(
            conversation=self.conversation, role=Message.Role.USER, content="hi"
        )
        Message.objects.create(
            conversation=self.conversation, role=Message.Role.ASSISTANT, content="hello"
        )

        self.client.post(
            self.url, {"content": "second question"}, content_type="application/json"
        )

        prior_messages_arg = mock_run_agent.call_args[0][1]
        self.assertEqual(len(prior_messages_arg), 2)

    def test_empty_content_is_rejected(self):
        response = self.client.post(
            self.url, {"content": ""}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_conversation_returns_404(self):
        bad_url = reverse(
            "message-list-create",
            kwargs={"conversation_id": "00000000-0000-0000-0000-000000000000"},
        )
        response = self.client.post(
            bad_url, {"content": "hi"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

    @patch("chat.views.run_agent")
    def test_get_lists_messages_in_order(self, mock_run_agent):
        Message.objects.create(
            conversation=self.conversation, role=Message.Role.USER, content="first"
        )
        Message.objects.create(
            conversation=self.conversation, role=Message.Role.ASSISTANT, content="second"
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([m["content"] for m in response.data], ["first", "second"])
        mock_run_agent.assert_not_called()

    @patch("chat.views.run_agent")
    def test_agent_run_is_logged_on_success(self, mock_run_agent):
        mock_run_agent.return_value = _agent_result(
            reply="Booked!",
            tool_used="create_reservation",
            tool_calls=[{"name": "create_reservation", "args": {}}],
            model_call_count=2,
            input_tokens=100,
            output_tokens=40,
            total_tokens=140,
            estimated_cost_usd=0.00034,
            latency_ms=812,
        )

        self.client.post(
            self.url, {"content": "Book a table for 2"}, content_type="application/json"
        )

        run = AgentRun.objects.get()
        self.assertEqual(run.status, AgentRun.Status.OK)
        self.assertEqual(run.conversation, self.conversation)
        self.assertEqual(run.user_message.content, "Book a table for 2")
        self.assertEqual(run.assistant_message.content, "Booked!")
        self.assertEqual(run.model_call_count, 2)
        self.assertEqual(run.total_tokens, 140)
        self.assertEqual(run.tool_calls, [{"name": "create_reservation", "args": {}}])
        self.assertEqual(run.error_message, "")

    @patch("chat.views.run_agent")
    def test_agent_error_logs_run_and_returns_502_without_assistant_message(
        self, mock_run_agent
    ):
        mock_run_agent.return_value = _agent_result(error="authentication_error: bad key")

        response = self.client.post(
            self.url, {"content": "What's on the menu?"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 502)
        self.assertFalse(
            self.conversation.messages.filter(role=Message.Role.ASSISTANT).exists()
        )

        run = AgentRun.objects.get()
        self.assertEqual(run.status, AgentRun.Status.ERROR)
        self.assertEqual(run.error_message, "authentication_error: bad key")
        self.assertIsNone(run.assistant_message)
