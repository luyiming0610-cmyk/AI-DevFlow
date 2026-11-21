
import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.real_task import (
    read_task_files,
    run_real_task,
)


st.set_page_config(
    page_title="新建研发任务｜AI DevFlow",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #F8FAFC;
    }

    .block-container {
        max-width: 920px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    [data-testid="stSidebar"] {
        display: none;
    }

    .task-header {
        background: linear-gradient(
            110deg, #101C33, #173765
        );
        border-radius: 16px;
        padding: 30px 34px;
        color: white;
        margin-bottom: 24px;
    }

    .task-header h1 {
        color: white;
        font-size: 32px;
        margin: 0 0 6px 0;
    }

    .task-header p {
        color: #C6D7F0;
        font-size: 17px;
        margin: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.page_link(
    "dashboard.py",
    label="返回项目总览",
    icon="🏠",
)

st.markdown(
    """
    <div class="task-header">
        <h1>新建研发任务</h1>
        <p>提交需求，由真实 DeepSeek Agent 生成方案与代码</p>
    </div>
    """,
    unsafe_allow_html=True,
)

DEFAULT_REQUIREMENT = (
    "开发一个赛事影像上传日志分析工具。"
    "日志每行包含日期、时间、级别、赛事编号和操作。"
    "需要统计有效记录、成功数量、失败数量，"
    "按照失败类型和赛事编号汇总，"
    "识别非法日期及异常格式，输出结构化字典。"
)

with st.form("development_task"):
    st.markdown("### 软件开发需求")

    requirement = st.text_area(
        "描述需要开发的功能",
        value=DEFAULT_REQUIREMENT,
        height=170,
        label_visibility="collapsed",
        max_chars=3000,
    )

    st.markdown("### 开发模式")
    st.write("DeepSeek · 真实模型")

    st.markdown("### 验收依据")
    st.write(
        "当前支持日志分析工具场景，"
        "代码接口及测试标准由项目现有测试集约束。"
    )

    consent = st.checkbox(
        "确认使用真实 API，本次调用将消耗 Token"
    )

    submitted = st.form_submit_button(
    "开始真实 AI 研发",
    type="primary",
    use_container_width=True,
    )

if submitted and not consent:
    st.error("请先确认本次真实 API 调用费用。")

if submitted and consent:
    with st.status(
        "正在执行真实 AI 研发任务",
        expanded=True,
    ) as status:
        st.write("读取需求并连接 DeepSeek")

        result = run_real_task(requirement)

        st.session_state["real_task_result"] = result

        if result["status"] == "FAILED":
            st.error(result.get("error", "执行失败"))
            status.update(
                label="任务执行失败",
                state="error",
            )
        else:
            st.write("需求分析与代码生成阶段已结束")
            st.write("已保存源代码和运行证据")

            if result["status"] == "STATIC_CHECKS_PASSED":
                status.update(
                    label="真实 AI 代码生成成功",
                    state="complete",
                )
            else:
                status.update(
                    label="候选生成完成，静态检查未通过",
                    state="error",
                )

result = st.session_state.get("real_task_result")

if result:
    st.divider()
    st.subheader("研发任务结果")

    st.write("任务编号：", result["task_id"])
    st.write("使用模型：", result.get("model", "未知"))

    usage = result.get("usage", {})

    planner_usage = usage.get("planner", {})
    developer_usage = usage.get("developer", {})

    total_tokens = (
        planner_usage.get("total_tokens", 0)
        + developer_usage.get("total_tokens", 0)
    )

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "实际 API Token",
            total_tokens,
        )

    with c2:
        st.metric(
            "功能测试",
            "待验证",
        )

    files = read_task_files(result["task_id"])

    tabs = st.tabs(
        [
            "开发计划",
            "生成代码",
            "质量检查",
            "任务报告",
        ]
    )

    with tabs[0]:
        if files["plan"]:
            st.markdown(files["plan"])

            st.download_button(
                "下载开发计划",
                data=files["plan"],
                file_name="开发计划.md",
                mime="text/markdown",
            )
        else:
            st.warning("尚无开发计划")

    with tabs[1]:
        if files["code"]:
            st.code(
                files["code"],
                language="python",
            )

            st.download_button(
                "下载 Python 源代码",
                data=files["code"],
                file_name="analyzer.py",
                mime="text/x-python",
            )
        else:
            st.warning("尚无生成代码")

    with tabs[2]:
        checks = result.get("checks", {})

        names = {
            "python_syntax": "Python 语法检查",
            "ruff_lint": "Ruff 代码检查",
            "basic_security_scan": "基础安全规则检查",
        }

        for key, label in names.items():
            if checks.get(key) is True:
                st.success(f"{label}：通过")
            else:
                st.error(f"{label}：未通过或未执行")

        for note in checks.get("notes", []):
            st.code(note, language="text")

        st.warning(
            "当前仅完成静态检查。"
            "真实模型生成的代码尚未运行功能测试。"
        )

    with tabs[3]:
        st.markdown(
            files["report"] or "暂无报告"
        )

        if files["report"]:
            st.download_button(
                "下载任务报告",
                data=files["report"],
                file_name="真实AI研发报告.md",
                mime="text/markdown",
            )
