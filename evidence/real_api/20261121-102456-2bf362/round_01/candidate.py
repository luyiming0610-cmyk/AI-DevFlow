"""赛事影像上传日志分析工具。

公开接口：
    parse_line(line) -> dict | None
    analyze_logs(lines) -> dict
    analyze_text(text) -> dict

仅使用 Python 3.12 标准库，纯计算逻辑，无文件读写、无网络、无子进程。
"""

import re
from datetime import date as _date
from typing import Any, Iterable

__all__ = ["parse_line", "analyze_logs", "analyze_text"]

_DETAIL_LIMIT = 1000

_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
_TIME_RE = re.compile(r"^[0-9]{2}:[0-9]{2}:[0-9]{2}$")
_EVENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_LEVELS = ("INFO", "ERROR")

# 已知的失败操作（无冒号形式）
_LEGACY_FAILURE_ACTIONS = ("upload_timeout", "connection_failed")

# 带原因的失败操作前缀
_FAILED_REASON_PREFIX = "upload_failed:"


def _validate_date(value: str) -> bool:
    if not _DATE_RE.match(value):
        return False
    try:
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
    except (TypeError, ValueError):
        return False
    try:
        _date(year, month, day)
    except ValueError:
        return False
    return True


def _validate_time(value: str) -> bool:
    if not _TIME_RE.match(value):
        return False
    try:
        hour = int(value[0:2])
        minute = int(value[3:5])
        second = int(value[6:8])
    except (TypeError, ValueError):
        return False
    if hour < 0 or hour > 23:
        return False
    if minute < 0 or minute > 59:
        return False
    if second < 0 or second > 59:
        return False
    return True


def _extract_failure_type(action: str) -> str | None:
    """从操作字段提取失败类型，未知返回 None。"""
    if action in _LEGACY_FAILURE_ACTIONS:
        return action
    if action.startswith(_FAILED_REASON_PREFIX):
        reason = action[len(_FAILED_REASON_PREFIX):].strip()
        if reason:
            return reason.lower()
        return None
    return None


def _coerce_line(line: Any) -> tuple[str | None, str]:
    """将输入行转换为文本。返回 (text, raw_repr)。

    text 为 None 表示无法解码。
    """
    if isinstance(line, str):
        return line, line
    if isinstance(line, (bytes, bytearray)):
        try:
            decoded = bytes(line).decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_repr = bytes(line).decode("utf-8", errors="backslashreplace")
            except Exception:
                raw_repr = repr(line)
            return None, raw_repr
        return decoded, decoded
    # 其它类型尝试 str 转换（容错），但视为格式异常内容
    try:
        text = str(line)
    except Exception:
        text = repr(line)
    return text, text


def _split_fields(text: str) -> list[str]:
    """按空白拆分，忽略前导/尾随空白但要能识别空行。"""
    stripped = text.strip()
    if stripped == "":
        return []
    return re.split(r"\s+", stripped)


def _classify(line: Any) -> tuple[dict[str, Any] | None, str | None, str]:
    """解析原始行。

    返回 (record, error_kind, reason)。

    error_kind 为 None / "date" / "format"。
    record 非 None 时表示有效记录。
    """
    text, _raw_repr = _coerce_line(line)
    if text is None:
        return None, "format", "undecodable line"

    fields = _split_fields(text)

    if not fields:
        return None, "format", "empty line"

    if len(fields) != 5:
        return None, "format", f"expected 5 fields, got {len(fields)}"

    date_str, time_str, level, event_id, action = fields

    if not _validate_date(date_str):
        return None, "date", f"invalid date: {date_str!r}"

    if not _validate_time(time_str):
        return None, "format", f"invalid time: {time_str!r}"

    if level not in _LEVELS:
        return None, "format", f"invalid level: {level!r}"

    if not _EVENT_RE.match(event_id):
        return None, "format", f"invalid event id: {event_id!r}"

    # 操作与级别匹配
    if action == "upload_success":
        if level != "INFO":
            return None, "format", (
                f"level/action mismatch: {level} + {action}"
            )
        record = {
            "date": date_str,
            "time": time_str,
            "level": level,
            "event_id": event_id,
            "action": action,
            "kind": "success",
            "failure_type": None,
        }
        return record, None, ""

    failure_type = _extract_failure_type(action)
    if failure_type is None:
        return None, "format", f"unknown action: {action!r}"

    if level != "ERROR":
        return None, "format", (
            f"level/action mismatch: {level} + {action}"
        )

    record = {
        "date": date_str,
        "time": time_str,
        "level": level,
        "event_id": event_id,
        "action": action,
        "kind": "failure",
        "failure_type": failure_type,
    }
    return record, None, ""


def parse_line(line: str) -> dict[str, Any] | None:
    """解析单行日志，合法返回标准化记录，否则返回 None。"""
    record, _, _ = _classify(line)
    return record


def _iter_lines(lines: Any) -> Iterable[Any]:
    """将输入规范化为可迭代行序列。"""
    if isinstance(lines, (str, bytes, bytearray)):
        if isinstance(lines, (bytes, bytearray)):
            try:
                text = bytes(lines).decode("utf-8")
            except UnicodeDecodeError:
                # 整体不可解码：拆出原始字节做单行处理
                yield lines
                return
        else:
            text = lines
        # 保留末尾空行的问题：以 \n 切分，如果结尾为 \n 则去掉最后一个空
        parts = text.split("\n")
        if parts and parts[-1] == "":
            parts = parts[:-1]
        for part in parts:
            yield part
        return

    # 可迭代对象
    try:
        iterator = iter(lines)
    except TypeError:
        # 不能迭代：当作单行处理
        yield lines
        return
    for item in iterator:
        yield item


def _empty_result() -> dict[str, Any]:
    return {
        "total_lines": 0,
        "valid_records": 0,
        "invalid_records": 0,
        "success_count": 0,
        "failure_count": 0,
        "failure_by_type": {},
        "failure_by_event": {},
        "records_by_event": {},
        "invalid_dates": [],
        "format_errors": [],
        "invalid_dates_omitted": 0,
        "format_errors_omitted": 0,
    }


def analyze_logs(lines: Any) -> dict[str, Any]:
    """分析日志行，返回确定性统计字典。

    支持可迭代对象（含生成器）以及多行字符串。
    """
    result = _empty_result()

    failure_by_type: dict[str, int] = {}
    failure_by_event: dict[str, int] = {}
    records_by_event: dict[str, int] = {}
    invalid_dates: list[dict[str, Any]] = []
    format_errors: list[dict[str, Any]] = []

    total = 0
    valid = 0
    invalid = 0
    success = 0
    failure = 0
    date_omitted = 0
    format_omitted = 0

    for index, raw in enumerate(_iter_lines(lines), start=1):
        total += 1

        _text, raw_repr = _coerce_line(raw)

        record, error_kind, reason = _classify(raw)

        if record is not None:
            valid += 1
            event_id = record["event_id"]
            records_by_event[event_id] = records_by_event.get(event_id, 0) + 1
            if record["kind"] == "success":
                success += 1
            else:
                failure += 1
                ftype = record["failure_type"]
                failure_by_type[ftype] = failure_by_type.get(ftype, 0) + 1
                failure_by_event[event_id] = (
                    failure_by_event.get(event_id, 0) + 1
                )
            continue

        invalid += 1
        detail = {
            "line_number": index,
            "raw_line": raw_repr,
            "reason": reason,
        }

        if error_kind == "date":
            if len(invalid_dates) < _DETAIL_LIMIT:
                invalid_dates.append(detail)
            else:
                date_omitted += 1
        else:
            if len(format_errors) < _DETAIL_LIMIT:
                format_errors.append(detail)
            else:
                format_omitted += 1

    result["total_lines"] = total
    result["valid_records"] = valid
    result["invalid_records"] = invalid
    result["success_count"] = success
    result["failure_count"] = failure
    result["failure_by_type"] = failure_by_type
    result["failure_by_event"] = failure_by_event
    result["records_by_event"] = records_by_event
    result["invalid_dates"] = invalid_dates
    result["format_errors"] = format_errors
    result["invalid_dates_omitted"] = date_omitted
    result["format_errors_omitted"] = format_omitted

    return result


def analyze_text(text: str) -> dict[str, Any]:
    """兼容旧接口，内部仅委托 analyze_logs。"""
    return analyze_logs(text)


if __name__ == "__main__":
    sample = (
        "2026-11-20 09:01:12 INFO event_001 upload_success\n"
        "2026-11-20 09:02:15 ERROR event_001 upload_timeout\n"
        "2026-11-20 09:03:21 ERROR event_002 connection_failed\n"
        "2026-11-20 09:04:10 INFO event_002 upload_success\n"
    )
    import json as _json

    print(_json.dumps(analyze_text(sample), ensure_ascii=False, indent=2))
