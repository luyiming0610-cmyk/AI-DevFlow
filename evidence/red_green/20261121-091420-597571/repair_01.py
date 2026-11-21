"""赛事影像上传日志分析工具。

只使用 Python 3.12 标准库（datetime、re、collections 等），
纯离线计算，无文件读写、网络、子进程、eval/exec 或动态导入。
"""

import re
from collections import OrderedDict
from datetime import datetime

__all__ = ["parse_line", "analyze_logs", "analyze_text"]

_MAX_DETAILS = 1000

_DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
_TIME_RE = re.compile(r"\A\d{2}:\d{2}:\d{2}\Z")
_EVENT_RE = re.compile(r"\A[A-Za-z0-9_-]+\Z")
_FAILED_RE = re.compile(r"\Aupload_failed:(.*)\Z", re.DOTALL)

_LEVELS = frozenset({"INFO", "ERROR"})
_FAILURE_ACTIONS = frozenset({"upload_timeout", "connection_failed"})

_REASON_DATE = "invalid date"
_REASON_FIELD_COUNT = "invalid field count"
_REASON_LEVEL = "invalid level"
_REASON_EVENT = "invalid event id"
_REASON_TIME_FORMAT = "invalid time format"
_REASON_TIME_RANGE = "invalid time range"
_REASON_ACTION_MISMATCH = "level action mismatch"
_REASON_ACTION_UNKNOWN = "unknown action"
_REASON_NON_STRING = "invalid line type"
_REASON_UNDECODABLE = "undecodable bytes"
_REASON_EMPTY = "empty line"


def _normalise_failure_type(raw):
    return raw.strip().lower()


def _classify_action(level, action):
    """返回 (kind, failure_type) 或错误原因字符串。"""
    if level == "INFO":
        if action == "upload_success":
            return ("success", None)
        if action == "upload_timeout" or action == "connection_failed":
            return _REASON_ACTION_MISMATCH
        if _FAILED_RE.match(action):
            return _REASON_ACTION_MISMATCH
        return _REASON_ACTION_UNKNOWN

    # level == "ERROR"
    if action == "upload_success":
        return _REASON_ACTION_MISMATCH
    if action in _FAILURE_ACTIONS:
        return ("failure", action)
    match = _FAILED_RE.match(action)
    if match is not None:
        reason = _normalise_failure_type(match.group(1))
        if not reason:
            return _REASON_ACTION_UNKNOWN
        return ("failure", reason)
    return _REASON_ACTION_UNKNOWN


def _parse_fields(fields):
    date_s, time_s, level, event_id, action = fields

    date_ok = False
    if _DATE_RE.match(date_s):
        try:
            datetime.strptime(date_s, "%Y-%m-%d")
            date_ok = True
        except ValueError:
            date_ok = False

    if not date_ok:
        return None, _REASON_DATE

    if not _TIME_RE.match(time_s):
        return None, _REASON_TIME_FORMAT
    hour = int(time_s[0:2])
    minute = int(time_s[3:5])
    second = int(time_s[6:8])
    if hour > 23 or minute > 59 or second > 59:
        return None, _REASON_TIME_RANGE

    if level not in _LEVELS:
        return None, _REASON_LEVEL

    if not _EVENT_RE.match(event_id):
        return None, _REASON_EVENT

    classified = _classify_action(level, action)
    if isinstance(classified, str):
        return None, classified

    kind, failure_type = classified
    return (
        {
            "date": date_s,
            "time": time_s,
            "level": level,
            "event_id": event_id,
            "action": action,
            "kind": kind,
            "failure_type": failure_type,
        },
        None,
    )


def _decode_line(line):
    if isinstance(line, str):
        return line, None
    if isinstance(line, (bytes, bytearray, memoryview)):
        try:
            return bytes(line).decode("utf-8"), None
        except UnicodeDecodeError:
            return None, _REASON_UNDECODABLE
    return None, _REASON_NON_STRING


def parse_line(line):
    """解析单行日志，合法返回标准化记录，非法返回 None。"""
    if isinstance(line, str):
        text = line
    elif isinstance(line, (bytes, bytearray, memoryview)):
        try:
            text = bytes(line).decode("utf-8")
        except UnicodeDecodeError:
            return None
    else:
        return None

    text = text.rstrip("\r\n")
    fields = text.split()
    if len(fields) != 5:
        return None

    record, _ = _parse_fields(fields)
    return record


def _iter_lines(text):
    if text.endswith("\n"):
        text = text[:-1]
    if text == "":
        return
    for raw in text.split("\n"):
        yield raw


def _append_detail(bucket, omitted_holder, line_number, raw_line, reason):
    if len(bucket) >= _MAX_DETAILS:
        omitted_holder[0] += 1
        return
    if isinstance(raw_line, str):
        raw_repr = raw_line
    else:
        try:
            raw_repr = bytes(raw_line)
        except (TypeError, ValueError):
            raw_repr = repr(raw_line)
    bucket.append(
        {
            "line_number": line_number,
            "raw_line": raw_repr,
            "reason": reason,
        }
    )


def analyze_logs(lines):
    """分析日志行（可迭代对象或多行字符串），返回统计字典。"""
    total_lines = 0
    valid_records = 0
    invalid_records = 0
    success_count = 0
    failure_count = 0
    failure_by_type = OrderedDict()
    failure_by_event = OrderedDict()
    records_by_event = OrderedDict()
    invalid_dates = []
    format_errors = []
    invalid_dates_omitted = [0]
    format_errors_omitted = [0]

    if isinstance(lines, str):
        source = _iter_lines(lines)
    else:
        source = lines

    for index, raw in enumerate(source, start=1):
        total_lines += 1

        text, decode_error = _decode_line(raw)
        if decode_error is not None:
            invalid_records += 1
            _append_detail(
                format_errors,
                format_errors_omitted,
                index,
                raw,
                decode_error,
            )
            continue

        content = text.rstrip("\r\n")
        fields = content.split()
        if len(fields) != 5:
            invalid_records += 1
            reason = _REASON_EMPTY if content.strip() == "" else _REASON_FIELD_COUNT
            _append_detail(
                format_errors,
                format_errors_omitted,
                index,
                raw,
                reason,
            )
            continue

        record, error = _parse_fields(fields)
        if error is not None:
            invalid_records += 1
            if error == _REASON_DATE:
                _append_detail(
                    invalid_dates,
                    invalid_dates_omitted,
                    index,
                    raw,
                    error,
                )
            else:
                _append_detail(
                    format_errors,
                    format_errors_omitted,
                    index,
                    raw,
                    error,
                )
            continue

        valid_records += 1
        event_id = record["event_id"]
        records_by_event[event_id] = records_by_event.get(event_id, 0) + 1

        if record["kind"] == "success":
            success_count += 1
        else:
            failure_count += 1
            failure_type = record["failure_type"]
            failure_by_type[failure_type] = (
                failure_by_type.get(failure_type, 0) + 1
            )
            failure_by_event[event_id] = (
                failure_by_event.get(event_id, 0) + 1
            )

    return {
        "total_lines": total_lines,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "success_count": success_count,
        "failure_count": failure_count,
        "failure_by_type": dict(failure_by_type),
        "failure_by_event": dict(failure_by_event),
        "records_by_event": dict(records_by_event),
        "invalid_dates": invalid_dates,
        "format_errors": format_errors,
        "invalid_dates_omitted": invalid_dates_omitted[0],
        "format_errors_omitted": format_errors_omitted[0],
    }


def analyze_text(text):
    """兼容旧接口，委托 analyze_logs。"""
    return analyze_logs(text)
