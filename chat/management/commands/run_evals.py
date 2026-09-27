"""Runs the fixed agent eval set against the real Claude API.

This makes real, billed API calls (whatever model ANTHROPIC_MODEL points
at) and is not part of `manage.py test` - it checks the agent's judgment,
not code correctness, so it doesn't belong in a suite that must be fast,
free, and deterministic.

Any DB rows the cases create (menu items, reservations) are rolled back at
the end via an outer transaction, so this is safe to run against a real
database without leaving eval fixtures behind.

Usage:
    python manage.py run_evals
    python manage.py run_evals --case create_reservation_extracts_all_fields
"""
from contextlib import nullcontext
from unittest.mock import patch

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from chat.agent.eval_cases import EVAL_CASES
from chat.agent.orchestrator import run_agent


def _check_tool_input(expected: dict, actual: dict) -> list:
    failures = []
    for key, expectation in expected.items():
        actual_value = actual.get(key)
        if callable(expectation):
            ok = expectation(actual_value)
        else:
            ok = str(actual_value).strip().lower() == str(expectation).strip().lower()
        if not ok:
            failures.append(f"arg {key!r}: expected {expectation!r}, got {actual_value!r}")
    return failures


def _run_case(case) -> tuple:
    """Returns (passed: bool, failures: list[str], reply: str)."""
    if case.setup:
        case.setup()

    pin_now = (
        patch("chat.agent.orchestrator._now", return_value=case.now)
        if case.now
        else nullcontext()
    )
    try:
        with pin_now:
            result = run_agent(case.input, prior_messages=[])
    except Exception as exc:  # noqa: BLE001 - eval harness must not crash on a bad case
        return False, [f"agent raised {type(exc).__name__}: {exc}"], ""

    failures = []
    tool_names = [call["name"] for call in result["tool_calls"]]
    if case.expected_tool is None:
        if tool_names:
            failures.append(f"tool: expected none, got {tool_names!r}")
    elif case.expected_tool not in tool_names:
        failures.append(f"tool: expected {case.expected_tool!r}, got {tool_names!r}")
    else:
        # Check the args of the first call to the expected tool - a turn may
        # also call others (e.g. list_menu before create_reservation).
        call = next(c for c in result["tool_calls"] if c["name"] == case.expected_tool)
        failures.extend(_check_tool_input(case.expected_tool_input, call["args"]))

    reply = result["reply"]
    for substring in case.expected_reply_contains:
        if substring.lower() not in reply.lower():
            failures.append(f"reply missing expected substring {substring!r}")

    return not failures, failures, reply


class Command(BaseCommand):
    help = "Run the agent eval set against the real Claude API (makes billed calls)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--case",
            help="Run only the eval case with this name.",
        )

    def handle(self, *args, **options):
        case_filter = options.get("case")
        cases = EVAL_CASES
        if case_filter:
            cases = [c for c in cases if c.name == case_filter]
            if not cases:
                raise CommandError(f"No eval case named {case_filter!r}")

        passed_count = 0
        failed_names = []

        with transaction.atomic():
            for case in cases:
                passed, failures, reply = _run_case(case)
                if passed:
                    passed_count += 1
                    self.stdout.write(self.style.SUCCESS(f"PASS  {case.name}"))
                else:
                    failed_names.append(case.name)
                    self.stdout.write(self.style.ERROR(f"FAIL  {case.name}"))
                    for failure in failures:
                        self.stdout.write(f"        - {failure}")
                reply_preview = (reply[:100] + "...") if len(reply) > 100 else reply
                self.stdout.write(f"        reply: {reply_preview!r}\n")

            # Nothing this run created (menu items, reservations) should
            # persist - it's an eval run, not real restaurant data.
            transaction.set_rollback(True)

        total = len(cases)
        self.stdout.write(f"\n{passed_count}/{total} passed")

        if failed_names:
            raise CommandError(f"Failed: {', '.join(failed_names)}")
