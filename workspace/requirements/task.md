
# Event Image Upload Log Analyzer

## Business Background

A sports event image platform needs an internal tool
to analyze image upload logs.

## Requirements

Build a Python log analysis tool that:

1. Reads event upload logs from a text file.
2. Counts the total number of valid records.
3. Counts successful and failed uploads.
4. Groups upload failures by error type.
5. Groups records by event ID.
6. Handles empty lines and malformed records.
7. Produces JSON and Markdown reports.

## Example Input

2026-11-20 09:01:12 INFO event_001 upload_success
2026-11-20 09:02:15 ERROR event_001 upload_timeout
2026-11-20 09:03:21 ERROR event_002 connection_failed
2026-11-20 09:04:10 INFO event_002 upload_success

## Acceptance Criteria

- Valid records are parsed correctly.
- Invalid records do not crash the program.
- Success and failure counts are accurate.
- Failure categories are reported.
- Automated unit tests are provided.
- The tool can be executed from the command line.

## Constraints

- Python 3.12
- No production credentials
- No real customer data
- No network access required by the generated tool
