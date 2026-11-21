# 赛事影像上传日志分析工具｜唯一验收规范

版本：2.0

## 一、业务目标

开发一个离线赛事影像上传日志分析工具。

输入文本日志，识别有效上传记录、成功记录、失败记录及异常记录，并生成确定性的结构化 Python 字典。

本文件是 Planner、Developer、Tester 和 Repair Agent 的唯一业务验收依据。

## 二、功能接口

必须提供以下接口：

### 1. parse_line(line: str) -> dict | None

解析单行日志。

合法时返回标准化记录：

- date
- time
- level
- event_id
- action
- kind
- failure_type

非法时返回 None。

### 2. analyze_logs(lines: Iterable[str]) -> dict

接收可迭代日志行，支持生成器和流式输入。

为了兼容文本输入，也允许直接传入多行字符串。

### 3. analyze_text(text: str) -> dict

兼容旧接口，内部调用 analyze_logs，不允许出现两套独立统计逻辑。

## 三、输入格式

每行固定五个字段：

日期 时间 级别 赛事编号 操作

示例：

2026-11-20 09:01:12 INFO event_001 upload_success
2026-11-20 09:02:15 ERROR event_001 upload_timeout
2026-11-20 09:03:21 ERROR event_002 connection_failed
2026-11-20 09:04:10 INFO event_002 upload_success

### 字段规则

1. 日期严格使用 YYYY-MM-DD。
2. 日期必须是真实有效的日历日期。
3. 时间严格使用 HH:MM:SS。
4. 小时范围为 00-23。
5. 分钟和秒范围为 00-59。
6. 级别仅接受 INFO 和 ERROR。
7. 赛事编号只允许英文字母、数字、下划线和连字符。
8. 必须严格包含五个字段。

## 四、操作类型规则

成功：

INFO + upload_success

失败：

ERROR + upload_failed:失败原因

同时兼容现有样例中的：

- ERROR + upload_timeout
- ERROR + connection_failed

失败类型必须能够从操作字段准确提取。

未知操作不得擅自归类。

级别与操作不匹配时，视为格式异常。

## 五、输出结构

analyze_logs 必须返回以下字典：

{
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
    "format_errors_omitted": 0
}

### 字段含义

- total_lines：输入总行数。
- valid_records：有效记录数量。
- invalid_records：非法记录数量。
- success_count：成功记录数量。
- failure_count：失败记录数量。
- failure_by_type：按失败原因统计。
- failure_by_event：按赛事编号统计失败数量。
- records_by_event：按赛事编号统计全部有效记录。
- invalid_dates：非法日期明细。
- format_errors：其他格式异常明细。
- invalid_dates_omitted：因明细上限未保存的非法日期数量。
- format_errors_omitted：因明细上限未保存的格式异常数量。

异常明细必须包含：

- line_number：原始行号，从 1 开始。
- raw_line：原始日志内容。
- reason：异常原因。

每类异常明细最多保存 1000 条，超出部分计入 omitted 字段。

## 六、边界条件

必须处理：

1. 空输入。
2. 空行和纯空白行。
3. 字段不足或超过五个。
4. 非法日期格式。
5. 不存在的日历日期。
6. 非法时间格式。
7. 超出时间范围。
8. 非法赛事编号。
9. 未知操作类型。
10. 级别和操作不匹配。
11. 无法 UTF-8 解码的输入行。
12. 多赛事混合统计。
13. 大量异常日志。
14. 生成器输入。

空行默认计入总行数，并记录为格式异常。

不可解码的行不得导致整个任务崩溃。

## 七、统计约束

必须满足：

1. total_lines = valid_records + invalid_records
2. valid_records = success_count + failure_count
3. sum(failure_by_type.values()) = failure_count
4. sum(failure_by_event.values()) = failure_count
5. sum(records_by_event.values()) = valid_records

同一输入重复运行，结果必须完全一致。

## 八、技术限制

- Python 3.12。
- 仅使用 Python 标准库。
- 不允许网络请求。
- 不允许文件读写。
- 不允许启动子进程。
- 不允许 eval 或 exec。
- 核心函数必须是纯计算逻辑。
- 不允许修改测试断言来掩盖错误。

## 九、验收要求

必须通过自动化测试：

- 正常成功记录。
- 正常失败记录。
- 失败类型统计。
- 赛事维度统计。
- 非法日期。
- 非法时间。
- 格式异常。
- 未知操作。
- 空输入。
- 编码异常。
- 生成器输入。
- 多次运行确定性。

所有测试必须针对当前版本候选代码执行。

## 十、交付要求

保留：

- 完整源代码。
- 开发计划。
- 测试结果。
- 每轮修复前后代码。
- SHA256 文件哈希。
- API Token 消耗。
- 测试失败日志。
- 最终质量检查报告。
- 人工审核请求。

未经人工审核，不得自动发布或部署。
