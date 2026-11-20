
import ast
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


FORBIDDEN_MODULES = {
    "os",
    "subprocess",
    "socket",
    "ctypes",
    "multiprocessing",
    "requests",
    "httpx",
}

FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "__import__",
    "compile",
}


def check_quality(
    root: Path,
    code_path: Path,
    tests_passed: bool,
) -> dict:
    """Run deterministic quality gates for the MOCK artifact."""

    checks = {
        "python_syntax": False,
        "basic_security_scan": False,
        "ruff_lint": False,
        "pytest": bool(tests_passed),
    }

    details = {}
    source = code_path.read_text(encoding="utf-8")

    # Gate 1: Syntax
    tree = None

    try:
        tree = ast.parse(source)
        checks["python_syntax"] = True
        details["python_syntax"] = "PASS"
    except SyntaxError as exc:
        details["python_syntax"] = str(exc)

    # Gate 2: Basic static security rules
    violations = []

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    if module in FORBIDDEN_MODULES:
                        violations.append(f"import {module}")

            elif isinstance(node, ast.ImportFrom):
                module = (node.module or "").split(".")[0]
                if module in FORBIDDEN_MODULES:
                    violations.append(f"from {module}")

            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in FORBIDDEN_CALLS:
                        violations.append(
                            f"call {node.func.id}"
                        )

        checks["basic_security_scan"] = not violations

    details["basic_security_scan"] = (
        "PASS" if not violations and tree is not None
        else ", ".join(violations) or "Syntax invalid"
    )

    # Gate 3: Ruff lint
    executable = (
        "ruff.exe" if os.name == "nt" else "ruff"
    )

    ruff_path = Path(sys.executable).parent / executable

    if ruff_path.exists():
        try:
            result = subprocess.run(
                [
                    str(ruff_path),
                    "check",
                    str(code_path),
                    "--select",
                    "E4,E7,E9,F",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )

            checks["ruff_lint"] = result.returncode == 0
            details["ruff_lint"] = (
                result.stdout + result.stderr
            ).strip() or "PASS"

        except (OSError, subprocess.TimeoutExpired) as exc:
            details["ruff_lint"] = str(exc)
    else:
        details["ruff_lint"] = "Ruff executable not found"

    # Gate 4: Real pytest result from TesterAgent
    details["pytest"] = (
        "PASS" if tests_passed else "FAIL"
    )

    passed = all(checks.values())

    report = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "artifact": str(code_path.relative_to(root)),
        "sha256": hashlib.sha256(
            code_path.read_bytes()
        ).hexdigest(),
        "checks": checks,
        "details": details,
        "passed": passed,
        "warning": (
            "Static checks are not a security sandbox. "
            "Untrusted AI code must not be executed "
            "without appropriate isolation and review."
        ),
    }

    reports = root / "reports"
    reports.mkdir(exist_ok=True)

    (reports / "quality_gate.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return report
