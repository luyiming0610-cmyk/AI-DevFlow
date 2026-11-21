
"""Independent supplemental B11 tests.

Not included in Planner, Developer or Repair prompts.
Executed only inside the isolated Docker tester.
"""

import importlib.util
import os
import sys
from pathlib import Path


CANDIDATE = Path(
    os.environ["AI_DEVFLOW_CANDIDATE"]
).resolve()

spec = importlib.util.spec_from_file_location(
    "b11_holdout_candidate",
    CANDIDATE,
)

if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load {CANDIDATE}")

app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)


def line(
    date="2026-11-20",
    time="09:00:00",
    level="INFO",
    event="race_01",
    action="upload_success",
):
    return (
        f"{date} {time} "
        f"{level} {event} {action}"
    )


def test_leap_day_and_date_boundaries():
    assert app.parse_line(
        line(date="2024-02-29")
    ) is not None

    for value in (
        "2025-02-29",
        "2026-04-31",
        "0000-01-01",
    ):
        assert app.parse_line(
            line(date=value)
        ) is None


def test_time_boundaries():
    for value in ("00:00:00", "23:59:59"):
        assert app.parse_line(
            line(time=value)
        ) is not None

    for value in (
        "24:00:00",
        "23:60:00",
        "23:59:60",
        "9:00:00",
    ):
        assert app.parse_line(
            line(time=value)
        ) is None


def test_case_sensitive_levels_and_actions():
    examples = (
        ("info", "upload_success"),
        ("INFO", "Upload_Success"),
        ("ERROR", "upload_success"),
        ("INFO", "upload_timeout"),
    )

    for level, action in examples:
        assert app.parse_line(
            line(level=level, action=action)
        ) is None


def test_event_id_allowlist():
    for event in ("EVT_01", "race-2", "A3"):
        assert app.parse_line(
            line(event=event)
        ) is not None

    for event in (
        "event/001",
        "event.01",
        "赛事01",
    ):
        assert app.parse_line(
            line(event=event)
        ) is None


def test_unknown_failures_are_not_counted():
    examples = [
        line(level="ERROR", action=action)
        for action in (
            "unknown_action",
            "upload_failed:",
            "upload_success",
        )
    ]

    result = app.analyze_logs(examples)

    assert result["valid_records"] == 0
    assert result["invalid_records"] == 3
    assert result["failure_count"] == 0


def test_multievent_reconciliation():
    examples = [
        line(event="race_01"),
        line(
            level="ERROR",
            event="race_01",
            action="upload_failed:Timeout",
        ),
        line(event="race_02"),
        line(
            level="ERROR",
            event="race_02",
            action="connection_failed",
        ),
        line(date="2026-99-99"),
        "bad log",
    ]

    result = app.analyze_logs(examples)

    assert result["total_lines"] == 6
    assert result["valid_records"] == 4
    assert result["invalid_records"] == 2

    assert result["success_count"] == 2
    assert result["failure_count"] == 2

    assert result["failure_by_type"] == {
        "timeout": 1,
        "connection_failed": 1,
    }

    assert result["failure_by_event"] == {
        "race_01": 1,
        "race_02": 1,
    }

    assert result["records_by_event"] == {
        "race_01": 2,
        "race_02": 2,
    }


def test_error_details_keep_source_positions():
    result = app.analyze_logs([
        "bad log",
        line(),
        line(date="2026/11/20"),
    ])

    assert (
        result["format_errors"][0]["line_number"]
        == 1
    )

    assert (
        result["format_errors"][0]["raw_line"]
        == "bad log"
    )

    assert (
        result["invalid_dates"][0]["line_number"]
        == 3
    )

    assert (
        result["invalid_dates"][0]["raw_line"]
        == line(date="2026/11/20")
    )

    assert result["format_errors"][0]["reason"]


def test_both_error_detail_caps_are_independent():
    examples = (
        [line(date="2026-99-99")] * 1002
        + ["bad log"] * 1003
    )

    result = app.analyze_logs(examples)

    assert result["total_lines"] == 2005
    assert result["invalid_records"] == 2005

    assert len(result["invalid_dates"]) == 1000
    assert result["invalid_dates_omitted"] == 2

    assert len(result["format_errors"]) == 1000
    assert result["format_errors_omitted"] == 3


def test_generator_and_text_entry_agree():
    examples = [
        line(),
        line(
            level="ERROR",
            action="upload_timeout",
        ),
    ]

    direct = app.analyze_logs(
        item for item in examples
    )

    via_text = app.analyze_text(
        "\n".join(examples)
    )

    assert direct == via_text


def test_invalid_bytes_do_not_crash():
    result = app.analyze_logs([
        b"\xff",
        line(),
    ])

    assert result["total_lines"] == 2
    assert result["valid_records"] == 1
    assert result["invalid_records"] == 1

    assert len(result["format_errors"]) == 1


def test_crlf_text_has_no_phantom_extra_line():
    result = app.analyze_logs(
        line()
        + "\r\n"
        + line(event="race_02")
        + "\r\n"
    )

    assert result["total_lines"] == 2
    assert result["valid_records"] == 2


def test_determinism_and_count_invariants():
    examples = [
        line(),
        line(
            level="ERROR",
            action="connection_failed",
        ),
        "invalid",
    ]

    result = app.analyze_logs(examples)

    assert result == app.analyze_logs(examples)

    assert (
        result["total_lines"]
        == result["valid_records"]
        + result["invalid_records"]
    )

    assert (
        result["valid_records"]
        == result["success_count"]
        + result["failure_count"]
    )

    assert (
        sum(result["failure_by_type"].values())
        == result["failure_count"]
    )

    assert (
        sum(result["failure_by_event"].values())
        == result["failure_count"]
    )

    assert (
        sum(result["records_by_event"].values())
        == result["valid_records"]
    )
