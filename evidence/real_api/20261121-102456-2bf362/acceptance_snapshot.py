
import importlib.util
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = Path(
    os.environ.get(
        "AI_DEVFLOW_CANDIDATE",
        str(ROOT / "workspace" / "generated" / "analyzer.py"),
    )
).resolve()

if not MODULE_PATH.is_file():
    raise FileNotFoundError(
        f"找不到待测试代码：{MODULE_PATH}"
    )

spec = importlib.util.spec_from_file_location(
    "candidate_analyzer",
    MODULE_PATH,
)

if spec is None or spec.loader is None:
    raise ImportError("无法加载候选代码")

analyzer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analyzer
spec.loader.exec_module(analyzer)


def test_parse_success():
    line = (
        "2026-11-20 09:01:12 "
        "INFO event_001 upload_success"
    )

    result = analyzer.parse_line(line)

    assert result is not None
    assert result["kind"] == "success"
    assert result["event_id"] == "event_001"


def test_parse_failure():
    line = (
        "2026-11-20 09:02:15 "
        "ERROR event_001 upload_timeout"
    )

    result = analyzer.parse_line(line)

    assert result is not None
    assert result["kind"] == "failure"
    assert result["failure_type"] == "upload_timeout"


def test_parse_failure_with_reason():
    line = (
        "2026-11-20 09:02:15 "
        "ERROR event_001 upload_failed:Timeout"
    )

    result = analyzer.parse_line(line)

    assert result is not None
    assert result["failure_type"] == "timeout"


def test_unknown_action_rejected():
    line = (
        "2026-11-20 09:02:15 "
        "ERROR event_001 unknown_action"
    )

    assert analyzer.parse_line(line) is None


def test_upload_statistics():
    logs = [
        "2026-11-20 09:01:12 INFO event_001 upload_success",
        "2026-11-20 09:02:15 ERROR event_001 upload_timeout",
        "2026-11-20 09:03:21 ERROR event_002 connection_failed",
        "2026-11-20 09:04:10 INFO event_002 upload_success",
    ]

    result = analyzer.analyze_logs(logs)

    assert result["total_lines"] == 4
    assert result["valid_records"] == 4
    assert result["invalid_records"] == 0

    assert result["success_count"] == 2
    assert result["failure_count"] == 2

    assert result["failure_by_type"]["upload_timeout"] == 1
    assert result["failure_by_type"]["connection_failed"] == 1

    assert result["failure_by_event"]["event_001"] == 1
    assert result["failure_by_event"]["event_002"] == 1

    assert result["records_by_event"]["event_001"] == 2
    assert result["records_by_event"]["event_002"] == 2


def test_invalid_dates():
    logs = [
        "2026-99-99 09:01:12 INFO event_001 upload_success",
        "2026/11/20 09:01:12 INFO event_001 upload_success",
    ]

    result = analyzer.analyze_logs(logs)

    assert result["total_lines"] == 2
    assert result["valid_records"] == 0
    assert result["invalid_records"] == 2

    assert len(result["invalid_dates"]) == 2
    assert result["invalid_dates"][0]["line_number"] == 1
    assert result["invalid_dates"][1]["line_number"] == 2


def test_format_errors():
    logs = [
        "",
        "   ",
        "invalid log entry",
        "2026-11-20 25:00:00 INFO event_001 upload_success",
        "2026-11-20 09:01:12 WARN event_001 upload_success",
        "2026-11-20 09:01:12 INFO event/001 upload_success",
        "2026-11-20 09:01:12 ERROR event_001 unknown_action",
    ]

    result = analyzer.analyze_logs(logs)

    assert result["total_lines"] == 7
    assert result["valid_records"] == 0
    assert result["invalid_records"] == 7
    assert len(result["format_errors"]) == 7


def test_invalid_bytes():
    result = analyzer.analyze_logs([b"\xff"])

    assert result["total_lines"] == 1
    assert result["invalid_records"] == 1
    assert len(result["format_errors"]) == 1


def test_empty_input():
    result = analyzer.analyze_logs([])

    assert result["total_lines"] == 0
    assert result["valid_records"] == 0
    assert result["invalid_records"] == 0
    assert result["success_count"] == 0
    assert result["failure_count"] == 0
    assert result["failure_by_type"] == {}
    assert result["failure_by_event"] == {}
    assert result["records_by_event"] == {}
    assert result["invalid_dates"] == []
    assert result["format_errors"] == []


def test_generator_input():
    logs = (
        line
        for line in [
            "2026-11-20 09:01:12 INFO event_001 upload_success",
            "2026-11-20 09:02:15 ERROR event_001 upload_timeout",
        ]
    )

    result = analyzer.analyze_logs(logs)

    assert result["total_lines"] == 2
    assert result["valid_records"] == 2


def test_string_input():
    logs = (
        "2026-11-20 09:01:12 INFO event_001 upload_success\n"
        "2026-11-20 09:02:15 ERROR event_001 upload_timeout\n"
    )

    result = analyzer.analyze_logs(logs)

    assert result["total_lines"] == 2
    assert result["valid_records"] == 2


def test_analyze_text_compatibility():
    logs = (
        "2026-11-20 09:01:12 INFO event_001 upload_success"
    )

    result = analyzer.analyze_text(logs)

    assert result["total_lines"] == 1
    assert result["success_count"] == 1


def test_detail_limit():
    logs = [
        "2026-99-99 09:01:12 INFO event_001 upload_success"
        for _ in range(1001)
    ]

    result = analyzer.analyze_logs(logs)

    assert result["total_lines"] == 1001
    assert result["invalid_records"] == 1001
    assert len(result["invalid_dates"]) == 1000
    assert result["invalid_dates_omitted"] == 1


def test_statistics_invariants():
    logs = [
        "2026-11-20 09:01:12 INFO event_001 upload_success",
        "2026-11-20 09:02:15 ERROR event_001 upload_timeout",
        "2026-99-99 09:03:21 INFO event_002 upload_success",
    ]

    result = analyzer.analyze_logs(logs)

    assert (
        result["total_lines"]
        == result["valid_records"] + result["invalid_records"]
    )

    assert (
        result["valid_records"]
        == result["success_count"] + result["failure_count"]
    )

    assert sum(result["failure_by_type"].values()) == result["failure_count"]

    assert sum(result["failure_by_event"].values()) == result["failure_count"]

    assert sum(result["records_by_event"].values()) == result["valid_records"]


def test_deterministic_output():
    logs = [
        "2026-11-20 09:01:12 INFO event_001 upload_success",
        "2026-11-20 09:02:15 ERROR event_001 upload_timeout",
        "2026-99-99 09:03:21 INFO event_002 upload_success",
    ]

    first = analyzer.analyze_logs(logs)
    second = analyzer.analyze_logs(logs)

    assert json.dumps(first, sort_keys=True) == json.dumps(
        second,
        sort_keys=True,
    )
