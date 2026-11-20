
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    passed: bool
    return_code: int
    output: str
    log_path: Path


class TesterAgent:
    """
    Execute pytest and save real test evidence.

    The result is determined by pytest's exit code,
    not by an AI-generated success message.
    """

    def __init__(self, root: Path):
        self.root = root

    def run(self, stage: str) -> TestResult:
        reports = self.root / "reports"
        reports.mkdir(parents=True, exist_ok=True)

        log_path = reports / f"{stage}_pytest.txt"

        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_analyzer.py",
            "-v",
            "--tb=short",
        ]

        try:
            process = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )

            parts = [
                chunk.rstrip("\r\n")
                for chunk in (
                    process.stdout,
                    process.stderr,
                )
                if chunk and chunk.strip()
            ]

            output = (
                "\n".join(parts).rstrip("\n") + "\n"
                if parts
                else "No pytest output.\n"
            )

            return_code = process.returncode

        except subprocess.TimeoutExpired:
            output = (
                "ERROR: Pytest exceeded "
                "the 30-second time limit.\n"
            )
            return_code = 124

        except OSError as exc:
            output = (
                f"ERROR: Unable to execute pytest: "
                f"{exc}\n"
            )
            return_code = 125

        log_path.write_text(
            output,
            encoding="utf-8",
        )

        return TestResult(
            passed=(return_code == 0),
            return_code=return_code,
            output=output,
            log_path=log_path,
        )
