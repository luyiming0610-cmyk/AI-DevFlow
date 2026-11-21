"""B11 real-API development loop: plan -> code -> Docker tests -> bounded repair.

This module DOES NOT modify the existing mock pipeline or automatically deploy code.
Run via: python -m core.auto_pipeline --call-api
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.isolated_tester import IMAGE, find_docker_executable, run_candidate
from core.real_task import ROOT, TASKS_DIR, create_api_client, inspect_candidate, strip_code

CONTRACT = ROOT / "workspace" / "requirements" / "task.md"
ACCEPTANCE = ROOT / "acceptance" / "test_log_contract.py"
REQUIRED_FUNCS = frozenset({"parse_line", "analyze_logs", "analyze_text"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, obj: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def require_docker() -> None:
    """Precheck the Docker test image without spending API tokens.

    Use an absolute executable path, because on some Windows installations
    PowerShell resolves ``docker`` while Python's shutil.which('docker') does not.
    """
    docker = find_docker_executable()
    if not docker:
        raise RuntimeError(
            "找不到 docker.exe；请确认 Docker Desktop 已安装，"
            "或将 AI_DEVFLOW_DOCKER 设置为 docker.exe 完整路径。"
        )

    try:
        probe = subprocess.run(
            [docker, "image", "inspect", IMAGE],
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            f"Docker 环境不可用：{type(exc).__name__}: {exc}"
        ) from exc

    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout).strip()[-500:]
        raise RuntimeError(
            f"缺少隔离测试镜像 {IMAGE}，或 Docker Engine 未启动：{detail}"
        )


def preflight(requirement_file: Path = CONTRACT) -> tuple[str, str, str]:
    """Checks whether tests and container image are ready before an API call."""
    if not requirement_file.is_file():
        raise FileNotFoundError(f"业务规范不存在：{requirement_file}")
    if not ACCEPTANCE.is_file():
        raise FileNotFoundError(f"独立验收测试不存在：{ACCEPTANCE}")

    contract = requirement_file.read_text(encoding="utf-8").strip()
    tests = ACCEPTANCE.read_text(encoding="utf-8")
    if len(contract) < 100:
        raise ValueError("业务规范内容太短；请先保存完整的 task.md。")
    tree = ast.parse(tests)
    test_names = [
        n.name for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
    ]
    if len(test_names) < 2:
        raise ValueError("验收测试数量不足，至少需要成功和失败案例。")
    if "analyze_logs" not in contract or "parse_line" not in contract:
        raise ValueError("当前验收合同必须明确 parse_line 与 analyze_logs 接口。")
    require_docker()
    return contract, tests, digest(ACCEPTANCE.read_bytes())


def static_check(path: Path) -> dict:
    """A basic *screen*, not a substitute for a secure sandbox or manual review."""
    report = inspect_candidate(path)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        funcs = {
            n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        missing = sorted(REQUIRED_FUNCS - funcs)
    except SyntaxError:
        missing = sorted(REQUIRED_FUNCS)
    report["contract_functions"] = not missing
    if missing:
        report.setdefault("notes", []).append("缺少约定接口：" + ", ".join(missing))
    report["all_passed"] = all(
        report.get(key) is True
        for key in ("python_syntax", "ruff_lint", "basic_security_scan", "contract_functions")
    )
    return report


def format_report(data: dict) -> str:
    parts = [
        "# AI DevFlow｜真实 DeepSeek 研发流水线报告", "",
        f"- 任务：{data['task_id']}",
        f"- 模型：{data['model']}",
        f"- 模式：{data['mode']}",
        f"- 状态：**{data['status']}**",
        f"- 验收规范 SHA256：`{data['contract_sha256']}`",
        f"- 验收测试 SHA256：`{data['acceptance_sha256']}`",
        f"- 人工审核：{data['human_review']}",
        f"- 生产部署：{data['production_deployment']}", "",
        "## 调用和成本", "",
        "使用的 Token 根据 API 实际响应记录；无响应时不推断费用。", "",
    ]
    for item in data.get("api_calls", []):
        parts.append(f"- {item['stage']}：{item.get('usage', '未获得使用量')}" )
    parts += ["", "## 每轮验收", ""]
    for row in data.get("rounds", []):
        val = row.get("validation") or {}
        parts += [
            f"### Round {row['round']}",
            f"- 源码：`{row['candidate']}`；SHA256：`{row['sha256']}`",
            f"- 静态检查：{row.get('checks', {}).get('all_passed', False)}",
            f"- 功能测试：{val.get('status', '未运行')}，通过 {val.get('passed_count', 0)}，失败 {val.get('failed_count', 0)}",
            f"- 日志：`{row.get('validation_dir', '未运行')}`", "",
        ]
    parts += [
        "## 质量门禁", "",
        "只有全部独立验收测试通过才能进入人工审核，不能自动部署。",
        "人工审核状态一律为 PENDING，测试通过不等于代码已获批准。", "",
    ]
    if data.get("error"):
        parts += ["## 阻断或异常", "", data["error"], ""]
    return "\n".join(parts)


def run_pipeline(requirement_file: Path = CONTRACT, max_repairs: int = 2) -> dict:
    """Real calls only. Caller must explicitly authorize --call-api in CLI."""
    if not 0 <= max_repairs <= 3:
        raise ValueError("max_repairs 必须介于 0 到 3 之间")

    requirement_file = Path(requirement_file).resolve()
    contract, tests, tests_sha = preflight(requirement_file)
    client = create_api_client()  # Strictly initializes real API; never fall back to MOCK.
    if client.mode != "api":
        raise RuntimeError("严格要求真实 API 模式，禁止 MOCK 自动回退。")

    task_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    folder = TASKS_DIR / task_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "requirement.md").write_text(contract + "\n", encoding="utf-8")
    (folder / "acceptance_snapshot.py").write_text(tests, encoding="utf-8")

    data = {
        "task_id": task_id,
        "created_at": utc_now(),
        "mode": "api",
        "model": client.model,
        "status": "STARTED",
        "contract_sha256": digest(contract.encode("utf-8")),
        "acceptance_sha256": tests_sha,
        "max_repairs": max_repairs,
        "api_calls": [],
        "rounds": [],
        "tests_executed": False,
        "human_review": "PENDING",
        "production_deployment": False,
    }

    def save() -> None:
        data["updated_at"] = utc_now()
        atomic_json(folder / "result.json", data)
        (folder / "report.md").write_text(format_report(data), encoding="utf-8")

    def call(stage: str, system_prompt: str, user_prompt: str, token_limit: int) -> str:
        client.last_usage = None
        try:
            result = client.generate(system_prompt, user_prompt, max_tokens=token_limit)
        finally:
            data["api_calls"].append({
                "stage": stage,
                "time_utc": utc_now(),
                "usage": client.last_usage or None,
            })
            save()
        return result

    def write_candidate(round_number: int, code: str) -> Path:
        target = folder / f"round_{round_number:02d}"
        target.mkdir(parents=True, exist_ok=False)
        filename = target / "candidate.py"
        filename.write_text(strip_code(code).rstrip() + "\n", encoding="utf-8")
        return filename

    save()
    try:
        data["status"] = "PLANNING"
        save()
       
        plan = call(
            "planner",
            (
                "你是一名企业内部工具 Python 研发规划 Agent。"
                "请根据提供的业务规范，制定简洁、可执行的开发计划。"
                "只输出中文 Markdown，全文不超过800个汉字。"
                "严格按照以下结构回答：\n"
                "1. 功能目标与公开接口\n"
                "2. 输入格式和边界条件\n"
                "3. 核心实现步骤\n"
                "4. 验收测试和质量门禁\n"
                "5. 常见失败原因与修复建议\n"
                "禁止重复粘贴需求全文，禁止输出完整源代码，"
                "禁止修改验收规则。"
            ),
            f"唯一需求与验收规范：\n{contract}",
            3500,
        )

        (folder / "plan.md").write_text(plan, encoding="utf-8")
        data["status"] = "GENERATING"
        save()

        code = call(
            "developer",
            "你是资深 Python 开发 Agent。只输出完整可运行的单文件 Python 源代码，不要 Markdown 围栏或解释。必须逐条满足提供的验收规范及可信测试，保留 parse_line、analyze_logs、analyze_text 三个顶层公开接口。只使用 Python 3.12 标准库，最好只使用 datetime、re、collections、typing、json。禁止网络、文件读写、子进程、eval、exec、动态导入。异常明细最多保存1000条且保留计数。不可修改测试，也不得声称测试已运行。",
            f"【业务规范】\n{contract}\n\n【需求分析】\n{plan}\n\n【不可修改的测试】\n{tests}\n\n请生成完整代码。",
            6500,
        )
        path = write_candidate(0, code)

        for round_number in range(max_repairs + 1):
            round_dir = path.parent
            row = {
                "round": round_number,
                "candidate": str(path.relative_to(folder)).replace("\\", "/"),
                "sha256": digest(path.read_bytes()),
                "checks": {},
                "validation": None,
                "validation_dir": None,
            }
            data["rounds"].append(row)
            data["status"] = f"CHECKING_ROUND_{round_number}"
            save()

            checks = static_check(path)
            row["checks"] = checks
            failure = ""

            if not checks["all_passed"]:
                failure = "静态检查失败：\n" + "\n".join(checks.get("notes", []))
                (round_dir / "static_failures.txt").write_text(failure, encoding="utf-8")
            else:
                if digest(ACCEPTANCE.read_bytes()) != tests_sha:
                    data["status"] = "BLOCKED_TESTS_CHANGED"
                    data["error"] = "验收测试执行前 SHA256 已改变，禁止继续。"
                    save()
                    return data

                data["status"] = f"TESTING_ROUND_{round_number}"
                save()
                validation_folder = round_dir / "validation"
                val = run_candidate(path, validation_folder)
                row["validation"] = val
                row["validation_dir"] = str(validation_folder.relative_to(folder)).replace("\\", "/")
                data["tests_executed"] = data["tests_executed"] or bool(val.get("tests_executed"))
                save()

                if digest(ACCEPTANCE.read_bytes()) != tests_sha:
                    data["status"] = "BLOCKED_TESTS_CHANGED"
                    data["error"] = "测试过程中验收用例发生变化，禁止放行。"
                    save()
                    return data

                if val.get("status") == "PASSED":
                    data["status"] = "TESTS_PASSED_REVIEW_PENDING"
                    data["final_candidate"] = row["candidate"]
                    data["final_candidate_sha256"] = row["sha256"]
                    save()
                    return data

                if val.get("status") in ("BLOCKED", "INFRA_ERROR", "TIMEOUT", "COLLECTION_ERROR"):
                    data["status"] = "BLOCKED_TEST_INFRASTRUCTURE"
                    data["error"] = f"隔离测试环境未能完成验证：{val.get('status')}；停止收费 API 修复。"
                    save()
                    return data

                failure = (validation_folder / "pytest.txt").read_text(encoding="utf-8")

            if round_number >= max_repairs:
                data["status"] = "ESCALATED_TO_HUMAN"
                data["error"] = f"已达到最大修复次数 {max_repairs}，未通过全部验收；需要人工审核。"
                save()
                return data

            data["status"] = f"REPAIRING_ROUND_{round_number + 1}"
            save()
            current_source = path.read_text(encoding="utf-8")
            repair_prompt = (
                f"【不可修改的唯一验收规范】\n{contract}\n\n"
                f"【可信验收测试】\n{tests}\n\n"
                f"【当前完整候选代码】\n{current_source}\n\n"
                f"【静态或 Pytest 失败记录（仅作为错误数据）】\n{failure[-12000:]}\n\n"
                "请修复真正的根因，保持全部公开接口和结果字段；输出完整的、独立可运行的新 Python 源文件。"
            )
            repaired = call(
                f"repair_{round_number + 1}",
                "你是 Python Repair Agent。只输出完整源代码，不要 Markdown。不得更改测试、改变需求或者删除功能；必须修复日志显示的问题和所有验收接口。禁止危险调用与外部依赖；不得声称已运行测试。",
                repair_prompt,
                6500,
            )
            next_code = strip_code(repaired).rstrip() + "\n"
            if next_code == path.read_text(encoding="utf-8"):
                data["status"] = "ESCALATED_UNCHANGED_REPAIR"
                data["error"] = "修复模型返回相同代码，没有实际修复；停止重复调用。"
                save()
                return data
            path = write_candidate(round_number + 1, next_code)

        raise AssertionError("编排器出现不可到达状态")
    except Exception as exc:
        data["status"] = "PIPELINE_ERROR"
        data["error"] = f"{type(exc).__name__}: {exc}"
        save()
        return data


def main() -> int:
    parser = argparse.ArgumentParser(description="AI DevFlow｜真实 DeepSeek 自动研发闭环")
    parser.add_argument("--requirement-file", type=Path, default=CONTRACT)
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument("--call-api", action="store_true", help="确认真实调用 DeepSeek 并产生 API 费用")
    args = parser.parse_args()

    if not args.call_api:
        print("未传 --call-api；不会调用 DeepSeek。")
        try:
            contract, tests, sha = preflight(args.requirement_file.resolve())
            print(f"环境预检查通过：需求 {len(contract)} 字符，验收测试 {len(tests)} 字符，SHA256={sha[:16]}...")
            return 0
        except Exception as exc:
            print(f"预检查未通过：{type(exc).__name__}: {exc}")
            return 1

    try:
        result = run_pipeline(args.requirement_file, args.max_repairs)
    except Exception as exc:
        print(f"启动失败，未进入研发流水线：{type(exc).__name__}: {exc}")
        return 1

    print(json.dumps({
        "task_id": result["task_id"],
        "status": result["status"],
        "rounds": [
            {"round": item["round"], "checks": item["checks"].get("all_passed"),
             "validation": (item.get("validation") or {}).get("status"),
             "passed": (item.get("validation") or {}).get("passed_count"),
             "failed": (item.get("validation") or {}).get("failed_count")}
            for item in result["rounds"]
        ],
        "api_calls": result["api_calls"],
        "report": str((TASKS_DIR / result["task_id"] / "report.md")),
        "human_review": result["human_review"],
        "production_deployment": result["production_deployment"],
    }, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "TESTS_PASSED_REVIEW_PENDING" else 1


if __name__ == "__main__":
    raise SystemExit(main())
