
import json
import re
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "runs" / "interactive_tasks"


st.set_page_config(
    page_title="AI DevFlow｜AI 研发工作台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ========================================
# 页面样式
# ========================================

st.markdown(
    """
    <style>
    .stApp {
        background: #F8FAFC;
    }

    .block-container {
        max-width: 1120px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .hero {
        background: linear-gradient(
            115deg, #101C33, #193B6B
        );
        padding: 38px 42px;
        border-radius: 18px;
        margin-bottom: 26px;
    }

    .hero h1 {
        color: white;
        font-size: 40px;
        margin: 0 0 10px 0;
    }

    .hero p {
        color: #C7D9F3;
        font-size: 19px;
        margin: 0;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
    }

    div.stButton > button[kind="primary"] {
        background: #2563EB;
        color: white;
        border-radius: 10px;
        min-height: 52px;
        font-weight: 650;
    }

    h2, h3 {
        color: #14233D;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ========================================
# 文件读取工具
# ========================================

def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
        return data if isinstance(data, dict) else {}

    except (OSError, ValueError):
        return {}


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def read_test_log(path: Path) -> str:
    """
    兼容 UTF-8 和 PowerShell 生成的 UTF-16 日志。
    """
    if not path.is_file():
        return ""

    raw = path.read_bytes()

    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode(
            "utf-16",
            errors="replace",
        )

    if raw and raw.count(b"\x00") > len(raw) // 8:
        return raw.decode(
            "utf-16-le",
            errors="replace",
        )

    return raw.decode(
        "utf-8-sig",
        errors="replace",
    )


def parse_tests(log: str) -> tuple[int, int, bool]:
    passed_matches = re.findall(
        r"\b(\d+)\s+passed\b",
        log,
    )

    failed_matches = re.findall(
        r"\b(\d+)\s+failed\b",
        log,
    )

    passed = (
        int(passed_matches[-1])
        if passed_matches else 0
    )

    failed = (
        int(failed_matches[-1])
        if failed_matches else 0
    )

    found = bool(passed_matches or failed_matches)

    return passed, failed, found


def load_latest_task():
    if not TASKS_DIR.is_dir():
        return None

    folders = sorted(
        [
            folder
            for folder in TASKS_DIR.iterdir()
            if folder.is_dir()
        ],
        key=lambda folder: folder.name,
        reverse=True,
    )

    for folder in folders:
        record = read_json(
            folder / "result.json"
        )

        if record:
            return folder, record

    return None


def status_text(status: str) -> str:
    return {
        "STARTED": "任务已创建",
        "PLAN_GENERATED": "开发计划已生成",
        "STATIC_CHECKS_PASSED": "静态检查通过",
        "STATIC_CHECKS_FAILED": "静态检查未通过",
        "FAILED": "代码生成失败",
    }.get(status, status or "未知")


def check_label(value) -> str:
    if value is True:
        return "通过"

    if value is False:
        return "未通过"

    return "未验证"


# ========================================
# 页面顶部
# ========================================

st.markdown(
    """
    <div class="hero">
        <h1>AI DevFlow</h1>
        <p>从业务需求到代码交付的 AI 研发工作台</p>
    </div>
    """,
    unsafe_allow_html=True,
)


if st.button(
    "＋ 新建 AI 研发任务",
    type="primary",
    use_container_width=True,
):
    st.switch_page(
        "pages/01_新建研发任务.py"
    )


st.write("")
st.subheader("最近的研发任务")

latest = load_latest_task()


# ========================================
# 最近任务
# ========================================

if latest is None:
    st.info("暂无研发任务，请先创建一个任务。")

else:
    task_dir, record = latest

    task_id = record.get(
        "task_id",
        task_dir.name,
    )

    st.write("任务编号：", task_id)

    st.write(
        "代码生成状态：",
        status_text(record.get("status", "")),
    )

    requirement = record.get(
        "requirement",
        "",
    )

    if requirement:
        with st.expander("查看业务需求"):
            st.write(requirement)

    # ------------------------------------
    # 真实 API 使用量
    # ------------------------------------

    usage = record.get("usage", {})

    if not isinstance(usage, dict):
        usage = {}

    total_tokens = sum(
        item.get("total_tokens", 0)
        for item in usage.values()
        if isinstance(item, dict)
    )

    # ------------------------------------
    # 静态检查
    # ------------------------------------

    checks = record.get("checks", {})

    if not isinstance(checks, dict):
        checks = {}

    required_checks = [
        "python_syntax",
        "ruff_lint",
        "basic_security_scan",
    ]

    static_passed = all(
        checks.get(key) is True
        for key in required_checks
    )

    # ------------------------------------
    # 功能测试
    # ------------------------------------

    pytest_file = task_dir / "pytest.txt"

    log = read_test_log(pytest_file)

    passed, failed, found = parse_tests(log)

    if not found:
        test_status = "未执行或记录不完整"

    elif failed > 0:
        test_status = f"{failed} 项失败"

    elif passed > 0:
        test_status = f"{passed} 项通过"

    else:
        test_status = "结果待核对"

    # ------------------------------------
    # AI 修复状态
    # ------------------------------------

    repair_result = read_json(
        task_dir / "repair_result.json"
    )

    repair_status = repair_result.get(
        "status",
        "",
    )

    repair_status_labels = {
        "STARTED": "正在处理",
        "REPAIR_FAILED": "修复请求失败",
        "REPAIR_CANDIDATE_READY": "修复候选已生成",
        "STATIC_CHECKS_FAILED": "修复候选静态检查未通过",
    }

    repair_display = repair_status_labels.get(
        repair_status,
        "尚未执行",
    )

    # ------------------------------------
    # 主要指标
    # ------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "真实 API Token",
            total_tokens,
        )

    with c2:
        st.metric(
            "代码静态检查",
            "通过" if static_passed else "未通过",
        )

    with c3:
        st.metric(
            "功能验收",
            test_status,
        )

    with c4:
        st.metric(
            "AI 修复状态",
            repair_display,
        )

    st.divider()

    # ------------------------------------
    # 测试与失败响应
    # ------------------------------------

    st.subheader("研发验收结果")

    if found and failed > 0:
        st.error(
            f"功能验收失败："
            f"{passed} 项通过，{failed} 项失败。"
        )

    elif found and passed > 0:
        st.success(
            f"当前测试记录：{passed} 项通过。"
        )

    else:
        st.warning(
            "当前任务尚无可确认的功能测试结果。"
        )

    if repair_status == "REPAIR_FAILED":
        st.error(
            "AI 修复未完成："
            + repair_result.get(
                "error",
                "未知错误",
            )
        )

    elif repair_status == "REPAIR_CANDIDATE_READY":
        st.success(
            "AI 已生成修复候选代码。"
            "尚需人工检查和回归测试。"
        )

    with st.expander("查看真实 Pytest 测试日志"):
        st.code(
            log or "尚无测试日志",
            language="text",
        )

    # ------------------------------------
    # 文件位置
    # ------------------------------------

    plan_path = task_dir / "plan.md"
    code_path = task_dir / "candidate.py"
    repaired_path = task_dir / "candidate_repaired.py"
    report_path = task_dir / "report.md"

    tabs = st.tabs(
        [
            "开发计划",
            "生成代码",
            "质量检查",
            "任务报告",
        ]
    )

    # ------------------------------------
    # 开发计划
    # ------------------------------------

    with tabs[0]:
        if plan_path.is_file():
            plan = read_text(plan_path)

            st.download_button(
                "下载开发计划",
                data=plan,
                file_name="development_plan.md",
                mime="text/markdown",
            )

            with st.expander(
                "查看完整开发计划",
                expanded=False,
            ):
                st.markdown(plan)

        else:
            st.info("暂无开发计划。")

    # ------------------------------------
    # 源代码
    # ------------------------------------

    with tabs[1]:
        if code_path.is_file():
            code = read_text(code_path)

            st.markdown("**DeepSeek 原始生成代码**")
            st.code(
                code,
                language="python",
            )

            st.download_button(
                "下载原始代码",
                data=code,
                file_name="candidate.py",
                mime="text/x-python",
            )

        if repaired_path.is_file():
            repaired_code = read_text(repaired_path)

            st.markdown("**DeepSeek 修复候选代码**")
            st.code(
                repaired_code,
                language="python",
            )

            st.download_button(
                "下载修复候选代码",
                data=repaired_code,
                file_name="candidate_repaired.py",
                mime="text/x-python",
            )

        if (
            not code_path.is_file()
            and not repaired_path.is_file()
        ):
            st.info("暂无代码。")

    # ------------------------------------
    # 质量检查
    # ------------------------------------

    with tabs[2]:
        check_names = {
            "python_syntax": "Python 语法检查",
            "ruff_lint": "Ruff 代码检查",
            "basic_security_scan": "基础安全规则检查",
        }

        for key, label in check_names.items():
            result = checks.get(key)

            if result is True:
                st.success(
                    f"{label}：通过"
                )

            elif result is False:
                st.error(
                    f"{label}：未通过"
                )

            else:
                st.warning(
                    f"{label}：未验证"
                )

        if repair_result:
            st.markdown("**最近一次 AI 修复记录**")

            st.write(
                "状态：",
                repair_display,
            )

            repair_usage = repair_result.get(
                "usage",
                {},
            )

            if repair_usage:
                st.json(repair_usage)

            repair_checks = repair_result.get(
                "checks",
                {},
            )

            if repair_checks:
                st.json(repair_checks)

    # ------------------------------------
    # 任务报告
    # ------------------------------------

    with tabs[3]:
        st.markdown("**代码生成阶段报告**")

        if report_path.is_file():
            st.download_button(
                "下载任务报告",
                data=read_text(report_path),
                file_name="task_report.md",
                mime="text/markdown",
            )

            with st.expander(
                "查看完整任务报告",
                expanded=False,
            ):
                st.markdown(
                    read_text(report_path)
                )
        else:
            st.info("暂无任务报告。")

        if found:
            st.write(
                "功能验收：",
                test_status,
            )

        if repair_result:
            st.write(
                "最近一次修复：",
                repair_display,
            )

        st.write("人工审核：待完成")
        st.write("生产环境部署：未执行")
