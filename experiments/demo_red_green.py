
"""B11：受控故障注入与真实 DeepSeek 红灯→绿灯实验。

不修改正式验收测试，不覆盖原始候选代码，不自动部署。
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import uuid

from datetime import datetime, timezone
from pathlib import Path

from core.auto_pipeline import (
    ACCEPTANCE,
    CONTRACT,
    preflight,
    static_check,
)
from core.isolated_tester import run_candidate
from core.real_task import ROOT, create_api_client, strip_code


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="B11 真实 Pytest 失败与自动修复实验"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="已经通过15项验收的原始候选代码",
    )
    parser.add_argument(
        "--max-repairs",
        type=int,
        default=2,
        choices=(1, 2, 3),
    )
    parser.add_argument(
        "--call-api",
        action="store_true",
        help="明确授权调用真实 DeepSeek API",
    )
    args = parser.parse_args()

    if not args.call_api:
        parser.error("未传 --call-api，不会调用模型。")

    source = args.source.resolve()

    if not source.is_file():
        parser.error(f"原始候选代码不存在：{source}")

    # 在产生费用前，检查 Docker 和可信验收用例。
    contract, tests, test_sha = preflight(CONTRACT)

    task_id = (
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:6]
    )

    folder = ROOT / "evidence" / "red_green" / task_id
    folder.mkdir(parents=True, exist_ok=False)

    (folder / "requirement_snapshot.md").write_text(
        contract + "\n",
        encoding="utf-8",
    )

    (folder / "acceptance_snapshot.py").write_text(
        tests,
        encoding="utf-8",
    )

    data = {
        "scenario": "CONTROLLED_FAULT_INJECTION",
        "task_id": task_id,
        "created_utc": now(),
        "baseline_source": str(source),
        "baseline_source_sha256": sha256(source),
        "acceptance_sha256": test_sha,
        "status": "STARTED",
        "fault": (
            "人为在 analyze_logs 函数中插入错误返回值，"
            "仅修改实验副本"
        ),
        "api_calls": [],
        "rounds": [],
        "human_review": "PENDING",
        "production_deployment": False,
    }

    def save() -> None:
        data["updated_utc"] = now()

        (folder / "result.json").write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        lines = [
            "# B11｜真实 DeepSeek 红灯→绿灯实验",
            "",
            f"- 任务：{task_id}",
            f"- 状态：**{data['status']}**",
            "- 类型：人为注入缺陷的受控实验",
            f"- 原始候选 SHA256：`{data['baseline_source_sha256']}`",
            f"- 正式测试 SHA256：`{test_sha}`",
            "- 人工审核：PENDING",
            "- 生产部署：False",
            "",
            "## 每轮验证",
            "",
        ]

        for item in data["rounds"]:
            validation = item.get("validation") or {}

            lines.append(
                f"- {item['name']}："
                f"静态检查={item.get('static_passed')}；"
                f"测试状态={validation.get('status', '未执行')}；"
                f"通过={validation.get('passed_count', 0)}；"
                f"失败={validation.get('failed_count', 0)}"
            )

        lines.extend(["", "## 实际模型调用", ""])

        for call in data["api_calls"]:
            lines.append(
                f"- {call['stage']}：{call['usage']}"
            )

        if data.get("error"):
            lines.extend([
                "",
                "## 阻断或异常",
                "",
                data["error"],
            ])

        (folder / "report.md").write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )

    def check_test_hash() -> None:
        if sha256(ACCEPTANCE) != test_sha:
            raise RuntimeError(
                "正式验收测试发生变化，停止实验。"
            )

    def validate(
        name: str,
        candidate: Path,
    ) -> tuple[dict, str]:
        check_test_hash()

        entry = {
            "name": name,
            "candidate": candidate.name,
            "sha256": sha256(candidate),
            "static_passed": False,
            "validation": None,
        }

        data["rounds"].append(entry)

        checks = static_check(candidate)

        (folder / f"{name}_static.json").write_text(
            json.dumps(
                checks,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        entry["static_passed"] = bool(
            checks.get("all_passed")
        )

        if not entry["static_passed"]:
            save()
            return entry, (
                "静态检查失败：\n"
                + "\n".join(checks.get("notes", []))
            )

        output = folder / f"{name}_validation"
        validation = run_candidate(candidate, output)

        entry["validation"] = validation
        entry["validation_dir"] = output.name

        check_test_hash()
        save()

        log = (output / "pytest.txt").read_text(
            encoding="utf-8"
        )

        return entry, log

    save()

    try:
        # A. 先证明原始代码确实能够通过所有测试。
        baseline = folder / "baseline_good.py"
        baseline.write_bytes(source.read_bytes())

        baseline_entry, _ = validate(
            "baseline",
            baseline,
        )

        baseline_result = (
            baseline_entry.get("validation") or {}
        )

        if (
            not baseline_entry["static_passed"]
            or baseline_result.get("status") != "PASSED"
        ):
            data["status"] = "BLOCKED_BASELINE_NOT_GREEN"
            data["error"] = (
                "原始代码未通过基线验证，"
                "不能开展红灯→绿灯实验。"
            )
            save()
            return 1

        # B. 在副本的 analyze_logs 函数内注入缺陷。
        # 不修改正式验收测试或原始候选代码。
        original = baseline.read_text(encoding="utf-8")
        tree = ast.parse(original)

        functions = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "analyze_logs"
        ]

        if len(functions) != 1:
            raise RuntimeError(
                "找不到唯一的 analyze_logs 函数。"
            )

        func = functions[0]

        if not func.body:
            raise RuntimeError("无法确定注入位置。")

        lines = original.splitlines(keepends=True)

        inserted = (
            " " * (func.col_offset + 4)
            + "return {'success_count': -1}"
            + "  # B11 deliberately seeded bug\n"
        )

        lines.insert(
            func.body[0].lineno - 1,
            inserted,
        )

        faulty = folder / "faulty_seed.py"
        faulty.write_text(
            "".join(lines),
            encoding="utf-8",
        )

        # C. 必须获得真实 Pytest 失败，否则不调用 API。
        red_entry, failure = validate(
            "red_fault",
            faulty,
        )

        red_result = red_entry.get("validation") or {}

        if (
            not red_entry["static_passed"]
            or red_result.get("status") != "FAILED"
            or red_result.get("failed_count", 0) < 1
        ):
            data["status"] = "BLOCKED_NO_REAL_RED_TEST"
            data["error"] = (
                "没有产生合格的真实 Pytest 失败记录，"
                "本次不调用 DeepSeek。"
            )
            save()
            return 1

        print(
            "已确认真实 Pytest 红灯："
            f"{red_result['failed_count']} 项失败"
        )

        # D. 只有获得真实测试失败后，才启动模型修复。
        client = create_api_client()

        if client.mode != "api":
            raise RuntimeError(
                "禁止 MOCK 模式自动回退。"
            )

        current = faulty

        for index in range(1, args.max_repairs + 1):
            data["status"] = f"REPAIRING_{index}"
            save()

            prompt = (
                f"【不可修改的业务规范】\n{contract}\n\n"
                f"【正式验收测试】\n{tests}\n\n"
                f"【当前完整源码】\n"
                f"{current.read_text(encoding='utf-8')}\n\n"
                f"【真实测试或静态检查失败日志】\n"
                f"{failure[-12000:]}\n\n"
                "这是一项明确标记的受控故障注入实验。"
                "请修复真实逻辑问题，保留 parse_line、"
                "analyze_logs、analyze_text 三个公开接口。"
                "只能输出完整 Python 单文件源码，"
                "不能修改验收测试，不能访问网络或文件。"
            )

            client.last_usage = None

            try:
                reply = client.generate(
                    (
                        "你是专业的 Python Repair Agent。"
                        "根据完整规范、当前代码和真实失败日志"
                        "修复问题，避免回归。"
                        "只输出完整代码，不要 Markdown。"
                    ),
                    prompt,
                    max_tokens=7000,
                )
            finally:
                data["api_calls"].append({
                    "stage": f"repair_{index}",
                    "usage": client.last_usage,
                })
                save()

            repaired_code = (
                strip_code(reply).rstrip() + "\n"
            )

            previous_code = current.read_text(
                encoding="utf-8"
            )

            if repaired_code == previous_code:
                data["status"] = (
                    "ESCALATED_UNCHANGED_REPAIR"
                )
                data["error"] = (
                    "模型返回相同代码，"
                    "没有实际修复，停止重试。"
                )
                save()
                return 1

            candidate = (
                folder / f"repair_{index:02d}.py"
            )

            candidate.write_text(
                repaired_code,
                encoding="utf-8",
            )

            entry, failure = validate(
                f"repair_{index:02d}",
                candidate,
            )

            validation = entry.get("validation") or {}

            if (
                entry["static_passed"]
                and validation.get("status") == "PASSED"
            ):
                data["status"] = (
                    "TESTS_PASSED_REVIEW_PENDING"
                )
                data["final_candidate"] = candidate.name
                data["final_sha256"] = sha256(candidate)
                save()

                print(
                    "实验成功：真实 Pytest 红灯 → "
                    "DeepSeek 修复 → 15/15 绿灯"
                )
                print(f"证据目录：{folder}")
                return 0

            if validation.get("status") in (
                "BLOCKED",
                "INFRA_ERROR",
                "COLLECTION_ERROR",
                "TIMEOUT",
            ):
                data["status"] = (
                    "BLOCKED_TEST_INFRASTRUCTURE"
                )
                data["error"] = (
                    "Docker 测试环境异常，"
                    "停止继续调用 Repair Agent。"
                )
                save()
                return 1

            current = candidate

        data["status"] = "ESCALATED_TO_HUMAN"
        data["error"] = (
            "达到最大修复次数，"
            "尚未通过全部验收，需人工处理。"
        )
        save()
        return 1

    except Exception as exc:
        data["status"] = "PIPELINE_ERROR"
        data["error"] = f"{type(exc).__name__}: {exc}"
        save()

        print(f"实验终止：{data['error']}")
        print(f"证据目录：{folder}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
