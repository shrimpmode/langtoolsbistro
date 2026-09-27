from django.db import models


class LoginCode(models.Model):
    """A one-time code emailed to a guest to prove they own that address.

    Only an HMAC of the code is stored (see guests.services.hash_login_code),
    so reading the database doesn't give anyone a working code - they'd also
    need the SECRET_KEY. The code itself exists only in the email.
    """

    email = models.EmailField()
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"{self.email} ({self.created_at:%Y-%m-%d %H:%M})"


class MockEmail(models.Model):
    """An email the mock email backend "sent". See guests/mock_email.py."""

    to = models.TextField()  # comma-separated, as the recipients were given
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.subject} -> {self.to}"
