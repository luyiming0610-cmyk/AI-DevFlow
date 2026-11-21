
"""Scan Git candidate files for common credential patterns.

Only prints filenames and line numbers, never secret values.
Does not access .env or make network requests.
"""

import re
import subprocess
from pathlib import Path


PATTERNS = {
    "API key": re.compile(
        rb"sk-[A-Za-z0-9_-]{16,}"
    ),
    "GitHub token": re.compile(
        rb"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}"
    ),
    "AWS access key": re.compile(
        rb"AKIA[0-9A-Z]{16}"
    ),
    "Private key": re.compile(
        rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    ),
}


def main() -> int:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        ],
        check=True,
        capture_output=True,
    )

    paths = [
        Path(raw.decode("utf-8"))
        for raw in result.stdout.split(b"\0")
        if raw
    ]

    scanned = 0
    findings = []
    errors = []

    for path in paths:
        if not path.is_file():
            continue

        scanned += 1

        try:
            with path.open("rb") as file:
                for line_number, line in enumerate(file, 1):
                    for name, pattern in PATTERNS.items():
                        if pattern.search(line):
                            findings.append(
                                (str(path), line_number, name)
                            )
        except OSError:
            errors.append(str(path))

    print(f"Scanned files: {scanned}")

    if findings:
        print("\nPotential secrets found:")

        for filename, line_number, kind in findings:
            print(
                f"{filename}:{line_number} ({kind})"
            )
    else:
        print("Potential secrets: NONE")

    if errors:
        print("\nFiles that could not be scanned:")
        for filename in errors:
            print(filename)

    if findings or errors:
        print("\nRESULT: REVIEW REQUIRED")
        return 1

    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
