
"""Regression tests for the AI candidate static security gate."""

from pathlib import Path

from core.real_task import inspect_candidate


def inspect_source(
    tmp_path: Path,
    source: str,
) -> dict:
    path = tmp_path / "candidate.py"
    path.write_text(source, encoding="utf-8")
    return inspect_candidate(path)


def test_safe_future_annotations_allowed(tmp_path):
    report = inspect_source(
        tmp_path,
        (
            "from __future__ import annotations\n\n"
            "def analyze_text(text: str) -> dict:\n"
            "    return {}\n"
        ),
    )

    assert report["python_syntax"] is True
    assert report["basic_security_scan"] is True
    assert report["ruff_lint"] is True


def test_os_import_still_rejected(tmp_path):
    report = inspect_source(
        tmp_path,
        (
            "import os\n\n"
            "def analyze_text(text):\n"
            "    return {}\n"
        ),
    )

    assert report["basic_security_scan"] is False
    assert any(
        "os" in note for note in report["notes"]
    )


def test_eval_call_still_rejected(tmp_path):
    report = inspect_source(
        tmp_path,
        (
            "def analyze_text(text):\n"
            "    return eval(text)\n"
        ),
    )

    assert report["basic_security_scan"] is False
    assert any(
        "eval" in note for note in report["notes"]
    )


def test_invalid_python_still_blocked(tmp_path):
    report = inspect_source(
        tmp_path,
        "def analyze_text(:\n    pass\n",
    )

    assert report["python_syntax"] is False
