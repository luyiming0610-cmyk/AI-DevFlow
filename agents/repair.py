
import ast
from pathlib import Path


class RepairAgent:
    def __init__(self, model_client):
        self.model = model_client

    def run(
        self,
        code_path: Path,
        failure_output: str,
    ) -> str:

        if self.model.mode != "mock":
            raise RuntimeError(
                "API repair execution is not enabled yet."
            )

        if "test_reject_invalid_timestamp" not in failure_output:
            raise RuntimeError(
                "Unknown failure. Escalate to human review."
            )

        source = code_path.read_text(
            encoding="utf-8"
        )

        target = (
            "        date, time, level, "
            "event_id, action = parts\n"
        )

        if target not in source:
            raise RuntimeError(
                "Expected MOCK code structure not found."
            )

        if "datetime.strptime" in source:
            raise RuntimeError(
                "Date validation already exists. "
                "Escalate to human review."
            )

        source = source.replace(
            "from collections import Counter\n",
            "from collections import Counter\n"
            "from datetime import datetime\n",
            1,
        )

        replacement = (
            target
            + "\n"
            + "        try:\n"
            + "            datetime.strptime(\n"
            + '                f"{date} {time}",\n'
            + '                "%Y-%m-%d %H:%M:%S",\n'
            + "            )\n"
            + "        except ValueError:\n"
            + "            invalid += 1\n"
            + "            continue\n"
        )

        fixed_source = source.replace(
            target,
            replacement,
            1,
        )

        ast.parse(
            fixed_source,
            filename=str(code_path),
        )

        code_path.write_text(
            fixed_source,
            encoding="utf-8",
        )

        return (
            "MOCK repair applied: "
            "invalid timestamp validation added."
        )
