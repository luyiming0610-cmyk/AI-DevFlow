
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from agents.planner import PlannerAgent
from agents.developer import DeveloperAgent
from agents.tester import TesterAgent
from agents.repair import RepairAgent
from core.model_client import ModelClient
from core.quality_gate import check_quality
from review import create_review_request


ROOT = Path(__file__).resolve().parent
console = Console()


def main() -> int:
    load_dotenv(ROOT / ".env")

    console.print(
        Panel.fit(
            "[bold cyan]AI DEVFLOW[/bold cyan]\n"
            "Multi-Agent Software Development Pipeline",
            border_style="cyan",
        )
    )

    model = ModelClient()
    console.print(f"Mode: {model.mode.upper()}")

    requirement_path = (
        ROOT / "workspace" / "requirements" / "task.md"
    )

    requirement = requirement_path.read_text(
        encoding="utf-8"
    )

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)

    # 1. Planner
    console.print("[cyan][1/6] Planning...[/cyan]")

    planner = PlannerAgent(model)
    plan = planner.run(requirement)

    (reports / "development_plan.md").write_text(
        plan,
        encoding="utf-8",
    )

    # 2. Developer
    console.print("[cyan][2/6] Generating code...[/cyan]")

    developer = DeveloperAgent(model)

    code_path = (
        ROOT / "workspace" / "generated" / "analyzer.py"
    )

    developer.run(
        requirement=requirement,
        plan=plan,
        output_path=code_path,
    )

    console.print(f"Generated: {code_path}")

    # Never automatically execute unreviewed API code.
    if model.mode != "mock":
        console.print(
            "[yellow]API-generated code saved, "
            "but execution is blocked pending "
            "isolation and human review.[/yellow]"
        )
        return 0

    # 3. Initial tests
    console.print("[cyan][3/6] Initial tests...[/cyan]")

    tester = TesterAgent(ROOT)
    initial = tester.run("before_repair")

    console.print(
        f"Initial tests passed: {initial.passed}"
    )
    console.print(f"Log: {initial.log_path}")

    # Deliberate negative test must fail initially.
    if initial.passed:
        console.print(
            "[red]Expected failure was not reproduced."
            "[/red]"
        )
        return 1

    # 4. Repair and regression tests
    console.print(
        "[cyan][4/6] Repair and regression...[/cyan]"
    )

    repair_note = "Not attempted"
    final = initial

    try:
        repair = RepairAgent(model)

        repair_note = repair.run(
            code_path,
            initial.output,
        )

        console.print(repair_note)

        final = tester.run("after_repair")

    except Exception as exc:
        repair_note = f"Escalated: {exc}"
        console.print(f"[red]{repair_note}[/red]")

    # 5. Quality gate
    console.print(
        "[cyan][5/6] Checking quality gates...[/cyan]"
    )

    gate = check_quality(
        root=ROOT,
        code_path=code_path,
        tests_passed=final.passed,
    )

    for name, passed in gate["checks"].items():
        status = "PASS" if passed else "FAIL"
        console.print(f"  {name}: {status}")

    # 6. Human review request
    console.print(
        "[cyan][6/6] Creating review request...[/cyan]"
    )

    review_path = create_review_request(
        code_path=code_path,
        quality_passed=gate["passed"],
    )

    if gate["passed"]:
        status = "READY FOR HUMAN REVIEW"
    else:
        status = "BLOCKED - QUALITY GATE FAILED"

    report = f"""# AI DevFlow Pipeline Report

## Run Summary

- Mode: MOCK
- Scenario: Event Image Upload Log Analyzer
- Initial test exit code: {initial.return_code}
- Final test exit code: {final.return_code}
- Quality gate passed: {gate["passed"]}
- Final status: {status}

## Repair

{repair_note}

## Evidence

- Initial test log: reports/before_repair_pytest.txt
- Regression log: reports/after_repair_pytest.txt
- Quality results: reports/quality_gate.json
- Human review: reports/review_request.json
- Generated source: workspace/generated/analyzer.py

## Governance

- The initial failing test is deliberate.
- MOCK uses predefined code and a deterministic repair.
- Autonomous LLM repair has not been demonstrated.
- Human code review is required.
- No production deployment was performed.
"""

    report_path = reports / "pipeline_report.md"

    report_path.write_text(
        report,
        encoding="utf-8",
    )

    console.print(f"Report: {report_path}")
    console.print(f"Review request: {review_path}")

    if gate["passed"]:
        console.print(
            "[green]Quality gates passed.[/green]"
        )
        console.print(
            "[yellow]Human review: PENDING[/yellow]"
        )
        return 0

    console.print(
        "[red]Pipeline blocked by quality gate.[/red]"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
