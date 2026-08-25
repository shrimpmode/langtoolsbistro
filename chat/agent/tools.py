import datetime

from django.db.utils import DataError
from langchain_core.tools import tool

from restaurant.models import MenuItem, Reservation


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
    customer_name: str, party_size: int, date: str, time: str
) -> str:
    """Book a table reservation at the restaurant.

    Args:
        customer_name: Name the reservation should be booked under.
        party_size: Number of guests.
        date: Reservation date in YYYY-MM-DD format.
        time: Reservation time in 24-hour HH:MM format.
    """
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
            party_size=party_size,
            date=parsed_date,
            time=parsed_time,
        )
    except DataError:
        return "I couldn't create that reservation — please double-check the details."

    return (
        f"Reservation confirmed for {reservation.customer_name}, "
        f"party of {reservation.party_size}, on {reservation.date} "
        f"at {reservation.time.strftime('%H:%M')} (confirmation #{reservation.id})."
    )


@tool
def check_reservation(customer_name: str) -> str:
    """Look up existing reservations for a customer by name.

    Args:
        customer_name: The name the reservation was booked under.
    """
    reservations = Reservation.objects.filter(
        customer_name__iexact=customer_name.strip()
    ).order_by("-date", "-time")
    if not reservations.exists():
        return f"No reservations found for {customer_name}."

    lines = [
        f"- #{r.id}: party of {r.party_size} on {r.date} at "
        f"{r.time.strftime('%H:%M')} ({r.get_status_display()})"
        for r in reservations
    ]
    return "\n".join(lines)


TOOLS = [list_menu, create_reservation, check_reservation]
