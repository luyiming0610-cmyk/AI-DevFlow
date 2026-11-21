
import os
import subprocess
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from core.report_generator import (
    build_report,
    collect_results,
    read_text,
    review_description,
    test_description,
)


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"

st.set_page_config(
    page_title="AI DevFlow｜智能研发流水线",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ====================================
# 页面设计
# ====================================

st.markdown(
    """
    <style>
    .stApp {
        background: #F8FAFC;
    }

    .block-container {
        max-width: 1220px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    [data-testid="stSidebar"] {
        display: none;
    }

    .hero {
        background: linear-gradient(
            115deg,
            #101C33 0%,
            #173765 100%
        );
        border-radius: 18px;
        padding: 34px 40px;
        margin-bottom: 26px;
        color: #FFFFFF;
    }

    .hero h1 {
        font-size: 38px;
        line-height: 1.2;
        font-weight: 750;
        letter-spacing: -1px;
        margin: 0 0 8px 0;
        color: #FFFFFF;
    }

    .hero p {
        font-size: 19px;
        font-weight: 500;
        color: #C6D7F0;
        margin: 0;
    }

    .mode-badge {
        display: inline-block;
        margin-top: 18px;
        background: #263F65;
        border: 1px solid #476184;
        border-radius: 8px;
        padding: 7px 12px;
        color: #E8F1FF;
        font-size: 14px;
        font-weight: 600;
    }

    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px 20px;
    }

    [data-testid="stMetricLabel"] {
        font-size: 15px;
        font-weight: 600;
        color: #64748B;
    }

    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #152440;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 22px;
        border-bottom: 1px solid #E2E8F0;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 16px;
        font-weight: 600;
        padding: 14px 4px;
    }

    .step-card {
        display: flex;
        align-items: center;
        gap: 14px;
        min-height: 75px;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }

    .step-number {
        width: 34px;
        height: 34px;
        flex-shrink: 0;
        background: #EAF1FF;
        color: #2563EB;
        border-radius: 10px;
        font-size: 16px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .step-name {
        font-size: 17px;
        font-weight: 650;
        color: #182941;
    }

    .gate-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 17px 18px;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        background: #FFFFFF;
        margin-bottom: 12px;
    }

    .gate-title {
        font-weight: 600;
        color: #24344D;
        font-size: 15px;
    }

    .gate-pass {
        color: #15803D;
        font-weight: 700;
    }

    .gate-fail {
        color: #B91C1C;
        font-weight: 700;
    }

    .gate-pending {
        color: #64748B;
        font-weight: 700;
    }

    div.stButton > button[kind="primary"] {
        background: #2563EB;
        color: white;
        border-radius: 10px;
        padding: 0.65rem 1.25rem;
        font-weight: 650;
    }

    h2, h3 {
        color: #14233D;
        letter-spacing: -0.4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ====================================
# 读取真实运行记录
# ====================================

data = collect_results(ROOT)

before = data["before"]
after = data["after"]
checks = data["checks"]

trial = data["api_trial"]
validation = data["api_validation"]


def metric_value(summary: dict) -> str:
    if not summary["found"]:
        return "—"

    total = summary["passed"] + summary["failed"]
    return f"{summary['passed']}/{total}"


def gate_card(name: str, value) -> None:
    if value is True:
        status = "通过"
        css_class = "gate-pass"
    elif value is False:
        status = "未通过"
        css_class = "gate-fail"
    else:
        status = "待验证"
        css_class = "gate-pending"

    st.markdown(
        f"""
        <div class="gate-card">
            <span class="gate-title">{name}</span>
            <span class="{css_class}">{status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def run_mock() -> None:
    env = os.environ.copy()
    env["AI_MODE"] = "mock"

    try:
        process = subprocess.run(
            [
                sys.executable,
                str(ROOT / "main.py"),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
        )

        st.session_state["last_output"] = (
            process.stdout + "\n" + process.stderr
        )

        st.session_state["last_exit"] = (
            process.returncode
        )

    except subprocess.TimeoutExpired:
        st.session_state["last_output"] = (
            "流水线运行超时。"
        )
        st.session_state["last_exit"] = -1

    except OSError as exc:
        st.session_state["last_output"] = (
            f"运行失败：{exc}"
        )
        st.session_state["last_exit"] = -1


# ====================================
# 顶部标题
# ====================================

st.markdown(
    """
    <div class="hero">
        <h1>AI DevFlow</h1>
        <p>智能研发流水线</p>
        <span class="mode-badge">
            AI 研发控制台
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ====================================
# 核心指标
# ====================================

# ====================================
# 真实 AI 研发任务入口
# ====================================

st.subheader("开始研发")

if st.button(
    "＋ 新建研发任务 · DeepSeek AI 开发",
    type="primary",
    use_container_width=True,
    key="new_real_task",
):
    st.switch_page("pages/01_新建研发任务.py")

st.divider()

st.subheader("研发流程验收记录（MOCK）")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "首次测试",
        metric_value(before),
    )

with c2:
    st.metric(
        "回归测试",
        metric_value(after),
    )

with c3:
    st.metric(
        "质量门禁",
        (
            "全部通过"
            if data["quality_passed"]
            else "待验证"
        ),
    )

with c4:
    st.metric(
        "人工审核",
        review_description(
            data["review"].get("status", "")
        ),
    )

st.write("")

# ====================================
# 主功能导航
# ====================================

tab_overview, tab_pipeline, tab_tests, tab_api, tab_report = (
    st.tabs(
        [
            "项目总览",
            "研发流水线",
            "测试与质量",
            "真实 AI 修复",
            "中文报告",
        ]
    )
)

# ====================================
# 项目总览
# ====================================

with tab_overview:
    st.subheader("测试通过情况")

    if before["found"] and after["found"]:
        chart_data = pd.DataFrame(
            [
                {
                    "阶段": "首次测试",
                    "状态": "通过",
                    "数量": before["passed"],
                    "顺序": 1,
                },
                {
                    "阶段": "首次测试",
                    "状态": "失败",
                    "数量": before["failed"],
                    "顺序": 2,
                },
                {
                    "阶段": "修复后回归",
                    "状态": "通过",
                    "数量": after["passed"],
                    "顺序": 1,
                },
                {
                    "阶段": "修复后回归",
                    "状态": "失败",
                    "数量": after["failed"],
                    "顺序": 2,
                },
            ]
        )

        maximum = max(
            3,
            before["passed"] + before["failed"],
            after["passed"] + after["failed"],
        )

        chart = (
            alt.Chart(chart_data)
            .mark_bar(
                size=36,
                cornerRadiusEnd=5,
            )
            .encode(
                y=alt.Y(
                    "阶段:N",
                    sort=[
                        "首次测试",
                        "修复后回归",
                    ],
                    title=None,
                    axis=alt.Axis(
                        labelAngle=0,
                        labelFontSize=15,
                        labelPadding=12,
                        labelLimit=200,
                        ticks=False,
                        domain=False,
                    ),
                ),
                x=alt.X(
                    "数量:Q",
                    title=None,
                    scale=alt.Scale(
                        domain=[0, maximum],
                    ),
                    axis=alt.Axis(
                        tickCount=4,
                        labelFontSize=12,
                        gridColor="#E5EAF2",
                    ),
                ),
                color=alt.Color(
                    "状态:N",
                    scale=alt.Scale(
                        domain=["通过", "失败"],
                        range=[
                            "#2563EB",
                            "#F59E0B",
                        ],
                    ),
                    legend=alt.Legend(
                        title=None,
                        orient="bottom",
                        labelFontSize=14,
                    ),
                ),
                order=alt.Order(
                    "顺序:Q",
                    sort="ascending",
                ),
                tooltip=[
                    "阶段:N",
                    "状态:N",
                    "数量:Q",
                ],
            )
            .properties(height=210)
            .configure_view(
                strokeOpacity=0,
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )
    else:
        st.warning("暂无完整测试数据。")

    st.subheader("研发工作流")

    steps = [
        "需求分析",
        "代码生成",
        "自动测试",
        "失败修复",
        "质量门禁",
        "人工审核",
    ]

    for start in (0, 3):
        columns = st.columns(3)

        for index, column in enumerate(columns):
            step_index = start + index

            with column:
                st.markdown(
                    f"""
                    <div class="step-card">
                        <span class="step-number">
                            {step_index + 1}
                        </span>
                        <span class="step-name">
                            {steps[step_index]}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ====================================
# 研发流水线
# ====================================

with tab_pipeline:
    st.subheader("研发任务")

    requirement = read_text(
        ROOT / "workspace" / "requirements" / "task.md"
    )

    with st.expander("查看需求文档"):
        if requirement:
            st.markdown(requirement)
        else:
            st.error("需求文档不存在。")

    st.subheader("运行流水线")

    if st.button(
        "▶ 开始运行",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("正在执行研发流水线..."):
            run_mock()

        st.rerun()

    if "last_output" in st.session_state:
        if st.session_state.get("last_exit") == 0:
            st.success("流水线执行成功")
        else:
            st.error("流水线执行失败")

        with st.expander(
            "查看本次运行日志",
            expanded=True,
        ):
            st.code(
                st.session_state["last_output"],
                language="text",
            )

    with st.expander("查看生成的代码"):
        source = read_text(
            ROOT
            / "workspace"
            / "generated"
            / "analyzer.py"
        )

        st.code(
            source or "暂无代码",
            language="python",
        )


# ====================================
# 测试与质量门禁
# ====================================

with tab_tests:
    st.subheader("自动化测试")

    left, right = st.columns(2)

    with left:
        st.markdown("### 首次测试")
        st.metric(
            "测试结果",
            metric_value(before),
        )

        with st.expander("查看失败测试记录"):
            st.code(
                data["before_log"] or "暂无日志",
                language="text",
            )

    with right:
        st.markdown("### 修复后回归")
        st.metric(
            "测试结果",
            metric_value(after),
        )

        with st.expander("查看回归测试记录"):
            st.code(
                data["after_log"] or "暂无日志",
                language="text",
            )

    st.subheader("质量门禁")

    gate_names = [
        (
            "python_syntax",
            "Python 语法检查",
        ),
        (
            "basic_security_scan",
            "基础安全规则检查",
        ),
        (
            "ruff_lint",
            "Ruff 静态代码检查",
        ),
        (
            "pytest",
            "Pytest 回归测试",
        ),
    ]

    for key, name in gate_names:
        gate_card(
            name,
            checks.get(key),
        )


# ====================================
# 真实 DeepSeek 修复
# ====================================

with tab_api:
    st.subheader("DeepSeek 真实修复实验")

    if not trial:
        st.warning("尚无真实 API 实验记录。")

    else:
        st.write(
            "**模型：**",
            trial.get("model", "未知"),
        )

        usage = trial.get("usage") or {}

        a, b, c = st.columns(3)

        with a:
            st.metric(
                "输入 Token",
                usage.get("prompt_tokens", "—"),
            )

        with b:
            st.metric(
                "输出 Token",
                usage.get("completion_tokens", "—"),
            )

        with c:
            st.metric(
                "总 Token",
                usage.get("total_tokens", "—"),
            )

        st.subheader("修复验证结果")

        if data["api_verified"]:
            st.success(
                "真实模型修复候选通过 3 项功能测试"
            )
        elif (
            validation.get("validation_status")
            == "PASSED"
        ):
            st.warning(
                "测试记录显示通过，"
                "但代码哈希或证据尚未核对完整。"
            )
        else:
            st.warning(
                "尚无完整的功能验证通过记录。"
            )

        a, b, c = st.columns(3)

        with a:
            st.metric(
                "功能测试",
                test_description(data["api_tests"]),
            )

        with b:
            st.metric(
                "代码哈希",
                (
                    "一致"
                    if data["api_hash_matches"]
                    else "待核对"
                ),
            )

        with c:
            st.metric(
                "人工审核",
                review_description(
                    validation.get(
                        "human_review",
                        "PENDING",
                    )
                ),
            )

        with st.expander("查看真实模型生成的代码"):
            st.code(
                read_text(data["api_candidate"])
                or "暂无代码",
                language="python",
            )

        with st.expander("查看真实回归测试记录"):
            st.code(
                data["api_log"] or "暂无日志",
                language="text",
            )

        with st.expander("实验说明与安全边界"):
            st.write(
                "这一实验真实调用了 DeepSeek，"
                "根据 Pytest 失败日志生成修复候选，"
                "并使用原有测试集进行验证。"
            )
            st.write(
                "网页的一键运行仍为 MOCK 模式。"
                "真实候选未经生产级沙箱验证，"
                "也尚未完成最终人工审核。"
            )


# ====================================
# 中文交付报告
# ====================================

with tab_report:
    st.subheader("研发流水线运行报告")

    # 仅生成页面文本，不反复写入 Git 跟踪文件
    report = build_report(ROOT)

    st.markdown(report)

    st.download_button(
        "下载中文报告",
        data=report,
        file_name="AI_DevFlow_运行报告.md",
        mime="text/markdown",
        use_container_width=True,
    )
