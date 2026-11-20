
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "workspace" / "generated" / "analyzer.py"

spec = importlib.util.spec_from_file_location(
    "analyzer", MODULE_PATH
)
analyzer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analyzer)


def test_upload_statistics():
    logs = """
2026-11-20 09:01:12 INFO event_001 upload_success
2026-11-20 09:02:15 ERROR event_001 upload_timeout
2026-11-20 09:03:21 ERROR event_002 connection_failed
"""

    result = analyzer.analyze_text(logs)

    assert result["total_records"] == 3
    assert result["success_count"] == 1
    assert result["failure_count"] == 2
    assert result["failure_types"]["upload_timeout"] == 1


def test_malformed_logs():
    logs = "invalid log entry"

    result = analyzer.analyze_text(logs)

    assert result["total_records"] == 0
    assert result["invalid_count"] == 1


def test_reject_invalid_timestamp():
    logs = (
        "2026-99-99 09:01:12 "
        "INFO event_001 upload_success"
    )

    result = analyzer.analyze_text(logs)

    assert result["total_records"] == 0
    assert result["success_count"] == 0
    assert result["invalid_count"] == 1
