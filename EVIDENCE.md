
# AI DevFlow — EVIDENCE

## 1. Alignment with Part A

This MVP implements the core workflow described in
Chapter 4 of `01_Team_Proposal.md`:

Requirement -> Planning -> Code Generation ->
Testing -> Failure Handling -> Quality Gate ->
Human Review Request.

The prototype also demonstrates the evaluation
and governance concepts in Chapters 5 and 7.

## 2. Execution Environment

- OS: Windows
- Python: 3.12.0
- Test framework: Pytest 9.2.0
- Code quality: Ruff
- Version control: Git
- Execution mode: MOCK

The MOCK mode uses predefined code and a
deterministic repair fixture. It does not call
the language model.

## 3. Reproduction Commands

Install dependencies:

    python -m pip install -r requirements.txt

Run the pipeline:

    python main.py

Run regression tests:

    python -m pytest tests -v

## 4. Verified Test Results

### Before repair

Actual result:

- test_upload_statistics: PASSED
- test_malformed_logs: PASSED
- test_reject_invalid_timestamp: FAILED

Summary: 2 passed, 1 failed.

Failure:

    assert result["total_records"] == 0
    AssertionError: assert 1 == 0

Cause:

The initial analyzer does not correctly reject
an invalid date such as 2026-99-99.

Evidence:

`reports/before_repair_pytest.txt`

### Failure Response

The MOCK Repair module recognized the failing
timestamp validation test and applied a
predefined correction.

The correction added datetime validation.
Existing test assertions were not changed.

This demonstrates deterministic failure
handling, NOT autonomous LLM repair.

### After repair

Actual result:

- test_upload_statistics: PASSED
- test_malformed_logs: PASSED
- test_reject_invalid_timestamp: PASSED

Summary: 3 passed.

Evidence:

`reports/after_repair_pytest.txt`

## 5. Quality Gate Evidence

The following checks passed:

| Check | Result |
|---|---|
| Python syntax | PASS |
| Basic static security rules | PASS |
| Ruff lint | PASS |
| Pytest regression | PASS |

Evidence:

`reports/quality_gate.json`

These static checks are not a security sandbox.

## 6. Human Review

The pipeline generated:

`reports/review_request.json`

Current verified status:

PENDING

The request contains the source file SHA256,
quality gate status, and review checklist.

Human approval has not yet been performed.
No production deployment was performed.

## 7. Git Evidence

Verified local commits:

- `57abd55` — Initial Agent pipeline
- `0f7ac1c` — CI workflow configuration
- `c457157` — Seven-chapter proposal

GitHub Actions execution is not yet verified.
Git rollback has not yet been demonstrated.

## 8. Model API Status

Provider: DeepSeek

An API request was observed in the provider
usage dashboard, but the earlier application
attempt returned empty content.

A successful real-model planning, coding,
and autonomous repair workflow has NOT yet
been verified.

The final submission must distinguish
API-generated results from MOCK fixtures.

API credentials are excluded from source control.

## 9. Current Limitations

- MOCK repair is deterministic.
- Real-model repair is not yet verified.
- No production-grade execution sandbox.
- No automatic production deployment.
- Human review remains mandatory.
- CI requires an actual GitHub run to verify.
- The 6-week to 2-week delivery improvement
  is a future target, not an MVP result.

## 10. Reference Sources

- Python: https://docs.python.org/3/
- Pytest: https://docs.pytest.org/
- Ruff: https://docs.astral.sh/ruff/
- Git: https://git-scm.com/docs
- GitHub Actions: https://docs.github.com/actions
- DeepSeek API: https://api-docs.deepseek.com/

These sources should be cited only to the extent
they were actually consulted or used.
