
import ast
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from core.model_client import ModelClient


ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "runs" / "interactive_tasks"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def strip_code(text: str) -> str:
    code = text.strip()

    if code.startswith("```"):
        lines = code.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        code = "\n".join(lines).strip()

    return code


def create_api_client() -> ModelClient:
    load_dotenv(ROOT / ".env")

    # 临时使用 API 模式创建客户端，
    # 不修改用户的 .env 文件。
    previous = os.environ.get("AI_MODE")
    os.environ["AI_MODE"] = "api"

    try:
        client = ModelClient()
    finally:
        if previous is None:
            os.environ.pop("AI_MODE", None)
        else:
            os.environ["AI_MODE"] = previous

    return client


def inspect_candidate(code_path: Path) -> dict:
    """静态检查，不执行模型生成的代码。"""

    result = {
        "python_syntax": False,
        "ruff_lint": False,
        "basic_security_scan": False,
        "notes": [],
    }

    source = code_path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source)
        result["python_syntax"] = True
    except SyntaxError as exc:
        result["notes"].append(
            f"语法错误：第 {exc.lineno} 行：{exc.msg}"
        )
        return result

    allowed_imports = {
        "collections",
        "datetime",
        "re",
        "json",
        "typing",
        "statistics",
    }

    forbidden_calls = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "breakpoint",
    }

    risks = []

    functions = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    ]

    if "analyze_text" not in functions:
        risks.append("缺少 analyze_text 函数")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]

                if module not in allowed_imports:
                    risks.append(
                        f"未批准的导入：{alias.name}"
                    )

        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]

            if node.level or module not in allowed_imports:
                risks.append(
                    f"未批准的导入：{node.module}"
                )

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in forbidden_calls:
                    risks.append(
                        f"禁止的函数调用：{node.func.id}"
                    )

    result["basic_security_scan"] = not risks
    result["notes"].extend(risks)

    try:
        lint = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                str(code_path),
                "--select",
                "E4,E7,E9,F",
                "--no-cache",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )

        result["ruff_lint"] = lint.returncode == 0

        if lint.returncode != 0:
            result["notes"].append(
                (lint.stdout + lint.stderr)[:2000]
            )

    except (OSError, subprocess.TimeoutExpired) as exc:
        result["notes"].append(
            f"Ruff 执行失败：{type(exc).__name__}"
        )

    return result


def build_task_report(record: dict) -> str:
    checks = record.get("checks", {})
    usage = record.get("usage", {})

    lines = [
        "# AI DevFlow｜真实 AI 研发任务报告",
        "",
        f"- 任务编号：{record['task_id']}",
        f"- 创建时间：{record['created_at']}",
        f"- 模型：{record['model']}",
        f"- 状态：{record['status']}",
        "",
        "## 一、开发需求",
        "",
        record["requirement"],
        "",
        "## 二、模型调用",
        "",
        f"- 需求分析 Token：{usage.get('planner', {})}",
        f"- 代码生成 Token：{usage.get('developer', {})}",
        "",
        "## 三、代码静态检查",
        "",
        f"- Python 语法：{checks.get('python_syntax')}",
        f"- Ruff：{checks.get('ruff_lint')}",
        f"- 基础安全规则：{checks.get('basic_security_scan')}",
        "",
        "## 四、测试与审核",
        "",
        "- 功能测试：未执行",
        "- 人工审核：PENDING",
        "- 生产环境部署：未执行",
        "",
        "## 五、说明",
        "",
        "本次是真实 DeepSeek 需求分析与代码生成实验。",
        "模型生成的代码已保存，但未直接执行。",
        "静态检查不能替代受限执行环境和人工审核。",
    ]

    if record.get("error"):
        lines.extend([
            "",
            "## 六、错误记录",
            "",
            record["error"],
        ])

    return "\n".join(lines) + "\n"


def run_real_task(requirement: str) -> dict:
    requirement = requirement.strip()

    if len(requirement) < 20:
        raise ValueError("请至少输入 20 个字符的需求。")

    if len(requirement) > 3000:
        raise ValueError("需求不能超过 3000 个字符。")

    task_id = (
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        + "-"
        + uuid.uuid4().hex[:6]
    )

    task_dir = TASKS_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=False)

    record = {
        "task_id": task_id,
        "created_at": now_utc(),
        "requirement": requirement,
        "model": "",
        "status": "STARTED",
        "usage": {},
        "checks": {},
        "tests_executed": False,
        "human_review": "PENDING",
        "production_deployment": False,
    }

    record_path = task_dir / "result.json"

    def persist() -> None:
        save_json(record_path, record)

        (task_dir / "report.md").write_text(
            build_task_report(record),
            encoding="utf-8",
        )

    (task_dir / "requirement.md").write_text(
        "# 研发需求\n\n" + requirement + "\n",
        encoding="utf-8",
    )

    persist()

    try:
        client = create_api_client()
        record["model"] = client.model

        # 第一阶段：真实 AI 需求分析
        plan = client.generate(
            system_prompt=(
                "你是一名 Python 研发规划 Agent。"
                "请针对内部日志分析工具制定简短、可执行的"
                "中文开发计划。包括接口、边界条件、"
                "验收标准、风险及检查步骤。"
                "只输出 Markdown，不要输出代码。"
            ),
            user_prompt=requirement,
            max_tokens=1200,
        )

        (task_dir / "plan.md").write_text(
            plan,
            encoding="utf-8",
        )

        record["usage"]["planner"] = (
            client.last_usage or {}
        )
        record["status"] = "PLAN_GENERATED"
        persist()

        # 第二阶段：真实 AI 编写 Python 代码
        # 本期限定日志分析场景，以便复用
        # 已有的独立验收用例。
        code = client.generate(
            system_prompt=(
                "你是一名 Python 开发 Agent。"
                "根据需求和计划，编写一个完整 Python 模块。"
                "只返回 Python 源码，不要 Markdown 标记。"
                "必须提供 analyze_text(text: str) -> dict。"
                "日志格式为："
                "YYYY-MM-DD HH:MM:SS LEVEL event_ID ACTION。"
                "必须识别格式错误和非法日期。"
                "输出字典必须包含："
                "total_records、success_count、failure_count、"
                "invalid_count、failure_types、events。"
                "INFO upload_success 记作成功；"
                "ERROR 记作失败。"
                "不允许网络、文件读写、子进程、"
                "eval、exec 或额外依赖。"
                "不要编造测试已通过的结论。"
            ),
            user_prompt=(
                f"需求：\n{requirement}\n\n"
                f"开发计划：\n{plan}"
            ),
            max_tokens=2400,
        )

        candidate = strip_code(code)
        code_path = task_dir / "candidate.py"

        code_path.write_text(
            candidate.rstrip() + "\n",
            encoding="utf-8",
        )

        record["usage"]["developer"] = (
            client.last_usage or {}
        )

        record["candidate_sha256"] = hashlib.sha256(
            code_path.read_bytes()
        ).hexdigest()

        record["checks"] = inspect_candidate(code_path)

        if all([
            record["checks"]["python_syntax"],
            record["checks"]["ruff_lint"],
            record["checks"]["basic_security_scan"],
        ]):
            record["status"] = "STATIC_CHECKS_PASSED"
        else:
            record["status"] = "STATIC_CHECKS_FAILED"

    except Exception as exc:
        record["status"] = "FAILED"
        record["error"] = (
            f"{type(exc).__name__}: {exc}"
        )

    persist()
    return record


def read_task_files(task_id: str) -> dict:
    task_dir = TASKS_DIR / task_id

    # 任务标识只允许使用目录名称，不接受路径。
    if task_id != Path(task_id).name:
        raise ValueError("无效任务编号")

    return {
        "plan": (
            (task_dir / "plan.md").read_text(
                encoding="utf-8"
            )
            if (task_dir / "plan.md").exists()
            else ""
        ),
        "code": (
            (task_dir / "candidate.py").read_text(
                encoding="utf-8"
            )
            if (task_dir / "candidate.py").exists()
            else ""
        ),
        "report": (
            (task_dir / "report.md").read_text(
                encoding="utf-8"
            )
            if (task_dir / "report.md").exists()
            else ""
        ),
    }
