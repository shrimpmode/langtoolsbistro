"""The restaurant's own details, in one place.

Both the landing page (GET /api/restaurant/) and the agent's system prompt
read from here, so the hours a guest sees on the page can't drift from the
hours the assistant quotes.
"""
import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

NAME = "Trattoria Orchai"
TAGLINE = "A small Italian restaurant on Main Street."
ADDRESS = "123 Main Street"
WALK_INS = "We take walk-ins, but reservations are recommended on weekends."

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_DINNER = (datetime.time(17, 0), datetime.time(22, 0))

# Keyed by datetime.weekday() (Monday is 0). None means closed all day.
OPENING_HOURS: dict[int, tuple[datetime.time, datetime.time] | None] = {
    0: None,
    1: _DINNER,
    2: _DINNER,
    3: _DINNER,
    4: _DINNER,
    5: _DINNER,
    6: _DINNER,
}


def restaurant_now() -> datetime.datetime:
    """The current time in the restaurant's own time zone."""
    return timezone.now().astimezone(ZoneInfo(settings.RESTAURANT_TIME_ZONE))


def _format_time(t: datetime.time) -> str:
    return t.strftime("%-I:%M %p")


def hours_summary() -> str:
    """Hours as one line, e.g. "Tuesday-Sunday, 5:00 PM - 10:00 PM. Closed Mondays."

    Groups consecutive days with the same hours, so it stays correct if the
    table above changes.
    """
    groups: list[tuple[int, int, tuple | None]] = []
    for day in range(7):
        hours = OPENING_HOURS[day]
        if groups and groups[-1][2] == hours:
            groups[-1] = (groups[-1][0], day, hours)
        else:
            groups.append((day, day, hours))

    open_parts, closed_days = [], []
    for first, last, hours in groups:
        days = WEEKDAYS[first] if first == last else f"{WEEKDAYS[first]}-{WEEKDAYS[last]}"
        if hours is None:
            closed_days.append(days)
        else:
            open_parts.append(f"{days}, {_format_time(hours[0])} - {_format_time(hours[1])}")

    summary = "; ".join(open_parts) + "."
    if closed_days:
        summary += " Closed " + ", ".join(f"{d}s" for d in closed_days) + "."
    return summary


def opening_status(now: datetime.datetime) -> dict:
    """Whether the restaurant is open at `now`, and when that changes.

    Returns {"open_now": bool, "closes_at": "HH:MM" or None,
    "next_opening": {"date", "weekday", "time"} or None}. `next_opening` is
    set only while closed.
    """
    today = OPENING_HOURS[now.weekday()]
    if today and today[0] <= now.time() < today[1]:
        return {"open_now": True, "closes_at": today[1].strftime("%H:%M"), "next_opening": None}

    for days_ahead in range(0, 8):
        day = now.date() + datetime.timedelta(days=days_ahead)
        hours = OPENING_HOURS[day.weekday()]
        # Later today counts only if it hasn't opened yet.
        if hours and (days_ahead > 0 or now.time() < hours[0]):
            return {
                "open_now": False,
                "closes_at": None,
                "next_opening": {
                    "date": day.isoformat(),
                    "weekday": WEEKDAYS[day.weekday()],
                    "time": hours[0].strftime("%H:%M"),
                },
            }
    return {"open_now": False, "closes_at": None, "next_opening": None}


def restaurant_details(now: datetime.datetime) -> dict:
    """Everything the landing page shows about the restaurant."""
    return {
        "name": NAME,
        "tagline": TAGLINE,
        "address": ADDRESS,
        "walk_ins": WALK_INS,
        "hours": [
            {
                "weekday": WEEKDAYS[day],
                "open": hours[0].strftime("%H:%M") if hours else None,
                "close": hours[1].strftime("%H:%M") if hours else None,
            }
            for day, hours in OPENING_HOURS.items()
        ],
        "today": WEEKDAYS[now.weekday()],
        "status": opening_status(now),
    }
