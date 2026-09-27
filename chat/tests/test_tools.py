"""Unit tests for the LangChain tools the agent can call.

These exercise the tool functions directly against the test database - no
LLM calls involved. That split matters: bugs in tool logic (bad queries, bad
validation) should be caught here, cheaply and deterministically, rather
than only showing up as a confusing agent eval failure.
"""
import datetime
from types import SimpleNamespace

from django.test import TestCase

from chat.agent.tools import GuestContext, check_reservation, create_reservation, list_menu
from restaurant.models import MenuItem, Reservation


def _runtime(guest_email=""):
    """Stand-in for the ToolRuntime LangChain injects; tools only read .context."""
    return SimpleNamespace(context=GuestContext(guest_email=guest_email))


class ListMenuTests(TestCase):
    def setUp(self):
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
        MenuItem.objects.create(
            name="Burnt Special",
            description="Not available",
            category=MenuItem.Category.MAIN,
            price="99.00",
            is_available=False,
        )

    def test_lists_all_available_items(self):
        result = list_menu.func()
        self.assertIn("Margherita", result)
        self.assertIn("Tiramisu", result)
        self.assertNotIn("Burnt Special", result)

    def test_filters_by_category(self):
        result = list_menu.func(category="dessert")
        self.assertIn("Tiramisu", result)
        self.assertNotIn("Margherita", result)

    def test_category_filter_is_case_and_space_insensitive(self):
        result = list_menu.func(category=" Dessert ")
        self.assertIn("Tiramisu", result)

    def test_no_matches_returns_friendly_message(self):
        result = list_menu.func(category="drink")
        self.assertIn("No menu items found", result)


class CreateReservationTests(TestCase):
    def _book(self, runtime=None, **overrides):
        kwargs = dict(
            customer_name="Alex",
            party_size=4,
            date="2026-09-01",
            time="19:00",
            contact_email="alex@example.com",
        )
        kwargs.update(overrides)
        return create_reservation.func(runtime=runtime or _runtime(), **kwargs)

    def test_creates_reservation_with_valid_input(self):
        result = self._book()
        self.assertIn("Alex", result)
        self.assertIn("party of 4", result)
        reservation = Reservation.objects.get(customer_name="Alex")
        self.assertEqual(reservation.date, datetime.date(2026, 9, 1))
        self.assertEqual(reservation.time, datetime.time(19, 0))
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)
        self.assertEqual(reservation.contact_email, "alex@example.com")

    def test_reply_includes_formatted_confirmation_code(self):
        result = self._book()
        code = Reservation.objects.get().confirmation_code
        self.assertIn(f"{code[:3]}-{code[3:]}", result)

    def test_each_reservation_gets_a_different_code(self):
        self._book()
        self._book()
        codes = set(Reservation.objects.values_list("confirmation_code", flat=True))
        self.assertEqual(len(codes), 2)

    def test_refuses_without_an_email(self):
        result = self._book(contact_email="")
        self.assertIn("No booking made", result)
        self.assertFalse(Reservation.objects.exists())

    def test_refuses_an_invalid_email(self):
        result = self._book(contact_email="not-an-email")
        self.assertIn("isn't a valid email", result)
        self.assertFalse(Reservation.objects.exists())

    def test_signed_in_guest_email_wins_over_one_the_model_passes(self):
        # The model can't book on someone else's behalf by passing their email.
        self._book(runtime=_runtime("guest@example.com"), contact_email="other@example.com")
        self.assertEqual(Reservation.objects.get().contact_email, "guest@example.com")

    def test_signed_in_guest_needs_no_email_argument(self):
        self._book(runtime=_runtime("guest@example.com"), contact_email="")
        self.assertEqual(Reservation.objects.get().contact_email, "guest@example.com")

    def test_rejects_unparseable_date(self):
        result = self._book(date="tonight")
        self.assertIn("couldn't understand", result)
        self.assertFalse(Reservation.objects.exists())

    def test_rejects_unparseable_time(self):
        result = self._book(time="7pm")
        self.assertIn("couldn't understand", result)
        self.assertFalse(Reservation.objects.exists())


class CheckReservationTests(TestCase):
    def setUp(self):
        self.priya = Reservation.objects.create(
            customer_name="Priya",
            contact_email="priya@example.com",
            confirmation_code="K7Q4MX",
            party_size=2,
            date=datetime.date(2026, 9, 1),
            time=datetime.time(19, 0),
        )
        Reservation.objects.create(
            customer_name="Sam",
            contact_email="sam@example.com",
            confirmation_code="ZZZ222",
            party_size=6,
            date=datetime.date(2026, 9, 2),
            time=datetime.time(20, 0),
        )

    def test_refuses_without_sign_in_or_code(self):
        result = check_reservation.func(runtime=_runtime())
        self.assertIn("Can't look up bookings", result)
        self.assertNotIn("Priya", result)

    def test_finds_reservation_by_code(self):
        result = check_reservation.func(runtime=_runtime(), confirmation_code="K7Q4MX")
        self.assertIn("Priya", result)
        self.assertIn("2026-09-01", result)
        self.assertNotIn("Sam", result)

    def test_code_is_forgiving_about_case_and_dashes(self):
        result = check_reservation.func(runtime=_runtime(), confirmation_code=" k7q-4mx ")
        self.assertIn("Priya", result)

    def test_wrong_code_finds_nothing(self):
        result = check_reservation.func(runtime=_runtime(), confirmation_code="AAA-AAA")
        self.assertIn("No reservation matches", result)

    def test_signed_in_guest_sees_only_their_own_bookings(self):
        result = check_reservation.func(runtime=_runtime("priya@example.com"))
        self.assertIn("K7Q-4MX", result)
        self.assertNotIn("Sam", result)

    def test_signed_in_guest_cannot_use_someone_elses_code(self):
        result = check_reservation.func(
            runtime=_runtime("priya@example.com"), confirmation_code="ZZZ222"
        )
        self.assertNotIn("Sam", result)
        self.assertIn("No reservations found", result)

    def test_signed_in_guest_with_no_bookings(self):
        result = check_reservation.func(runtime=_runtime("new@example.com"))
        self.assertIn("No reservations found", result)
