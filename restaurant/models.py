import secrets

from django.db import models

# No 0/O or 1/I/L, so a code read out over the phone can't be misheard.
CONFIRMATION_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CONFIRMATION_CODE_LENGTH = 6


def generate_confirmation_code() -> str:
    """A random booking code like "K7Q4MX" (shown to guests as "K7Q-4MX").

    Random rather than the row id, since the code is what proves a guest may
    see a booking - sequential ids (#7, #8, ...) would be trivial to guess.
    """
    return "".join(
        secrets.choice(CONFIRMATION_CODE_ALPHABET) for _ in range(CONFIRMATION_CODE_LENGTH)
    )


def normalize_confirmation_code(code: str) -> str:
    """Accept "k7q-4mx", "K7Q 4MX", etc. - guests won't type it exactly."""
    return "".join(ch for ch in code.upper() if ch.isalnum())


def format_confirmation_code(code: str) -> str:
    return f"{code[:3]}-{code[3:]}"


class MenuItem(models.Model):
    class Category(models.TextChoices):
        APPETIZER = "appetizer", "Appetizer"
        MAIN = "main", "Main"
        DESSERT = "dessert", "Dessert"
        DRINK = "drink", "Drink"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Reservation(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    customer_name = models.CharField(max_length=200)
    contact_email = models.EmailField(blank=True, default="")
    confirmation_code = models.CharField(
        max_length=CONFIRMATION_CODE_LENGTH,
        unique=True,
        default=generate_confirmation_code,
        editable=False,
    )
    party_size = models.PositiveIntegerField()
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.CONFIRMED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} ({self.party_size}) on {self.date} {self.time}"
