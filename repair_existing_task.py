
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

from agents.repair import RepairAgent
from core.model_client import ModelClient
from core.real_task import inspect_candidate


ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "runs" / "interactive_tasks"
TEST_FILE = ROOT / "tests" / "test_analyzer.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_log(path: Path) -> str:
    """兼容 PowerShell 可能生成的 UTF-16 日志。"""
    content = path.read_bytes()

    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return content.decode("utf-16")

    if content.count(b"\x00") > len(content) // 8:
        return content.decode("utf-16-le")

    return content.decode("utf-8", errors="replace")


def save_result(path: Path, result: dict) -> None:
    path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="对真实 AI 研发任务执行一次 Repair"
    )

    parser.add_argument("task_id")

    parser.add_argument(
        "--call-api",
        action="store_true",
        help="发起一次真实模型修复操作",
    )

    args = parser.parse_args()

    if not re.fullmatch(
        r"\d{8}-\d{6}-[0-9a-f]{6}",
        args.task_id,
    ):
        print("任务编号格式不正确。")
        return 1

    task_dir = TASKS_DIR / args.task_id

    original = task_dir / "candidate.py"
    failure_log = task_dir / "pytest.txt"

    repaired = task_dir / "candidate_repaired.py"
    result_file = task_dir / "repair_result.json"

    if not original.is_file():
        print("找不到原始 AI 生成代码。")
        return 1

    if not failure_log.is_file():
        print("找不到真实 Pytest 失败日志。")
        return 1

    if not TEST_FILE.is_file():
        print("找不到验收测试文件。")
        return 1

    failure = read_log(failure_log)

    if not re.search(r"\b\d+\s+failed\b", failure):
        print("失败日志中没有识别到 Pytest 失败结果。")
        return 1

    if repaired.exists() or result_file.exists():
        print("当前任务已经存在修复记录。")
        print("为保护证据，不允许覆盖原修复结果。")
        return 1

    tests = TEST_FILE.read_text(encoding="utf-8")

    # 将独立验收标准明确交给修复 Agent，
    # 不修改或弱化现有测试。
    failure_context = (
        "以下是不可修改的验收测试：\n\n"
        + tests[:4000]
        + "\n\n以下是实际 Pytest 失败记录：\n\n"
        + failure[:2500]
        + "\n\n修复必须满足：\n"
        + "1. total_records 仅统计有效业务记录。\n"
        + "2. 空行不计入有效记录。\n"
        + "3. 非法日期计入 invalid_count，"
          "不计入 total_records。\n"
        + "4. ERROR 日志中的 upload_timeout、"
          "connection_failed 等操作应计为失败。\n"
        + "5. 保留原有返回字典的字段名称。\n"
        + "6. 不得修改任何验收测试。\n"
    )

    print("任务编号：", args.task_id)
    print("原始代码：", original)
    print("失败日志：", failure_log)

    if not args.call_api:
        print("当前为预检查，API 请求数：0")
        print("增加 --call-api 才会调用 DeepSeek。")
        return 0

    load_dotenv(ROOT / ".env")

    if not os.getenv("AI_API_KEY"):
        print("未找到 AI_API_KEY。")
        return 1

    # 仅在当前进程中使用 API 模式。
    os.environ["AI_MODE"] = "api"

    # 先复制原文件，绝不覆盖第一次生成的代码。
    shutil.copy2(original, repaired)

    result = {
        "task_id": args.task_id,
        "mode": "api",
        "status": "STARTED",
        "original_sha256": sha256(original),
        "candidate_sha256": None,
        "model": None,
        "usage": {},
        "checks": {},
        "tests_executed": False,
        "human_review": "PENDING",
        "production_deployment": False,
    }

    try:
        client = ModelClient()
        repair = RepairAgent(client)

        result["model"] = client.model

        print("正在调用真实 DeepSeek Repair Agent...")

        message = repair.run(
            code_path=repaired,
            failure_output=failure_context,
        )

        result["message"] = message
        result["usage"] = client.last_usage or {}
        result["candidate_sha256"] = sha256(repaired)

        checks = inspect_candidate(repaired)
        result["checks"] = checks

        required = (
            "python_syntax",
            "ruff_lint",
            "basic_security_scan",
        )

        if all(checks.get(key) is True for key in required):
            result["status"] = "REPAIR_CANDIDATE_READY"

            print("真实 AI 修复候选生成成功。")
            print("基础静态检查：通过")
            print("功能测试：尚未执行")
        else:
            result["status"] = "STATIC_CHECKS_FAILED"

            print("已生成修复候选，但静态检查未通过。")
            print("检查详情：", checks.get("notes", []))

    except Exception as exc:
        result["status"] = "REPAIR_FAILED"
        result["error"] = f"{type(exc).__name__}: {exc}"

        # 如果修复请求失败，删除未完成的修复副本，
        # 原始 candidate.py 保持不变。
        if repaired.exists():
            repaired.unlink()

        print("AI 修复失败：", result["error"])

    save_result(result_file, result)

    print("运行记录：", result_file)
    print("Token 统计：", result["usage"])
    print("人工审核：待完成")

    return (
        0
        if result["status"] == "REPAIR_CANDIDATE_READY"
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
