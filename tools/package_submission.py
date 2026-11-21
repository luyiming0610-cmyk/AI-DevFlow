
"""Package B11 submission from a reviewed Git repository."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ROOT_FILES = [
    "01_Team_Proposal.md",
    "README.md",
    "EVIDENCE.md",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "main.py",
    "dashboard.py",
    "review.py",
    "check_api.py",
    "repair_existing_task.py",
    "validate_api_candidate.py",
    "verify_api_repair.py",
]

FOLDERS = [
    "agents",
    "core",
    "acceptance",
    "tests",
    "experiments",
    "docker",
    "evidence",
    "pages",
    "reports",
    "tools",
    "workspace/requirements",
    ".github/workflows",
]

MANDATORY = [
    "core/auto_pipeline.py",
    "core/isolated_tester.py",
    "acceptance/test_log_contract.py",
    "experiments/demo_red_green.py",
    "pages/01_新建研发任务.py",
    ".github/workflows/ci.yml",
    "evidence/real_api/20261121-085152-bc4b86/"
    "round_02/validation/pytest.txt",
    "evidence/red_green/20261121-091420-597571/"
    "red_fault_validation/pytest.txt",
    "evidence/red_green/20261121-091420-597571/"
    "repair_01_validation/pytest.txt",
    "evidence/real_api/20261121-102456-2bf362/"
    "round_01/validation/pytest.txt",
]

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "runs",
}

PATTERNS = [
    re.compile(rb"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(
        rb"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}"
    ),
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def run_git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def safe_file(path: Path) -> bool:
    rel = path.relative_to(ROOT)

    if path.is_symlink() or not path.is_file():
        return False

    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False

    # Keep the public config template, never include secrets.
    if rel.as_posix() != ".env.example":
        if any(
            part == ".env" or part.startswith(".env.")
            for part in rel.parts
        ):
            return False

    if path.suffix in {
        ".pyc", ".pyo", ".bak", ".swp", ".tmp"
    }:
        return False

    if path.name.endswith(".log"):
        return False

    return True


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            hasher.update(chunk)

    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create final B11 submission ZIP"
    )

    parser.add_argument("--name", required=True)
    parser.add_argument("--last4", required=True)
    parser.add_argument(
        "--video", required=True, type=Path
    )

    args = parser.parse_args()

    if not re.fullmatch(r"\d{4}", args.last4):
        parser.error("--last4 must be four digits")

    if (
        not args.name.strip()
        or any(
            char in args.name
            for char in '/\\:*?"<>|'
        )
    ):
        parser.error("Invalid submission name")

    video = args.video.resolve()

    if (
        not video.is_file()
        or video.suffix.lower() != ".mp4"
    ):
        parser.error(
            "--video must reference an existing MP4"
        )

    if run_git("status", "--porcelain"):
        raise SystemExit(
            "Git working tree is not clean. "
            "Review and commit changes first."
        )

    if run_git("branch", "--show-current") != "main":
        raise SystemExit(
            "Please package from the main branch."
        )

    paths: dict[str, Path] = {}

    for relative in ROOT_FILES:
        path = ROOT / relative

        if path.is_file() and safe_file(path):
            paths[relative] = path

    for folder in FOLDERS:
        base = ROOT / folder

        if not base.is_dir():
            continue

        for path in base.rglob("*"):
            if safe_file(path):
                relative = (
                    path.relative_to(ROOT).as_posix()
                )
                paths[relative] = path

    required = [
        *MANDATORY,
        "01_Team_Proposal.md",
        "README.md",
        "EVIDENCE.md",
        "requirements.txt",
    ]

    missing = [
        item
        for item in required
        if item not in paths
    ]

    if missing:
        raise SystemExit(
            "Missing submission files:\n"
            + "\n".join(missing)
        )

    suspicious = []

    for relative, path in paths.items():
        data = path.read_bytes()

        if any(
            pattern.search(data)
            for pattern in PATTERNS
        ):
            suspicious.append(relative)

    if suspicious:
        raise SystemExit(
            "Possible credentials detected in:\n"
            + "\n".join(suspicious)
        )

    output = (
        ROOT
        / "dist"
        / (
            f"B11-{args.name.strip()}"
            f"-{args.last4}.zip"
        )
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    commit = run_git("rev-parse", "HEAD")
    hashes = []

    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as bundle:

        for relative, path in sorted(paths.items()):
            bundle.write(path, relative)

            hashes.append(
                f"{digest_file(path)}  {relative}"
            )

        bundle.write(
            video,
            "demo.mp4",
            compress_type=zipfile.ZIP_STORED,
        )

        hashes.append(
            f"{digest_file(video)}  demo.mp4"
        )

        bundle.writestr(
            "COMMIT.txt",
            commit + "\n",
        )

        bundle.writestr(
            "SHA256SUMS.txt",
            "\n".join(hashes) + "\n",
        )

    with zipfile.ZipFile(output) as bundle:
        if bundle.testzip() is not None:
            raise SystemExit(
                "ZIP integrity check failed."
            )

        print("Created:", output)
        print("Files:", len(bundle.namelist()))
        print("Git commit:", commit)
        print("Video:", video.name)
        print(
            "Confirm video duration <= 5 minutes."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
