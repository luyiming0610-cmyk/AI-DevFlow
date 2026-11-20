
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def read_json(path: Path) -> dict:
    try:
        data = json.loads(read_text(path))
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def file_sha256(path: Path) -> str:
    if not path.is_file():
        return ""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_summary(log: str) -> dict:
    """从真实 Pytest 输出中解析测试数量。"""

    passed = re.findall(
        r"\b(\d+)\s+passed\b",
        log,
    )

    failed = re.findall(
        r"\b(\d+)\s+failed\b",
        log,
    )

    found = bool(passed or failed)

    return {
        "found": found,
        "passed": int(passed[-1]) if passed else 0,
        "failed": int(failed[-1]) if failed else 0,
    }


def test_description(summary: dict) -> str:
    if not summary["found"]:
        return "暂无可解析的测试记录"

    return (
        f"{summary['passed']} 项通过，"
        f"{summary['failed']} 项失败"
    )


def check_description(value) -> str:
    if value is True:
        return "通过"

    if value is False:
        return "未通过"

    return "尚未验证"


def review_description(status: str) -> str:
    return {
        "PENDING": "待人工审核",
        "APPROVED": "已审核通过",
        "BLOCKED": "已阻断",
        "REJECTED": "审核未通过",
    }.get(status, "状态未知")


def collect_results(root: Path = ROOT) -> dict:
    """统一读取 MOCK 与真实 API 实验数据。"""

    reports = root / "reports"

    before_log = read_text(
        reports / "before_repair_pytest.txt"
    )

    after_log = read_text(
        reports / "after_repair_pytest.txt"
    )

    quality = read_json(
        reports / "quality_gate.json"
    )

    review = read_json(
        reports / "review_request.json"
    )

    api_trial = read_json(
        reports / "api_repair_evidence.json"
    )

    if not api_trial:
        api_trial = read_json(
            root / "runs" / "api_repair_trial" / "result.json"
        )

    api_validation = read_json(
        reports / "api_repair_validation.json"
    )

    api_log = read_text(
        reports / "api_repair_pytest.txt"
    )

    archived_candidate = (
        reports / "api_repair_candidate.py"
    )

    local_candidate = (
        root / "runs" / "api_repair_trial" / "analyzer.py"
    )

    candidate_path = (
        archived_candidate
        if archived_candidate.is_file()
        else local_candidate
    )

    expected_hash = api_trial.get(
        "candidate_sha256",
        "",
    )

    actual_hash = file_sha256(candidate_path)

    hash_matches = bool(
        expected_hash
        and actual_hash
        and expected_hash == actual_hash
    )

    api_tests = test_summary(api_log)

    # 必须由真实测试记录共同证明，而不是仅凭状态字符串
    api_verified = (
        api_validation.get("tests_executed") is True
        and api_validation.get("validation_status") == "PASSED"
        and api_validation.get("test_exit_code") == 0
        and api_validation.get("passed_count") == 3
        and api_tests["found"]
        and api_tests["passed"] == 3
        and api_tests["failed"] == 0
        and hash_matches
    )

    checks = quality.get("checks", {})

    if not isinstance(checks, dict):
        checks = {}

    required_checks = [
        "python_syntax",
        "basic_security_scan",
        "ruff_lint",
        "pytest",
    ]

    quality_passed = (
        quality.get("passed") is True
        and all(
            checks.get(key) is True
            for key in required_checks
        )
    )

    return {
        "before_log": before_log,
        "after_log": after_log,
        "before": test_summary(before_log),
        "after": test_summary(after_log),
        "quality": quality,
        "checks": checks,
        "quality_passed": quality_passed,
        "review": review,
        "api_trial": api_trial,
        "api_validation": api_validation,
        "api_log": api_log,
        "api_tests": api_tests,
        "api_verified": api_verified,
        "api_hash_matches": hash_matches,
        "api_candidate": candidate_path,
        "candidate_archived": archived_candidate.is_file(),
        "candidate_hash": actual_hash,
    }


def build_report(root: Path = ROOT) -> str:
    data = collect_results(root)

    before = data["before"]
    after = data["after"]

    checks = data["checks"]

    review_status = review_description(
        data["review"].get("status", "")
    )

    check_names = {
        "python_syntax": "Python 语法检查",
        "basic_security_scan": "基础安全规则检查",
        "ruff_lint": "Ruff 静态代码检查",
        "pytest": "Pytest 自动化测试",
    }

    quality_rows = "\n".join(
        f"| {label} | "
        f"{check_description(checks.get(key))} |"
        for key, label in check_names.items()
    )

    trial = data["api_trial"]
    validation = data["api_validation"]
    usage = trial.get("usage") or {}

    if not isinstance(usage, dict):
        usage = {}

    if data["api_verified"]:
        api_result = (
            "通过：真实模型修复候选已通过原有三项功能测试"
        )
    elif validation.get("validation_status") == "PASSED":
        api_result = (
            "测试记录显示通过，但候选文件或哈希证据"
            "尚不完整，需要核对"
        )
    elif validation:
        api_result = "验证未通过或记录不完整"
    elif trial:
        api_result = "已生成候选，尚无功能验证结果"
    else:
        api_result = "暂无真实模型实验记录"

    api_review = review_description(
        validation.get(
            "human_review",
            trial.get("human_review", ""),
        )
    )

    api_section = f"""## 六、真实 DeepSeek API 修复实验

本实验独立于 MOCK 主流水线，
真实调用 DeepSeek 分析 Pytest 失败日志并生成修复候选。

| 验证项目 | 实际记录 |
|---|---|
| 模型 | {trial.get("model", "暂无记录")} |
| 调用状态 | {trial.get("status", "暂无记录")} |
| 输入 Token | {usage.get("prompt_tokens", "暂无记录")} |
| 输出 Token | {usage.get("completion_tokens", "暂无记录")} |
| 总 Token | {usage.get("total_tokens", "暂无记录")} |
| 候选代码哈希一致 | {"是" if data["api_hash_matches"] else "未确认"} |
| 独立回归测试 | {test_description(data["api_tests"])} |
| 功能验证结论 | {api_result} |
| 人工审核 | {api_review} |
| 生产环境部署 | 未执行 |

原始证据：

- `reports/api_repair_evidence.json`
- `reports/api_repair_candidate.py`
- `reports/api_repair_validation.json`
- `reports/api_repair_pytest.txt`

该实验使用的真实 API Token 数量以实际记录为准。
人民币费用需要按照 DeepSeek 平台账单核实。

测试运行于独立临时目录，
不是生产级的安全沙箱。
即使测试通过，仍需人工代码审核。
"""

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    overall = (
        "通过"
        if data["quality_passed"]
        else "未通过或证据不完整"
    )

    return f"""# AI DevFlow｜智能研发流水线运行报告

生成时间：{timestamp}

## 一、项目背景

本项目对应 B11《组建 AI 研发团队》笔试。

题目设定为一家传统行业公司，
现有 20 名研发人员维护 6 个内部系统，
需求积压约 3 个月。

建设目标是在 12 个月内，
探索将内部工具交付周期由 6 周缩短至 2 周，
预算约 80 万元/年。

以上属于 Part A 的企业建设目标，
不是当前 MVP 已完成的实际收益。

## 二、MVP 业务场景

本次选择赛事影像上传日志分析工具。

功能包括：

- 统计有效上传记录
- 统计成功及失败数量
- 分类统计失败原因
- 识别格式异常与非法时间戳

当前主流水线采用 MOCK 模式，
用于离线复现 Agent 编排和质量门禁。

## 三、研发流程

1. Planner：读取需求，生成开发计划。
2. Developer：生成日志分析代码。
3. Tester：执行自动化测试。
4. Repair：识别失败并执行预设修复。
5. Tester：运行回归测试。
6. Quality Gate：执行质量检查。
7. Human Review：生成待审核请求。

## 四、测试及修复结果

| 项目 | 真实运行结果 |
|---|---|
| 首次测试 | {test_description(before)} |
| 修复后回归测试 | {test_description(after)} |
| 综合质量门禁 | {overall} |
| 人工审核状态 | {review_status} |

### 失败原因

初始代码未正确校验时间戳。

当测试输入非法日期 `2026-99-99` 时，
初始程序错误地将其计为有效日志，
因此预设的边界条件测试失败。

### MOCK 修复响应

Repair Agent 读取真实 Pytest 失败日志，
根据预设规则增加日期有效性检查。

随后重新运行原有测试，
没有修改或弱化测试断言。

MOCK 修复是确定性实现，
不应描述为真实模型自主修复。

## 五、质量门禁

| 检查项目 | 验证结果 |
|---|---|
{quality_rows}

质量检查结果来自实际运行记录。

语法检查、Ruff 和基础安全规则
不等同于生产级安全审计。

{api_section}
## 七、代码审核与权限边界

- 代码使用 Git 进行版本管理。
- 测试结果保存在报告目录。
- 使用 SHA256 记录代码完整性。
- 质量门禁失败时不应进入发布流程。
- 当前审核状态：{review_status}。
- Agent 不持有生产环境部署权限。
- 本次没有执行生产环境部署。

## 八、证据文件

- `reports/development_plan.md`
- `reports/before_repair_pytest.txt`
- `reports/after_repair_pytest.txt`
- `reports/quality_gate.json`
- `reports/review_request.json`
- `reports/api_repair_evidence.json`
- `reports/api_repair_validation.json`
- `reports/api_repair_pytest.txt`
- `workspace/generated/analyzer.py`
- `EVIDENCE.md`

## 九、局限与结论

本 MVP 已验证本地研发工作流中的
测试失败、修复响应、回归测试和质量门禁。

真实 DeepSeek 修复实验单独保存，
不与 MOCK 主流水线混淆。

当前尚未实现任意需求的自主软件研发、
生产级安全沙箱或自动部署。

最终代码交付仍必须经过人工审核。
"""


def write_chinese_report(root: Path = ROOT) -> str:
    report = build_report(root)

    output = (
        root / "reports" / "pipeline_report_zh.md"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        report,
        encoding="utf-8",
    )

    return report


if __name__ == "__main__":
    write_chinese_report()

    print("中文报告生成成功：")
    print(
        ROOT / "reports" / "pipeline_report_zh.md"
    )
