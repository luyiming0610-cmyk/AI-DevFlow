
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from agents.developer import MOCK_CODE
from agents.repair import RepairAgent
from core.model_client import ModelClient


ROOT = Path(__file__).resolve().parent

TRIAL_DIR = ROOT / "runs" / "api_repair_trial"
SOURCE_FILE = TRIAL_DIR / "analyzer.py"
REPORT_FILE = TRIAL_DIR / "result.json"

FAILURE_LOG = (
    ROOT / "reports" / "before_repair_pytest.txt"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Controlled real LLM repair verification"
    )

    parser.add_argument(
        "--call-api",
        action="store_true",
        help="Make exactly one model request",
    )

    args = parser.parse_args()

    if not FAILURE_LOG.exists():
        print("Missing initial pytest failure log.")
        return 1

    failure_output = FAILURE_LOG.read_text(
        encoding="utf-8"
    )

    if "test_reject_invalid_timestamp" not in failure_output:
        print("Expected failure was not found.")
        return 1

    if not args.call_api:
        print("AI DevFlow API Repair - DRY RUN")
        print("Failure log: FOUND")
        print("Original code fixture: FOUND")
        print("API requests: 0")
        print("Cost: 0")
        print(
            "Run with --call-api to perform "
            "one real model request."
        )
        return 0

    if TRIAL_DIR.exists():
        print(
            "Trial directory already exists. "
            "Inspect the previous result first."
        )
        return 1

    load_dotenv(ROOT / ".env")

    if not os.getenv("AI_API_KEY"):
        print("AI_API_KEY is missing.")
        return 1

    # Override the mode only for this process.
    os.environ["AI_MODE"] = "api"

    TRIAL_DIR.mkdir(parents=True, exist_ok=False)

    SOURCE_FILE.write_text(
        MOCK_CODE.strip() + "\n",
        encoding="utf-8",
    )

    original_hash = sha256(SOURCE_FILE)

    client = ModelClient()
    repair = RepairAgent(client)

    print("Calling real model for repair candidate...")

    status = "FAILED"
    message = ""

    try:
        message = repair.run(
            code_path=SOURCE_FILE,
            failure_output=failure_output,
        )

        status = "CANDIDATE_GENERATED"

    except Exception as exc:
        message = (
            f"{type(exc).__name__}: {exc}"
        )

    result = {
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "mode": "api",
        "model": client.model,
        "status": status,
        "message": message,
        "original_sha256": original_hash,
        "candidate_sha256": sha256(SOURCE_FILE),
        "usage": client.last_usage,
        "tests_executed": False,
        "human_review": "PENDING",
        "production_deployment": False,
    }

    REPORT_FILE.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Status:", status)
    print("Message:", message)
    print("Result:", REPORT_FILE)
    print("Token usage:", client.last_usage)

    if status == "CANDIDATE_GENERATED":
        print("Candidate:", SOURCE_FILE)
        print("Do not execute before review.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
