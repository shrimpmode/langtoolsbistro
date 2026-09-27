"""Tests for passwordless guest sign-in and the mock email service."""
import re
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from chat.models import Conversation
from guests.models import LoginCode, MockEmail
from guests.services import MAX_FAILED_ATTEMPTS, request_login_code, verify_login_code


# Django's test runner swaps EMAIL_BACKEND for its in-memory one; these
# tests are about the mock inbox, so put it back.
use_mock_inbox = override_settings(EMAIL_BACKEND="guests.mock_email.MockInboxBackend")


def _latest_code(email="dana@example.com"):
    """The code from the newest email to `email`, read the way a guest would."""
    subject = MockEmail.objects.filter(to=email).latest("sent_at").subject
    return re.search(r"\d{6}", subject).group()


def _wrong(code):
    return "000000" if code != "000000" else "111111"


@use_mock_inbox
class MockEmailBackendTests(TestCase):
    def test_login_code_email_lands_in_the_mock_inbox(self):
        request_login_code("dana@example.com")

        email = MockEmail.objects.get()
        self.assertEqual(email.to, "dana@example.com")
        self.assertIn(_latest_code(), email.subject)
        self.assertIn(_latest_code(), email.body)


@use_mock_inbox
class VerifyLoginCodeTests(TestCase):
    def test_correct_code_works(self):
        request_login_code("dana@example.com")
        self.assertTrue(verify_login_code("dana@example.com", _latest_code()))

    def test_email_is_case_and_space_insensitive(self):
        request_login_code("  Dana@Example.com ")
        self.assertTrue(verify_login_code("DANA@example.com", _latest_code()))

    def test_code_works_only_once(self):
        request_login_code("dana@example.com")
        code = _latest_code()
        self.assertTrue(verify_login_code("dana@example.com", code))
        self.assertFalse(verify_login_code("dana@example.com", code))

    def test_wrong_code_fails(self):
        request_login_code("dana@example.com")
        self.assertFalse(verify_login_code("dana@example.com", _wrong(_latest_code())))

    def test_code_for_another_email_fails(self):
        request_login_code("dana@example.com")
        self.assertFalse(verify_login_code("sam@example.com", _latest_code()))

    def test_expired_code_fails(self):
        request_login_code("dana@example.com")
        LoginCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertFalse(verify_login_code("dana@example.com", _latest_code()))

    def test_requesting_a_new_code_cancels_the_old_one(self):
        request_login_code("dana@example.com")
        old = _latest_code()
        request_login_code("dana@example.com")
        new = _latest_code()
        if new != old:  # 1-in-a-million chance they match
            self.assertFalse(verify_login_code("dana@example.com", old))
        self.assertTrue(verify_login_code("dana@example.com", new))

    def test_database_holds_only_a_hash_of_the_code(self):
        request_login_code("dana@example.com")
        stored = LoginCode.objects.get().code_hash
        self.assertNotIn(_latest_code(), stored)
        self.assertEqual(len(stored), 64)

    def test_code_stops_working_after_too_many_wrong_guesses(self):
        request_login_code("dana@example.com")
        code = _latest_code()
        for _ in range(MAX_FAILED_ATTEMPTS):
            verify_login_code("dana@example.com", _wrong(code))
        self.assertFalse(verify_login_code("dana@example.com", code))


@use_mock_inbox
class LoginViewTests(TestCase):
    def setUp(self):
        self.conversation = Conversation.objects.create()
        self.kwargs = {"conversation_id": self.conversation.id}

    def _post(self, name, data=None):
        return self.client.post(
            reverse(name, kwargs=self.kwargs), data or {}, content_type="application/json"
        )

    def test_full_sign_in_flow_sets_guest_email_on_conversation(self):
        response = self._post("guest-login-request", {"email": "Dana@example.com"})
        self.assertEqual(response.status_code, 202)

        response = self._post(
            "guest-login-verify", {"email": "dana@example.com", "code": _latest_code()}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["guest_email"], "dana@example.com")
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.guest_email, "dana@example.com")

    def test_wrong_code_is_rejected_and_guest_stays_signed_out(self):
        self._post("guest-login-request", {"email": "dana@example.com"})
        response = self._post(
            "guest-login-verify", {"email": "dana@example.com", "code": _wrong(_latest_code())}
        )

        self.assertEqual(response.status_code, 400)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.guest_email, "")

    def test_invalid_email_is_rejected(self):
        response = self._post("guest-login-request", {"email": "not-an-email"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(MockEmail.objects.exists())

    def test_logout_clears_guest_email(self):
        self.conversation.guest_email = "dana@example.com"
        self.conversation.save()

        response = self._post("guest-logout")

        self.assertEqual(response.data["guest_email"], "")

    def test_unknown_conversation_returns_404(self):
        self.kwargs = {"conversation_id": "00000000-0000-0000-0000-000000000000"}
        response = self._post("guest-login-request", {"email": "dana@example.com"})
        self.assertEqual(response.status_code, 404)


@use_mock_inbox
class MockInboxViewTests(TestCase):
    @override_settings(MOCK_INBOX_ENABLED=True)
    def test_lists_sent_emails_newest_first(self):
        request_login_code("first@example.com")
        request_login_code("second@example.com")

        response = self.client.get(reverse("mock-inbox"))

        self.assertEqual([e["to"] for e in response.data], ["second@example.com", "first@example.com"])

    @override_settings(MOCK_INBOX_ENABLED=False)
    def test_hidden_when_disabled(self):
        response = self.client.get(reverse("mock-inbox"))
        self.assertEqual(response.status_code, 404)
