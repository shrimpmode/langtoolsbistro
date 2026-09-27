"""Passwordless guest sign-in: email a one-time code, then check it."""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import LoginCode

CODE_LIFETIME = timedelta(minutes=10)
MAX_FAILED_ATTEMPTS = 5


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_login_code(email: str, code: str) -> str:
    """HMAC-SHA256 of the code, keyed with SECRET_KEY and bound to the email.

    A keyed hash rather than a slow password hash: with only a million
    possible codes, a plain SHA-256 could be reversed by trying them all,
    but without the key there's nothing to try them against. Expiry and
    the attempt limit cover guessing through the API itself.
    """
    message = f"{normalize_email(email)}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def request_login_code(email: str) -> None:
    """Email a fresh code to `email`, replacing any earlier unused one."""
    email = normalize_email(email)
    now = timezone.now()
    LoginCode.objects.filter(email=email, used_at__isnull=True).update(used_at=now)
    code = f"{secrets.randbelow(1_000_000):06d}"
    LoginCode.objects.create(
        email=email, code_hash=hash_login_code(email, code), expires_at=now + CODE_LIFETIME
    )

    send_mail(
        subject=f"Your Trattoria Orchai sign-in code: {code}",
        message=(
            f"Your sign-in code is {code}.\n\n"
            f"It expires in {int(CODE_LIFETIME.total_seconds() // 60)} minutes. "
            "If you didn't ask for it, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


def verify_login_code(email: str, code: str) -> bool:
    """True if `code` is the current, unexpired code for `email`.

    A correct code works once. Each wrong guess counts against the code,
    and after MAX_FAILED_ATTEMPTS it stops working even if guessed right,
    so the 1-in-a-million odds can't be brute-forced.
    """
    email = normalize_email(email)
    login_code = (
        LoginCode.objects.filter(
            email=email, used_at__isnull=True, expires_at__gt=timezone.now()
        )
        .order_by("-created_at")
        .first()
    )
    if login_code is None or login_code.failed_attempts >= MAX_FAILED_ATTEMPTS:
        return False

    if not hmac.compare_digest(hash_login_code(email, code.strip()), login_code.code_hash):
        login_code.failed_attempts += 1
        login_code.save(update_fields=["failed_attempts"])
        return False

    login_code.used_at = timezone.now()
    login_code.save(update_fields=["used_at"])
    return True
