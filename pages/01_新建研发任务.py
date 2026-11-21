
"""AI DevFlow - Streamlit 真实 AI 自动研发工作台。

固定 B11 日志分析业务场景：
Planner -> Developer -> Static Gate -> Docker Pytest
-> Repair -> Regression -> Human Review
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.auto_pipeline import ACCEPTANCE, CONTRACT, run_pipeline
from core.real_task import TASKS_DIR


st.set_page_config(
    page_title="真实 AI 自动研发｜AI DevFlow",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    .stApp {
        background: #F8FAFC;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 1.4rem;
    }

    .task-hero {
        background: linear-gradient(115deg, #101C33, #173765);
        border-radius: 16px;
        padding: 28px 34px;
        color: white;
        margin: 12px 0 24px;
    }

    .task-hero h1 {
        color: white;
        margin: 0;
        font-size: 32px;
    }

    .task-hero p {
        color: #D3E4FA;
        margin: 10px 0 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def read_json(path: Path) -> dict | None:
    try:
        content = json.loads(
            path.read_text(encoding="utf-8")
        )
        return content if isinstance(content, dict) else None
    except (OSError, ValueError):
        return None


def task_history() -> list[str]:
    if not TASKS_DIR.is_dir():
        return []

    task_ids = []

    for result_file in TASKS_DIR.glob("*/result.json"):
        data = read_json(result_file)

        if (
            data
            and isinstance(data.get("rounds"), list)
            and "api_calls" in data
        ):
            task_ids.append(result_file.parent.name)

    return sorted(task_ids, reverse=True)


def safe_text(folder: Path, name: str | None) -> str:
    if not name:
        return ""

    path = (folder / name).resolve()

    try:
        path.relative_to(folder.resolve())
    except ValueError:
        return ""

    if not path.is_file():
        return ""

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""


def token_total(data: dict) -> int:
    total = 0

    for call in data.get("api_calls", []):
        usage = call.get("usage") or {}
        total += int(
            usage.get("total_tokens") or 0
        )

    return total


st.page_link(
    "dashboard.py",
    label="返回项目总览",
    icon="🏠",
)

st.markdown(
    """
    <div class="task-hero">
        <h1>真实 AI 自动研发</h1>
        <p>
            DeepSeek Planner → Developer → 静态检查
            → Docker Pytest → Repair → 人工审核
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "当前为 B11 固定场景 MVP：赛事影像上传日志分析。"
    "正式需求与 15 项验收测试已绑定。"
    "暂不支持任意业务需求使用这组测试。"
)


# ===== 1. 读取正式业务需求 =====

if CONTRACT.is_file():
    contract_text = CONTRACT.read_text(
        encoding="utf-8"
    )
else:
    contract_text = (
        "正式需求文件不存在，请检查 "
        "workspace/requirements/task.md。"
    )


# ===== 2. 创建真实研发任务 =====

with st.form("full_pipeline_form"):
    st.subheader("正式业务需求")

    st.text_area(
        "当前已绑定的业务规范（只读）",
        value=contract_text,
        height=220,
        disabled=True,
    )

    repairs = st.select_slider(
        "最多自动修复轮数",
        options=[0, 1, 2, 3],
        value=2,
    )

    confirmed = st.checkbox(
        "确认调用真实 DeepSeek API，并允许消耗 Token"
    )

    submitted = st.form_submit_button(
        "开始完整 AI 研发（含 Docker 测试和自动修复）",
        type="primary",
        use_container_width=True,
    )


if submitted:
    if not confirmed:
        st.error("请先勾选真实 API 调用确认。")

    elif (
        not CONTRACT.is_file()
        or not ACCEPTANCE.is_file()
    ):
        st.error(
            "正式需求或验收测试文件不存在，"
            "未调用 API。"
        )

    else:
        try:
            with st.spinner(
                "正在执行完整流水线。"
                "测试和修复结果将在任务结束后显示……"
            ):
                outcome = run_pipeline(
                    CONTRACT,
                    max_repairs=repairs,
                )

            st.session_state["full_history"] = (
                outcome["task_id"]
            )

            if (
                outcome["status"]
                == "TESTS_PASSED_REVIEW_PENDING"
            ):
                st.success(
                    "完整流水线执行成功："
                    "自动验收通过，等待人工审核。"
                )
            else:
                st.warning(
                    "流水线已记录实际失败或阻断状态，"
                    "请查看下面的逐轮证据。"
                )

        except Exception as exc:
            st.error(
                "启动失败，未完成完整流水线："
                f"{type(exc).__name__}: {exc}"
            )


# ===== 3. 读取完整研发历史 =====

st.divider()
st.subheader("历史完整流水线任务")

history = task_history()

if not history:
    st.info(
        "尚无完整流水线记录。"
        "可在上方启动首次真实任务。"
    )
    st.stop()

if st.session_state.get("full_history") not in history:
    st.session_state["full_history"] = history[0]

selected = st.selectbox(
    "选择任务编号",
    history,
    key="full_history",
)

folder = TASKS_DIR / selected
data = read_json(folder / "result.json")

if not data:
    st.error("读取 result.json 失败。")
    st.stop()


# ===== 4. 展示真实指标 =====

status = data.get("status", "UNKNOWN")
rounds = data.get("rounds", [])
last = rounds[-1] if rounds else {}

validation = last.get("validation") or {}

final_static = (
    (last.get("checks") or {}).get("all_passed")
    is True
)

repair_calls = sum(
    str(item.get("stage", "")).startswith("repair_")
    for item in data.get("api_calls", [])
)

st.caption(
    f"任务 {selected} · "
    f"模型 {data.get('model', '未知')} · "
    f"状态 {status}"
)

a, b, c, d = st.columns(4)

a.metric(
    "实际 API Token",
    f"{token_total(data):,}",
)

b.metric(
    "自动修复次数",
    repair_calls,
)

c.metric(
    "最终静态检查",
    "通过" if final_static else "未通过/未执行",
)

if validation.get("tests_executed"):
    d.metric(
        "Docker 功能验收",
        (
            f"{validation.get('passed_count', 0)}/"
            f"{validation.get('expected_tests', 15)}"
        ),
    )
else:
    d.metric(
        "Docker 功能验收",
        "未执行",
    )


# ===== 5. 审核状态 =====

if status == "TESTS_PASSED_REVIEW_PENDING":
    st.success(
        "全部可信验收已通过。"
        "人工审核仍为 PENDING，"
        "未部署生产环境。"
    )
else:
    st.warning(
        "本任务未通过全部验收，"
        "或者尚未执行完整验收，"
        "不得标记为已交付。"
    )

    if data.get("error"):
        st.error(str(data["error"]))


# ===== 6. 各轮自动修复记录 =====

st.subheader("每轮研发与质量门禁")

if not rounds:
    st.info(
        "没有生成候选轮次。"
        "请查看报告中的具体错误。"
    )

for item in rounds:
    round_num = item.get("round", "?")
    checks = item.get("checks") or {}
    val = item.get("validation") or {}

    is_static_ok = (
        checks.get("all_passed") is True
    )

    label = (
        f"Round {round_num}  |  "
        f"静态检查："
        f"{'通过' if is_static_ok else '未通过'}"
        f"  |  "
        f"Pytest：{val.get('status', '未执行')}"
    )

    with st.expander(
        label,
        expanded=(item is rounds[-1]),
    ):
        st.caption(
            f"源码：{item.get('candidate', '未知')}"
        )

        st.code(
            str(item.get("sha256", "")),
            language="text",
        )

        if not is_static_ok:
            failure = safe_text(
                folder,
                (
                    f"round_{int(round_num):02d}"
                    "/static_failures.txt"
                ),
            )

            if failure:
                st.code(
                    failure,
                    language="text",
                )

            for note in checks.get("notes", []):
                st.write(str(note))

        else:
            st.success("静态检查通过")

        if val:
            st.write(
                f"Docker 测试状态："
                f"{val.get('status')}；"
                f"通过 {val.get('passed_count', 0)}，"
                f"失败 {val.get('failed_count', 0)}"
            )

            log_path = (
                f"{item.get('validation_dir')}/pytest.txt"
                if item.get("validation_dir")
                else None
            )

            log = safe_text(
                folder,
                log_path,
            )

            if log:
                st.code(
                    log[-16000:],
                    language="text",
                )


# ===== 7. 开发计划、源码、报告 =====

plan_tab, code_tab, report_tab = st.tabs(
    [
        "开发计划",
        "最终候选源码",
        "完整报告",
    ]
)


with plan_tab:
    plan = safe_text(
        folder,
        "plan.md",
    )

    if plan:
        st.markdown(plan)

        st.download_button(
            "下载开发计划",
            plan,
            file_name=f"{selected}-plan.md",
        )
    else:
        st.info("暂无开发计划。")


with code_tab:
    relative_code = (
        data.get("final_candidate")
        or last.get("candidate")
    )

    source = safe_text(
        folder,
        relative_code,
    )

    if source:
        st.code(
            source,
            language="python",
        )

        st.download_button(
            "下载候选代码",
            source,
            file_name=f"{selected}-candidate.py",
        )
    else:
        st.info("暂无候选代码。")


with report_tab:
    report = safe_text(
        folder,
        "report.md",
    )

    if report:
        st.markdown(report)

        st.download_button(
            "下载完整报告",
            report,
            file_name=f"{selected}-report.md",
        )
    else:
        st.info("暂无报告。")


st.caption(
    "本页面不执行代码合并或生产发布；"
    "测试通过不等于人工审核批准。"
)
