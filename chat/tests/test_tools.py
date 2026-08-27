"""Unit tests for the LangChain tools the agent can call.

These exercise the tool functions directly against the test database - no
LLM calls involved. That split matters: bugs in tool logic (bad queries, bad
validation) should be caught here, cheaply and deterministically, rather
than only showing up as a confusing agent eval failure.
"""
import datetime

from django.test import TestCase

from chat.agent.tools import check_reservation, create_reservation, list_menu
from restaurant.models import MenuItem, Reservation


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
    def test_creates_reservation_with_valid_input(self):
        result = create_reservation.func(
            customer_name="Alex",
            party_size=4,
            date="2026-09-01",
            time="19:00",
        )
        self.assertIn("Alex", result)
        self.assertIn("party of 4", result)
        reservation = Reservation.objects.get(customer_name="Alex")
        self.assertEqual(reservation.date, datetime.date(2026, 9, 1))
        self.assertEqual(reservation.time, datetime.time(19, 0))
        self.assertEqual(reservation.status, Reservation.Status.CONFIRMED)

    def test_rejects_unparseable_date(self):
        result = create_reservation.func(
            customer_name="Alex",
            party_size=2,
            date="tonight",
            time="19:00",
        )
        self.assertIn("couldn't understand", result)
        self.assertFalse(Reservation.objects.exists())

    def test_rejects_unparseable_time(self):
        result = create_reservation.func(
            customer_name="Alex",
            party_size=2,
            date="2026-09-01",
            time="7pm",
        )
        self.assertIn("couldn't understand", result)
        self.assertFalse(Reservation.objects.exists())


class CheckReservationTests(TestCase):
    def setUp(self):
        Reservation.objects.create(
            customer_name="Priya",
            party_size=2,
            date=datetime.date(2026, 9, 1),
            time=datetime.time(19, 0),
        )

    def test_finds_reservation_by_exact_name(self):
        result = check_reservation.func(customer_name="Priya")
        self.assertIn("party of 2", result)
        self.assertIn("2026-09-01", result)

    def test_lookup_is_case_insensitive(self):
        result = check_reservation.func(customer_name="priya")
        self.assertIn("party of 2", result)

    def test_no_reservation_returns_friendly_message(self):
        result = check_reservation.func(customer_name="Nobody")
        self.assertIn("No reservations found", result)
