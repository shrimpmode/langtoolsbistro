"""A fake email service for development.

Set as EMAIL_BACKEND, it stores each outgoing email as a MockEmail row
instead of sending it, and the UI's "mock inbox" panel reads them back. The
login code never learns emails are fake - it calls Django's normal
send_mail() - so switching to a real provider later is a settings change
(EMAIL_BACKEND + SMTP credentials), not a code change.
"""
from django.core.mail.backends.base import BaseEmailBackend


class MockInboxBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        from .models import MockEmail  # apps aren't ready when backends are imported

        for message in email_messages:
            MockEmail.objects.create(
                to=", ".join(message.to),
                subject=message.subject,
                body=message.body,
            )
        return len(email_messages)
