
"""Run trusted acceptance tests against AI-generated code inside Docker."""

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid

from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE = "aidevflow-test:1"


def find_docker_executable() -> str | None:
    """
    Locate Docker on Windows or Linux.

    Supports:
    1. AI_DEVFLOW_DOCKER environment variable
    2. System PATH
    3. Docker Desktop per-user installation
    4. Docker Desktop all-users installation
    """
    explicit = os.environ.get("AI_DEVFLOW_DOCKER", "").strip().strip('"')

    candidates = [
        explicit or None,
        shutil.which("docker.exe"),
        shutil.which("docker"),
    ]

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(
            str(
                Path(local_app_data)
                / "Programs"
                / "DockerDesktop"
                / "resources"
                / "bin"
                / "docker.exe"
            )
        )

    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(
            str(
                Path(program_files)
                / "Docker"
                / "Docker"
                / "resources"
                / "bin"
                / "docker.exe"
            )
        )

    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate).resolve())

    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_candidate(
    candidate: Path,
    output_dir: Path,
    acceptance_file: Path | None = None,
) -> dict:
    """
    Run acceptance tests inside a restricted Docker container.

    Never run AI-generated candidate code directly on the host.
    """
    candidate = candidate.resolve()
    output_dir = output_dir.resolve()

    
    acceptance = (
        acceptance_file
        if acceptance_file is not None
        else ROOT / "acceptance" / "test_log_contract.py"
    ).resolve()

    trusted_dir = (ROOT / "acceptance").resolve()

    if (
        acceptance.parent != trusted_dir
        or acceptance.name not in {
            "test_log_contract.py",
            "test_log_holdout.py",
        }
    ):
        raise ValueError(
            "仅允许项目内已批准的验收测试文件。"
        )


    if not candidate.is_file():
        raise FileNotFoundError(
            f"未找到候选代码：{candidate}"
        )

    if not acceptance.is_file():
        raise FileNotFoundError(
            f"未找到验收测试：{acceptance}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    tree = ast.parse(
        acceptance.read_text(encoding="utf-8")
    )

    expected_count = sum(
        isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
        for node in tree.body
    )

    report = {
        "expected_tests": expected_count,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_sha256": sha256(candidate),
        "acceptance_sha256": sha256(acceptance),
        "image": IMAGE,
        "status": "BLOCKED",
        "tests_executed": False,
        "return_code": None,
        "passed_count": 0,
        "failed_count": 0,
        "human_review": "PENDING",
        "production_deployment": False,
    }

    def save(log: str) -> dict:
        (output_dir / "pytest.txt").write_text(
            log,
            encoding="utf-8",
        )

        (output_dir / "validation.json").write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return report

    # Locate the Docker executable.
    docker = find_docker_executable()

    if docker is None:
        report["reason"] = (
            "无法定位 docker.exe，"
            "禁止在宿主机直接执行 AI 生成代码。"
        )
        return save(report["reason"])

    # Check that the test image exists.
    try:
        check = subprocess.run(
            [docker, "image", "inspect", IMAGE],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report["reason"] = (
            f"Docker 检查失败："
            f"{type(exc).__name__}: {exc}"
        )
        return save(report["reason"])

    if check.returncode != 0:
        report["reason"] = (
            f"测试镜像不存在或 Docker 不可用，"
            f"请先构建 {IMAGE}。"
        )
        return save(report["reason"])

    # Prepare a temporary read-only test workspace.
    with tempfile.TemporaryDirectory(
        prefix="aidevflow-check-"
    ) as directory:

        work = Path(directory)

        generated_dir = work / "workspace" / "generated"
        acceptance_dir = work / "acceptance"

        generated_dir.mkdir(parents=True)
        acceptance_dir.mkdir()

        shutil.copy2(
            candidate,
            generated_dir / "analyzer.py",
        )

        shutil.copy2(
            acceptance,
            acceptance_dir / "test_log_contract.py",
        )

        
        # Linux: tempfile defaults to mode 0700.
        # The Docker container runs as uid 65534 and needs read access.
        # These temporary files contain only candidate source and tests.
        if os.name == "posix":
            for directory_path in (
                work,
                work / "workspace",
                work / "workspace" / "generated",
                work / "acceptance",
            ):
                directory_path.chmod(0o755)

            for file_path in (
                work / "workspace" / "generated" / "analyzer.py",
                work / "acceptance" / "test_log_contract.py",
            ):
                file_path.chmod(0o644)

        container_name = (
            "aidevflow-" + uuid.uuid4().hex[:12]
        )

        args = [
            docker,
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "64",
            "--memory",
            "256m",
            "--cpus",
            "1",
            "--user",
            "65534:65534",
            "--tmpfs",
            "/tmp:rw,nosuid,noexec,size=32m",
            "--mount",
            f"type=bind,source={work},target=/work,readonly",
            "--workdir",
            "/work",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            (
                "AI_DEVFLOW_CANDIDATE="
                "/work/workspace/generated/analyzer.py"
            ),
            IMAGE,
            "python",
            "-B",
            "-m",
            "pytest",
            "-v",
            "-p",
            "no:cacheprovider",
            "acceptance/test_log_contract.py",
        ]

        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                check=False,
            )

            log = proc.stdout + "\n" + proc.stderr
            report["return_code"] = proc.returncode

        except subprocess.TimeoutExpired:
            subprocess.run(
                [docker, "rm", "-f", container_name],
                capture_output=True,
                timeout=10,
                check=False,
            )

            report["status"] = "TIMEOUT"
            report["reason"] = (
                "容器测试超过 90 秒，已终止。"
            )

            return save(report["reason"])

        except OSError as exc:
            report["status"] = "INFRA_ERROR"
            report["reason"] = (
                f"无法启动 Docker 测试容器：{exc}"
            )
            return save(report["reason"])

    if report["return_code"] in (125, 126, 127):
        report["status"] = "INFRA_ERROR"
        report["reason"] = (
            "Docker 容器启动失败，"
            "不属于业务代码测试失败。"
        )
        return save(log)

    # Parse pytest results.
    passed = re.findall(
        r"\b(\d+)\s+passed\b",
        log,
    )

    failed = re.findall(
        r"\b(\d+)\s+failed\b",
        log,
    )

    report["passed_count"] = (
        int(passed[-1]) if passed else 0
    )

    report["failed_count"] = (
        int(failed[-1]) if failed else 0
    )

    report["tests_executed"] = (
        report["passed_count"]
        + report["failed_count"]
        > 0
    )

    if (
        report["return_code"] in (2, 3, 4, 5)
        and not report["tests_executed"]
    ):
        report["status"] = "COLLECTION_ERROR"
    else:
        report["status"] = (
            "PASSED"
            if (
                report["return_code"] == 0
                and report["passed_count"] == expected_count
                and expected_count > 0
            )
            else "FAILED"
        )

    return save(log)



def main() -> int:
    """命令行入口：在 Docker 中执行可信验收测试。"""

    parser = argparse.ArgumentParser(
        description="AI DevFlow｜Docker 隔离测试"
    )

    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
        help="需要验证的 AI 候选代码路径",
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="测试日志及结果输出目录",
    )

    parser.add_argument(
        "--acceptance",
        type=Path,
        default=None,
        help="可选验收测试文件；默认运行正式 15 项测试",
    )

    args = parser.parse_args()

    result = run_candidate(
        args.candidate,
        args.output,
        args.acceptance,
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0 if result["status"] == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
