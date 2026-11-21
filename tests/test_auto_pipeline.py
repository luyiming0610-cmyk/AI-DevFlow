"""Deterministic orchestration tests; these DO NOT call DeepSeek or Docker.

Run: python -m pytest tests/test_auto_pipeline.py -v
"""

import sys
import types

# This container's openai package is only a namespace; tests never make API calls.
try:
    from openai import OpenAI  # noqa: F401
except ImportError:
    stub = types.ModuleType("openai")
    stub.OpenAI = object
    sys.modules["openai"] = stub

import core.auto_pipeline as p


class FakeAPI:
    mode = "api"
    model = "fake-test-client-NOT-DeepSeek"
    last_usage = None

    def __init__(self, snippets):
        self.snippets = iter(snippets)
        self.calls = 0

    def generate(self, system_prompt, user_prompt, max_tokens):
        self.calls += 1
        self.last_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        return next(self.snippets)


def setup(monkeypatch, tmp_path, snippets, statuses):
    contract = tmp_path / "task.md"
    contract.write_text("# 合同\nparse_line\nanalyze_logs\n" + ("示例。" * 60), encoding="utf-8")
    accept = tmp_path / "acceptance.py"
    accept.write_text("def test_a(): pass\ndef test_b(): pass\n", encoding="utf-8")
    monkeypatch.setattr(p, "ACCEPTANCE", accept)
    monkeypatch.setattr(p, "TASKS_DIR", tmp_path / "runs")
    p.TASKS_DIR.mkdir()
    monkeypatch.setattr(p, "require_docker", lambda: None)
    fake = FakeAPI(snippets)
    monkeypatch.setattr(p, "create_api_client", lambda: fake)
    monkeypatch.setattr(
        p, "static_check",
        lambda path: {"python_syntax": True, "ruff_lint": True,
                      "basic_security_scan": True, "contract_functions": True,
                      "all_passed": True, "notes": []},
    )
    requested = iter(statuses)

    def fake_run_candidate(candidate, output_dir):
        output_dir.mkdir(parents=True)
        status = next(requested)
        (output_dir / "pytest.txt").write_text("2 failed\n" if status == "FAILED" else "2 passed\n", encoding="utf-8")
        return {"status": status, "tests_executed": status in ("PASSED", "FAILED"),
                "passed_count": 2 if status == "PASSED" else 0,
                "failed_count": 2 if status == "FAILED" else 0}

    monkeypatch.setattr(p, "run_candidate", fake_run_candidate)
    return contract, fake


def test_first_candidate_passes(monkeypatch, tmp_path):
    contract, fake = setup(monkeypatch, tmp_path, ["PLAN", "def analyze_logs(lines): return {}"], ["PASSED"])
    result = p.run_pipeline(contract, max_repairs=2)
    assert result["status"] == "TESTS_PASSED_REVIEW_PENDING"
    assert result["human_review"] == "PENDING"
    assert result["production_deployment"] is False
    assert result["tests_executed"] is True
    assert len(result["rounds"]) == 1
    assert fake.calls == 2
    assert (p.TASKS_DIR / result["task_id"] / "report.md").is_file()
    assert (p.TASKS_DIR / result["task_id"] / "acceptance_snapshot.py").is_file()


def test_repair_then_pass(monkeypatch, tmp_path):
    contract, fake = setup(monkeypatch, tmp_path,
                           ["PLAN", "a=1", "a=2"], ["FAILED", "PASSED"])
    result = p.run_pipeline(contract, max_repairs=2)
    assert result["status"] == "TESTS_PASSED_REVIEW_PENDING"
    assert len(result["rounds"]) == 2
    assert fake.calls == 3
    root = p.TASKS_DIR / result["task_id"]
    assert (root / "round_00" / "candidate.py").read_text(encoding="utf-8") == "a=1\n"
    assert (root / "round_01" / "candidate.py").read_text(encoding="utf-8") == "a=2\n"


def test_repair_budget_exhausted(monkeypatch, tmp_path):
    contract, fake = setup(monkeypatch, tmp_path,
                           ["PLAN", "a=1", "a=2", "a=3"],
                           ["FAILED", "FAILED", "FAILED"])
    result = p.run_pipeline(contract, max_repairs=2)
    assert result["status"] == "ESCALATED_TO_HUMAN"
    assert len(result["rounds"]) == 3
    assert fake.calls == 4
    assert result["production_deployment"] is False


def test_infrastructure_failure_stops_without_repair(monkeypatch, tmp_path):
    contract, fake = setup(monkeypatch, tmp_path, ["PLAN", "a=1"], ["BLOCKED"])
    result = p.run_pipeline(contract, max_repairs=2)
    assert result["status"] == "BLOCKED_TEST_INFRASTRUCTURE"
    assert fake.calls == 2
    assert result["tests_executed"] is False


def test_unchanged_repair_stops(monkeypatch, tmp_path):
    contract, fake = setup(monkeypatch, tmp_path, ["PLAN", "a=1", "a=1"], ["FAILED"])
    result = p.run_pipeline(contract, max_repairs=2)
    assert result["status"] == "ESCALATED_UNCHANGED_REPAIR"
    assert fake.calls == 3


def test_no_secret_in_report(monkeypatch, tmp_path):
    contract, _ = setup(monkeypatch, tmp_path, ["PLAN", "a=1"], ["PASSED"])
    result = p.run_pipeline(contract)
    text = (p.TASKS_DIR / result["task_id"] / "report.md").read_text(encoding="utf-8")
    assert "fake-test-client-NOT-DeepSeek" in text
    assert "人工审核" in text
