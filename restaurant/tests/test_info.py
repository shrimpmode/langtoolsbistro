"""Tests for the restaurant's details and live opening status."""
import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from restaurant.info import hours_summary, opening_status

NY = ZoneInfo("America/New_York")


def at(year, month, day, hour, minute=0):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=NY)


class HoursSummaryTests(SimpleTestCase):
    def test_groups_days_with_the_same_hours(self):
        self.assertEqual(hours_summary(), "Tuesday-Sunday, 5:00 PM - 10:00 PM. Closed Mondays.")


class OpeningStatusTests(SimpleTestCase):
    # 2026-10-03 is a Saturday, 2026-10-05 a Monday.

    def test_open_during_service(self):
        status = opening_status(at(2026, 10, 3, 19, 30))
        self.assertEqual(status, {"open_now": True, "closes_at": "22:00", "next_opening": None})

    def test_before_opening_today_opens_later_today(self):
        status = opening_status(at(2026, 10, 3, 12))
        self.assertFalse(status["open_now"])
        self.assertEqual(status["next_opening"], {"date": "2026-10-03", "weekday": "Saturday", "time": "17:00"})

    def test_closing_time_itself_counts_as_closed(self):
        status = opening_status(at(2026, 10, 3, 22))
        self.assertFalse(status["open_now"])
        self.assertEqual(status["next_opening"]["weekday"], "Sunday")

    def test_sunday_night_skips_closed_monday(self):
        status = opening_status(at(2026, 10, 4, 23))
        self.assertEqual(status["next_opening"], {"date": "2026-10-06", "weekday": "Tuesday", "time": "17:00"})

    def test_monday_is_closed_all_day(self):
        status = opening_status(at(2026, 10, 5, 19))
        self.assertFalse(status["open_now"])
        self.assertEqual(status["next_opening"]["weekday"], "Tuesday")


class RestaurantDetailsViewTests(TestCase):
    @patch("restaurant.views.restaurant_now", return_value=at(2026, 10, 5, 19))
    def test_returns_details_hours_and_status(self, _now):
        response = self.client.get(reverse("restaurant-details"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Trattoria Orchai")
        self.assertEqual(response.data["address"], "123 Main Street")
        self.assertEqual(response.data["today"], "Monday")
        self.assertEqual(
            response.data["hours"][0], {"weekday": "Monday", "open": None, "close": None}
        )
        self.assertEqual(
            response.data["hours"][1], {"weekday": "Tuesday", "open": "17:00", "close": "22:00"}
        )
        self.assertFalse(response.data["status"]["open_now"])
