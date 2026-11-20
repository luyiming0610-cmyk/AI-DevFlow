
import ast
from pathlib import Path


def extract_code(response: str) -> str:
    """Remove optional Markdown code fences."""
    code = response.strip()

    if code.startswith("```"):
        lines = code.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        code = "\n".join(lines).strip()

    return code


class RepairAgent:
    def __init__(self, model_client):
        self.model = model_client

    def run(
        self,
        code_path: Path,
        failure_output: str,
    ) -> str:

        if self.model.mode == "mock":
            return self._mock_repair(
                code_path,
                failure_output,
            )

        if self.model.mode == "api":
            return self._api_repair(
                code_path,
                failure_output,
            )

        raise ValueError("Unsupported AI mode")

    def _mock_repair(
        self,
        code_path: Path,
        failure_output: str,
    ) -> str:

        if "test_reject_invalid_timestamp" not in failure_output:
            raise RuntimeError(
                "Unknown failure. Escalate to human review."
            )

        source = code_path.read_text(encoding="utf-8")

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
                "Timestamp validation already exists."
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

        ast.parse(fixed_source)

        code_path.write_text(
            fixed_source,
            encoding="utf-8",
        )

        return (
            "MOCK repair applied: "
            "invalid timestamp validation added."
        )

    def _api_repair(
        self,
        code_path: Path,
        failure_output: str,
    ) -> str:
        """Generate a repair candidate using a real LLM."""

        original_code = code_path.read_text(
            encoding="utf-8"
        )

        system_prompt = """
You are a senior Python software repair agent.

Your task is to fix the provided source code
based on the real pytest failure output.

Rules:
1. Return ONLY the complete corrected Python source.
2. Do not include explanations or Markdown fences.
3. Preserve the function analyze_text(text: str).
4. Preserve the existing result dictionary keys.
5. Fix the root cause of the failure.
6. Do not change or weaken the tests.
7. Use only Python standard library modules.
8. Do not add network access, subprocess,
   eval, exec, or external dependencies.
9. Keep changes minimal.
10. Do not claim that tests have passed.
"""

        user_prompt = f"""
ORIGINAL SOURCE CODE:

{original_code}

PYTEST FAILURE OUTPUT:

{failure_output[:6000]}

Return the complete corrected Python source code.
"""

        response = self.model.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=3200,
        )

        fixed_code = extract_code(response)

        # Validate syntax before saving.
        tree = ast.parse(
            fixed_code,
            filename=str(code_path),
        )

        functions = [
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        ]

        if "analyze_text" not in functions:
            raise RuntimeError(
                "Repair output is missing analyze_text()."
            )

        if fixed_code.strip() == original_code.strip():
            raise RuntimeError(
                "Model returned unchanged code."
            )

        # Save the candidate, but do not execute it.
        code_path.write_text(
            fixed_code.rstrip() + "\n",
            encoding="utf-8",
        )

        return (
            "API repair candidate generated. "
            "Syntax checked. "
            "Execution and human review pending."
        )
