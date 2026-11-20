
import getpass
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REVIEW_FILE = ROOT / "reports" / "review_request.json"
GATE_FILE = ROOT / "reports" / "quality_gate.json"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_review_request(
    code_path: Path,
    quality_passed: bool,
) -> Path:
    """Create a review request; never auto-approve."""

    relative_path = str(code_path.relative_to(ROOT))

    request = {
        "artifact": relative_path,
        "sha256": file_hash(code_path),
        "quality_gate_passed": quality_passed,
        "status": (
            "PENDING" if quality_passed else "BLOCKED"
        ),
        "reviewer": None,
        "approved_at_utc": None,
        "checklist": [
            "Read the generated source code",
            "Confirm the change meets the requirement",
            "Inspect security and permission boundaries",
            "Review the test results",
            "Confirm no unintended changes",
        ],
        "production_deployment": "NOT_PERFORMED",
    }

    REVIEW_FILE.parent.mkdir(exist_ok=True)

    REVIEW_FILE.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return REVIEW_FILE


def approve():
    if not REVIEW_FILE.exists() or not GATE_FILE.exists():
        raise SystemExit(
            "Missing review request or quality gate report."
        )

    request = json.loads(
        REVIEW_FILE.read_text(encoding="utf-8")
    )

    gate = json.loads(
        GATE_FILE.read_text(encoding="utf-8")
    )

    if request["status"] != "PENDING":
        raise SystemExit(
            f"Review status: {request['status']}"
        )

    if not gate.get("passed"):
        raise SystemExit(
            "Quality gate is not passing."
        )

    code_path = ROOT / request["artifact"]
    current_hash = file_hash(code_path)

    if current_hash != request["sha256"]:
        raise SystemExit(
            "Source code changed after review request."
        )

    if current_hash != gate.get("sha256"):
        raise SystemExit(
            "Source code differs from quality gate artifact."
        )

    print("\nAI DevFlow - Human Code Review")
    print("--------------------------------")
    print("Artifact:", code_path)
    print("SHA256:", current_hash)
    print("\nReview checklist:")

    for item in request["checklist"]:
        print(" -", item)

    print(
        "\nRead the code, quality report, "
        "and test logs before approval."
    )

    confirmation = input(
        "\nType APPROVE only after reviewing: "
    ).strip()

    if confirmation != "APPROVE":
        print("Review remains pending.")
        return

    request["status"] = "APPROVED"
    request["reviewer"] = getpass.getuser()
    request["approved_at_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    REVIEW_FILE.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Human review recorded.")
    print("No production deployment was performed.")


if __name__ == "__main__":
    approve()
