
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent

TRIAL = ROOT / "runs" / "api_repair_trial"
CANDIDATE = TRIAL / "analyzer.py"
ORIGINAL_RESULT = TRIAL / "result.json"

TESTS = ROOT / "tests"

LOG_PATH = ROOT / "reports" / "api_repair_pytest.txt"
RESULT_PATH = ROOT / "reports" / "api_repair_validation.json"


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def validate_source(source: str) -> None:
    """
    对当前已人工查看的候选进行基础检查。
    这不是通用安全沙箱。
    """
    tree = ast.parse(source)

    allowed_imports = {
        "collections": {"Counter"},
        "datetime": {"datetime"},
    }

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            allowed_names = allowed_imports.get(
                node.module
            )

            imported_names = {
                alias.name
                for alias in node.names
            }

            if (
                node.level != 0
                or allowed_names is None
                or not imported_names <= allowed_names
            ):
                raise RuntimeError(
                    "候选代码包含未批准的导入。"
                )

        elif (
            isinstance(node, ast.FunctionDef)
            and node.name == "analyze_text"
        ):
            continue

        else:
            raise RuntimeError(
                "候选代码包含未批准的顶层语句。"
            )

    forbidden_calls = {
        "eval",
        "exec",
        "open",
        "compile",
        "__import__",
        "input",
        "breakpoint",
    }

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if node not in tree.body:
                raise RuntimeError(
                    "函数内部存在额外导入。"
                )

        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in forbidden_calls
            ):
                raise RuntimeError(
                    "候选代码包含禁止的动态调用。"
                )


def main() -> int:
    if not CANDIDATE.exists():
        print("错误：找不到 DeepSeek 修复候选。")
        return 1

    if not ORIGINAL_RESULT.exists():
        print("错误：找不到原始 API 实验记录。")
        return 1

    if not TESTS.exists():
        print("错误：找不到原始测试目录。")
        return 1

    original = json.loads(
        ORIGINAL_RESULT.read_text(encoding="utf-8")
    )

    expected_hash = original.get(
        "candidate_sha256"
    )

    actual_hash = file_hash(CANDIDATE)

    if expected_hash != actual_hash:
        print(
            "错误：候选代码与 API 实验记录"
            "中的 SHA256 不一致。"
        )
        return 1

    source = CANDIDATE.read_text(
        encoding="utf-8"
    )

    try:
        validate_source(source)
    except Exception as exc:
        print("基础检查未通过：", exc)
        return 1

    print("候选代码哈希校验通过。")
    print("基础静态检查通过。")
    print("开始在独立临时目录运行原始测试。")

    with tempfile.TemporaryDirectory(
        prefix="aidevflow-api-test-"
    ) as temp:
        temp_root = Path(temp)

        target = (
            temp_root
            / "workspace"
            / "generated"
        )

        target.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            CANDIDATE,
            target / "analyzer.py",
        )

        shutil.copytree(
            TESTS,
            temp_root / "tests",
            ignore=shutil.ignore_patterns(
                "__pycache__",
                ".pytest_cache",
            ),
        )

        environment = os.environ.copy()

        # 测试进程不需要模型密钥
        environment.pop("AI_API_KEY", None)
        environment.pop("DEEPSEEK_API_KEY", None)

        environment["AI_MODE"] = "mock"
        environment["PYTHONPATH"] = str(temp_root)
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

        try:
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests",
                    "-v",
                    "-p",
                    "no:cacheprovider",
                ],
                cwd=temp_root,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
            )

            output = (
                process.stdout
                + "\n"
                + process.stderr
            )

            exit_code = process.returncode

        except subprocess.TimeoutExpired:
            output = "测试执行超时（60 秒）。"
            exit_code = -1

    LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    LOG_PATH.write_text(
        output,
        encoding="utf-8",
    )

    test_counts = re.findall(
        r"(\d+)\s+passed",
        output,
    )

    passed_count = (
        int(test_counts[-1])
        if test_counts
        else 0
    )

    # 验证同一套 3 个验收测试
    passed = (
        exit_code == 0
        and passed_count == 3
    )

    result = {
        "model": original.get("model"),
        "source": "DeepSeek API repair candidate",
        "candidate_sha256": actual_hash,
        "test_suite": "tests/test_analyzer.py",
        "tests_executed": True,
        "test_exit_code": exit_code,
        "passed_count": passed_count,
        "validation_status": (
            "PASSED" if passed else "FAILED"
        ),
        "human_review": "PENDING",
        "production_deployment": False,
        "test_log": "reports/api_repair_pytest.txt",
    }

    RESULT_PATH.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(output)

    if passed:
        print("真实 DeepSeek 候选：3 项测试通过。")
    else:
        print("真实 DeepSeek 候选：验证未通过。")

    print("人工审核状态：待审核")
    print("报告：", RESULT_PATH)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
