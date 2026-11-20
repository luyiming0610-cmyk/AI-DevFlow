
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from core.report_generator import (
    collect_results,
    read_text,
    review_description,
    test_description,
    write_chinese_report,
)


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


st.set_page_config(
    page_title="AI DevFlow｜智能研发控制台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================
# 读取实际运行数据
# ============================

data = collect_results(ROOT)

before = data["before"]
after = data["after"]

checks = data["checks"]

trial = data["api_trial"]
validation = data["api_validation"]


def test_metric(summary: dict) -> str:
    if not summary["found"]:
        return "暂无记录"

    total = summary["passed"] + summary["failed"]

    return f"{summary['passed']}/{total}"


def quality_text() -> str:
    return (
        "全部通过"
        if data["quality_passed"]
        else "未通过或待验证"
    )


def run_mock_pipeline() -> None:
    """仅运行本地 MOCK，不调用收费 API。"""

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

        st.session_state["mock_output"] = (
            process.stdout + "\n" + process.stderr
        )

        st.session_state["mock_exit_code"] = (
            process.returncode
        )

    except subprocess.TimeoutExpired:
        st.session_state["mock_output"] = (
            "本次执行超时，请检查本地程序。"
        )
        st.session_state["mock_exit_code"] = -1

    except OSError as exc:
        st.session_state["mock_output"] = (
            f"启动失败：{exc}"
        )
        st.session_state["mock_exit_code"] = -1


# ============================
# 页面标题
# ============================

st.title("🤖 AI DevFlow")
st.subheader("AI 智能研发流水线控制台")

st.caption(
    "B11《组建 AI 研发团队》｜"
    "Agent 编排、失败响应、自动化测试与质量门禁"
)

st.info(
    "本地一键运行使用 MOCK 模式，不消耗 API 费用。"
    "真实 DeepSeek 修复实验及其功能验证单独展示，"
    "不会与 MOCK 结果混淆。"
)


# ============================
# 左侧导航说明
# ============================

with st.sidebar:
    st.title("项目导航")

    st.markdown(
        "**项目名称：** AI DevFlow"
    )

    st.markdown(
        "**笔试题目：** B11 · 组建 AI 研发团队"
    )

    st.divider()

    st.markdown("### 当前实现")

    st.write("✅ 本地研发流水线")
    st.write("✅ 自动测试与失败响应")
    st.write("✅ 四项质量门禁")
    st.write("✅ 真实 DeepSeek 修复实验")
    st.write("✅ 中文运行报告")
    st.write("⏳ 人工最终审核")

    st.divider()

    st.caption(
        "演示环境：本地 Python + Streamlit"
    )

    st.caption(
        "当前不会自动部署生产环境。"
    )


# ============================
# 项目指标
# ============================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "首次测试通过数",
        test_metric(before),
    )

with c2:
    st.metric(
        "回归测试通过数",
        test_metric(after),
    )

with c3:
    st.metric(
        "质量门禁",
        quality_text(),
    )

with c4:
    st.metric(
        "人工审核",
        review_description(
            data["review"].get("status", "")
        ),
    )

st.divider()


# ============================
# 五大功能页面
# ============================

(
    overview_tab,
    pipeline_tab,
    tests_tab,
    api_tab,
    report_tab,
) = st.tabs(
    [
        "项目总览",
        "研发流水线",
        "测试与质量门禁",
        "真实 DeepSeek 实验",
        "中文交付报告",
    ]
)


# ============================
# 1. 项目总览
# ============================

with overview_tab:
    st.header("项目总览")

    st.write(
        "本项目选择赛事影像上传日志分析工具"
        "作为内部研发场景，通过多阶段 Agent 编排，"
        "验证从需求到代码审核的最小闭环。"
    )

    st.subheader("测试通过情况")

    if before["found"] and after["found"]:
        chart_data = pd.DataFrame(
            [
                {
                    "测试阶段": "首次测试",
                    "通过": before["passed"],
                    "失败": before["failed"],
                },
                {
                    "测试阶段": "修复后回归",
                    "通过": after["passed"],
                    "失败": after["failed"],
                },
            ]
        )

        st.bar_chart(
            chart_data.set_index("测试阶段"),
        )

        st.caption(
            "图表直接读取保存的 Pytest 运行日志，"
            "展示故意失败测试与修复后的变化。"
        )
    else:
        st.warning(
            "缺少测试记录，请先运行本地流水线。"
        )

    st.subheader("研发工作流")

    stages = [
        (
            "① 需求分析",
            "读取需求并生成开发计划",
        ),
        (
            "② 代码生成",
            "生成日志分析程序",
        ),
        (
            "③ 自动测试",
            "执行验收用例，发现缺陷",
        ),
        (
            "④ 失败修复",
            "根据错误日志修复缺陷",
        ),
        (
            "⑤ 质量门禁",
            "语法、安全规则、Ruff、Pytest",
        ),
        (
            "⑥ 人工审核",
            "检查代码后决定是否合并",
        ),
    ]

    for start in (0, 3):
        columns = st.columns(3)

        for column, (title, desc) in zip(
            columns,
            stages[start:start + 3],
        ):
            with column:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.caption(desc)

    st.warning(
        "注意：MOCK 模式中的开发代码与修复补丁"
        "是预设的；真实 DeepSeek 修复使用独立实验。"
    )


# ============================
# 2. 研发流水线
# ============================

with pipeline_tab:
    st.header("研发任务与流水线执行")

    st.subheader("业务需求")

    requirement = read_text(
        ROOT / "workspace" / "requirements" / "task.md"
    )

    if requirement:
        with st.expander(
            "查看完整需求说明",
            expanded=True,
        ):
            st.markdown(requirement)
    else:
        st.warning(
            "找不到需求文件 workspace/requirements/task.md"
        )

    st.subheader("一键运行")

    st.write(
        "点击下方按钮，将按顺序执行需求分析、"
        "代码生成、首次测试、失败修复、回归测试、"
        "质量检查和人工审核请求生成。"
    )

    if st.button(
        "▶ 运行 MOCK 研发流水线",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner(
            "正在执行本地研发流水线..."
        ):
            run_mock_pipeline()

        st.rerun()

    if "mock_output" in st.session_state:
        if (
            st.session_state.get("mock_exit_code")
            == 0
        ):
            st.success(
                "本次本地流水线执行成功。"
            )
        else:
            st.error(
                "本次执行失败，请检查运行日志。"
            )

        with st.expander(
            "查看本次实际执行日志",
            expanded=True,
        ):
            st.code(
                st.session_state["mock_output"],
                language="text",
            )

    st.caption(
        "此按钮不会调用 DeepSeek API，"
        "也不会执行真实模型生成的候选代码。"
    )


# ============================
# 3. 测试与质量门禁
# ============================

with tests_tab:
    st.header("自动化测试与质量门禁")

    left, right = st.columns(2)

    with left:
        st.subheader("首次测试")

        st.write(test_description(before))

        if (
            before["found"]
            and before["failed"] > 0
        ):
            st.error(
                "预设缺陷成功触发失败测试。"
            )

        with st.expander(
            "查看首次测试原始日志"
        ):
            st.code(
                data["before_log"] or "暂无日志",
                language="text",
            )

    with right:
        st.subheader("修复后回归测试")

        st.write(test_description(after))

        if (
            after["found"]
            and after["failed"] == 0
            and after["passed"] > 0
        ):
            st.success(
                "保存的回归测试记录全部通过。"
            )

        with st.expander(
            "查看回归测试原始日志"
        ):
            st.code(
                data["after_log"] or "暂无日志",
                language="text",
            )

    st.divider()

    st.subheader("质量门禁检查")

    gate_names = {
        "python_syntax": "Python 语法检查",
        "basic_security_scan": "基础代码安全规则检查",
        "ruff_lint": "Ruff 静态代码检查",
        "pytest": "Pytest 自动化回归测试",
    }

    for key, label in gate_names.items():
        value = checks.get(key)

        if value is True:
            st.success(f"{label}：通过")
        elif value is False:
            st.error(f"{label}：未通过")
        else:
            st.warning(f"{label}：尚无记录")

    st.caption(
        "这些结果来自 reports/quality_gate.json。"
        "基础安全扫描不等于完整安全审计。"
    )

    st.divider()

    st.subheader("本地生成的代码")

    code = read_text(
        ROOT / "workspace" / "generated" / "analyzer.py"
    )

    with st.expander(
        "查看 MOCK 生成及修复后的代码"
    ):
        st.code(
            code or "尚未生成源代码",
            language="python",
        )


# ============================
# 4. 真实 DeepSeek API 实验
# ============================

with api_tab:
    st.header("真实 DeepSeek 修复实验")

    st.write(
        "该实验真实调用大模型，输入原始 Python 代码"
        "与 Pytest 失败日志，由模型生成修复候选，"
        "随后使用原有测试用例进行独立验证。"
    )

    if not trial:
        st.warning(
            "尚未找到真实 API 调用记录。"
        )

    else:
        st.write(
            "**模型名称：**",
            trial.get("model", "未知"),
        )

        st.write(
            "**调用状态：**",
            trial.get("status", "未知"),
        )

        usage = trial.get("usage") or {}

        a, b, c = st.columns(3)

        with a:
            st.metric(
                "输入 Token",
                usage.get("prompt_tokens", 0),
            )

        with b:
            st.metric(
                "输出 Token",
                usage.get("completion_tokens", 0),
            )

        with c:
            st.metric(
                "总 Token",
                usage.get("total_tokens", 0),
            )

        st.divider()

        st.subheader("真实模型修复验证结果")

        if data["api_verified"]:
            st.success(
                "真实 DeepSeek 修复候选已经通过"
                "原有三项功能回归测试。"
            )

        elif (
            validation.get("validation_status")
            == "PASSED"
        ):
            st.warning(
                "验证记录显示通过，"
                "但候选文件哈希或原始日志证据不完整。"
            )

        else:
            st.warning(
                "真实候选尚未取得完整的通过记录。"
            )

        x, y, z = st.columns(3)

        with x:
            st.metric(
                "功能测试",
                test_description(
                    data["api_tests"]
                ),
            )

        with y:
            st.metric(
                "代码哈希",
                (
                    "一致"
                    if data["api_hash_matches"]
                    else "待核对"
                ),
            )

        with z:
            st.metric(
                "人工审核",
                review_description(
                    validation.get(
                        "human_review",
                        "PENDING",
                    )
                ),
            )

        if not data["candidate_archived"]:
            st.info(
                "当前候选代码仍位于本地 runs 目录。"
                "提交 GitHub 前需要将它归档到 reports。"
            )

        with st.expander(
            "查看 DeepSeek 生成的修复代码"
        ):
            st.code(
                read_text(data["api_candidate"])
                or "没有找到候选代码",
                language="python",
            )

        with st.expander(
            "查看真实 API 回归测试日志"
        ):
            st.code(
                data["api_log"]
                or "暂无真实候选测试日志",
                language="text",
            )

        st.caption(
            "本页面只展示已经执行的真实模型实验记录。"
            "不会再次发起收费 API 请求。"
        )

    st.info(
        "真实模型生成代码并通过三项测试，"
        "不代表完成生产级安全审核。"
        "当前未执行生产环境部署。"
    )


# ============================
# 5. 中文交付报告
# ============================

with report_tab:
    st.header("中文研发流水线交付报告")

    report = write_chinese_report(ROOT)

    st.markdown(report)

    st.download_button(
        "下载中文 Markdown 报告",
        data=report,
        file_name="AI_DevFlow_中文运行报告.md",
        mime="text/markdown",
        use_container_width=True,
    )

    st.divider()

    st.subheader("B11 笔试交付说明")

    st.write(
        "Part A：七章 AI 研发团队组建方案。"
    )

    st.write(
        "Part B：可运行研发流水线、"
        "成功与失败测试、修复响应、"
        "质量门禁和人工审核。"
    )

    st.write(
        "配套材料：README、EVIDENCE、"
        "Git 版本记录和演示录屏。"
    )
