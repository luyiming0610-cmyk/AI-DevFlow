from collections import Counter
from datetime import datetime


def analyze_text(text: str) -> dict:
    success = 0
    failures = Counter()
    events = Counter()
    invalid = 0

    for line in text.splitlines():
        if not line.strip():
            continue

        parts = line.split()

        if len(parts) != 5:
            invalid += 1
            continue

        date, time, level, event_id, action = parts

        try:
            datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            invalid += 1
            continue

        if not event_id.startswith("event_"):
            invalid += 1
            continue

        if level == "INFO" and action == "upload_success":
            success += 1
        elif level == "ERROR":
            failures[action] += 1
        else:
            invalid += 1
            continue

        events[event_id] += 1

    failed = sum(failures.values())

    return {
        "total_records": success + failed,
        "success_count": success,
        "failure_count": failed,
        "invalid_count": invalid,
        "failure_types": dict(failures),
        "events": dict(events),
    }
