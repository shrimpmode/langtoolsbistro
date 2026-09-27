"""API-level tests for the chat endpoints.

run_agent is mocked here - these test persistence and HTTP contract
(status codes, payload shape, ordering), not agent behavior.
"""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from chat.models import Conversation, Message


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
        mock_run_agent.return_value = {
            "reply": "We're open 5-10pm Tuesday-Sunday.",
            "tool_calls": [],
            "turn_messages": [],
        }

        response = self.client.post(
            self.url, {"content": "What are your hours?"}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["content"], "We're open 5-10pm Tuesday-Sunday.")
        self.assertEqual(response.data["tool_calls"], [])

        messages = list(self.conversation.messages.all())
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, Message.Role.USER)
        self.assertEqual(messages[0].content, "What are your hours?")
        self.assertEqual(messages[1].role, Message.Role.ASSISTANT)

    @patch("chat.views.run_agent")
    def test_tool_calls_and_turn_are_recorded_on_the_assistant_message(self, mock_run_agent):
        tool_calls = [
            {"name": "list_menu", "args": {}},
            {"name": "create_reservation", "args": {"customer_name": "Alex"}},
        ]
        turn_messages = [{"type": "ai", "data": {"content": "Booked!"}}]
        mock_run_agent.return_value = {
            "reply": "Booked!",
            "tool_calls": tool_calls,
            "turn_messages": turn_messages,
        }

        response = self.client.post(
            self.url, {"content": "Book a table for 2"}, content_type="application/json"
        )

        assistant_message = self.conversation.messages.get(role=Message.Role.ASSISTANT)
        self.assertEqual(assistant_message.tool_calls, tool_calls)
        self.assertEqual(assistant_message.turn_messages, turn_messages)
        self.assertEqual(response.data["tool_calls"], tool_calls)
        # turn_messages is internal replay state (it can include the model's
        # thinking blocks) - it shouldn't leak out over the API.
        self.assertNotIn("turn_messages", response.data)

    @patch("chat.views.run_agent")
    def test_run_agent_receives_prior_messages_before_the_new_one_is_saved(
        self, mock_run_agent
    ):
        mock_run_agent.return_value = {"reply": "ok", "tool_calls": [], "turn_messages": []}
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

    @patch("chat.views.run_agent")
    def test_run_agent_receives_the_conversations_signed_in_guest(self, mock_run_agent):
        mock_run_agent.return_value = {"reply": "ok", "tool_calls": [], "turn_messages": []}
        self.conversation.guest_email = "dana@example.com"
        self.conversation.save()

        self.client.post(self.url, {"content": "my bookings?"}, content_type="application/json")

        self.assertEqual(mock_run_agent.call_args[0][2], "dana@example.com")

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
