"""Fixed eval dataset for the restaurant agent.

Unlike the unit tests in chat/tests/, these hit the real Claude API through
the real agent - they check judgment (did it pick the right tool? did it
extract the right arguments? did it answer directly when it should have),
not just our glue code. Run with `manage.py run_evals`.

Each case's `expected_tool_input` values may be a literal (compared as
case-insensitive strings) or a callable predicate `(actual_value) -> bool`,
for arguments where several correct phrasings exist (e.g. a name embedded
in a longer string).
"""
from dataclasses import dataclass, field
from datetime import date, time
from typing import Any, Callable, Optional

from restaurant.models import MenuItem, Reservation


@dataclass
class EvalCase:
    name: str
    input: str
    expected_tool: Optional[str]  # None means "should answer directly, no tool"
    expected_tool_input: dict = field(default_factory=dict)
    expected_reply_contains: list = field(default_factory=list)  # case-insensitive substrings
    setup: Optional[Callable[[], None]] = None


def _seed_menu():
    MenuItem.objects.create(
        name="Margherita",
        description="Tomato, mozzarella, basil",
        category=MenuItem.Category.MAIN,
        price="14.00",
    )
    MenuItem.objects.create(
        name="Tiramisu",
        description="Espresso-soaked ladyfingers",
        category=MenuItem.Category.DESSERT,
        price="8.00",
    )


def _seed_priya_reservation():
    Reservation.objects.create(
        customer_name="Priya",
        party_size=2,
        date=date(2026, 9, 1),
        time=time(19, 0),
    )


def _contains(needle: str) -> Callable[[Any], bool]:
    return lambda actual: needle.lower() in str(actual).lower()


EVAL_CASES = [
    EvalCase(
        name="menu_full_listing",
        input="What's on the menu?",
        expected_tool="list_menu",
        setup=_seed_menu,
        expected_reply_contains=["margherita", "tiramisu"],
    ),
    EvalCase(
        name="menu_category_filter",
        input="Do you have any desserts?",
        expected_tool="list_menu",
        expected_tool_input={"category": "dessert"},
        setup=_seed_menu,
        expected_reply_contains=["tiramisu"],
    ),
    EvalCase(
        name="create_reservation_extracts_all_fields",
        input="Book a table for 4 people on 2026-09-01 at 7pm under the name Priya.",
        expected_tool="create_reservation",
        expected_tool_input={
            "party_size": "4",
            "date": "2026-09-01",
            "time": "19:00",
            "customer_name": _contains("priya"),
        },
        expected_reply_contains=["priya", "4"],
    ),
    EvalCase(
        name="check_reservation_by_name",
        input="Do I have a table booked under the name Priya?",
        expected_tool="check_reservation",
        expected_tool_input={"customer_name": _contains("priya")},
        setup=_seed_priya_reservation,
        expected_reply_contains=["priya"],
    ),
    EvalCase(
        name="hours_answered_directly",
        input="What time do you close?",
        expected_tool=None,
        expected_reply_contains=["10"],
    ),
    EvalCase(
        name="location_answered_directly",
        input="What's your address?",
        expected_tool=None,
        expected_reply_contains=["main street"],
    ),
    EvalCase(
        name="small_talk_answered_directly",
        input="Hi there, how's it going?",
        expected_tool=None,
    ),
    EvalCase(
        name="invalid_party_size_does_not_crash",
        input="Book a table for -1 people called Bob on 2026-09-01 at 19:00.",
        expected_tool=None,
    ),
]
