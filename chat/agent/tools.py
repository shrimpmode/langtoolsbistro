import datetime
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.utils import DataError
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from restaurant.models import (
    MenuItem,
    Reservation,
    format_confirmation_code,
    normalize_confirmation_code,
)


@dataclass
class GuestContext:
    """Per-request facts the server knows and the model must not be able to change.

    Passed as `context=` when the agent runs, and read by tools through
    their `runtime` parameter. LangChain hides `runtime` from the model's
    view of the tool, so there's no argument it could fill in to pretend
    to be someone else.
    """

    guest_email: str = ""  # verified via an emailed code; "" if not signed in


@tool
def list_menu(category: str = "") -> str:
    """List items on the restaurant menu.

    Args:
        category: Optional filter — one of "appetizer", "main", "dessert",
            "drink". Leave empty to list the full menu.
    """
    qs = MenuItem.objects.filter(is_available=True)
    if category:
        qs = qs.filter(category=category.lower().strip())
    items = list(qs.order_by("category", "name"))
    if not items:
        return "No menu items found for that category."
    lines = [f"- {i.name} (${i.price}): {i.description}" for i in items]
    return "\n".join(lines)


@tool
def create_reservation(
    customer_name: str,
    party_size: int,
    date: str,
    time: str,
    runtime: ToolRuntime[GuestContext],
    contact_email: str = "",
) -> str:
    """Book a table reservation at the restaurant.

    Args:
        customer_name: Name the reservation should be booked under.
        party_size: Number of guests.
        date: Reservation date in YYYY-MM-DD format.
        time: Reservation time in 24-hour HH:MM format.
        contact_email: The guest's email address. Not needed if the guest is
            signed in - their verified email is used instead.
    """
    email = runtime.context.guest_email or contact_email.strip().lower()
    if not email:
        return (
            "No booking made: I need the guest's email address first (or they "
            "can sign in). Ask them for it, then try again."
        )
    try:
        validate_email(email)
    except ValidationError:
        return f"No booking made: {email!r} isn't a valid email address. Ask the guest to check it."

    try:
        parsed_date = datetime.date.fromisoformat(date)
        parsed_time = datetime.time.fromisoformat(time)
    except ValueError:
        return (
            "I couldn't understand that date/time. Please provide the date as "
            "YYYY-MM-DD and the time as HH:MM (24-hour)."
        )

    try:
        reservation = Reservation.objects.create(
            customer_name=customer_name,
            contact_email=email,
            party_size=party_size,
            date=parsed_date,
            time=parsed_time,
        )
    except DataError:
        return "I couldn't create that reservation — please double-check the details."

    return (
        f"Reservation confirmed for {reservation.customer_name}, "
        f"party of {reservation.party_size}, on {reservation.date} "
        f"at {reservation.time.strftime('%H:%M')}. Confirmation code: "
        f"{format_confirmation_code(reservation.confirmation_code)}. Give the "
        "guest this code - they need it to look the booking up later."
    )


@tool
def check_reservation(
    runtime: ToolRuntime[GuestContext],
    confirmation_code: str = "",
) -> str:
    """Look up the guest's existing reservations.

    If the guest is signed in, returns all bookings made with their email
    and no code is needed. Otherwise, it needs the confirmation code they
    were given when they booked.

    Args:
        confirmation_code: The booking's confirmation code, e.g. "K7Q-4MX".
            Leave empty if the guest is signed in.
    """
    # Access is decided here, from server-side facts - not by the model.
    # A name alone is never enough: anyone can type any name.
    guest_email = runtime.context.guest_email
    code = normalize_confirmation_code(confirmation_code)
    if guest_email:
        reservations = Reservation.objects.filter(contact_email__iexact=guest_email)
        if code:
            reservations = reservations.filter(confirmation_code=code)
        not_found = f"No reservations found for {guest_email}."
    elif code:
        reservations = Reservation.objects.filter(confirmation_code=code)
        not_found = "No reservation matches that confirmation code. Ask the guest to check it."
    else:
        return (
            "Can't look up bookings yet: the guest isn't signed in and gave no "
            "confirmation code. Ask for the code from their booking, or suggest "
            "they sign in with their email."
        )

    reservations = reservations.order_by("-date", "-time")
    if not reservations.exists():
        return not_found

    lines = [
        f"- {format_confirmation_code(r.confirmation_code)}: {r.customer_name}, "
        f"party of {r.party_size} on {r.date} at {r.time.strftime('%H:%M')} "
        f"({r.get_status_display()})"
        for r in reservations
    ]
    return "\n".join(lines)


TOOLS = [list_menu, create_reservation, check_reservation]
