
"""B11 final documentation consistency check and review template.

Does not modify original test logs, task results or approval states.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PATCHES = {
    "README.md": [
        (
            "**当前界面中的真实任务入口与 `core.auto_pipeline` "
            "的完整自动修复流程不是同一个入口。** "
            "完整自动研发闭环以第 4.4 节的 CLI 命令为准。",
            "当前 Streamlit「新建研发任务」页面已接入 "
            "`core.auto_pipeline.run_pipeline()`，支持真实 API "
            "规划、代码生成、静态检查、Docker 测试、有限次数"
            "自动修复和报告展示。首页仍保留历史任务展示功能。",
        ),
        (
            "CI 配置主要覆盖离线 MOCK 流水线和工程测试。"
            "新版 Docker 验收是否已经在远端 GitHub Actions "
            "运行成功，需要以实际工作流记录为准。",
            "2026 年 11 月 21 日，GitHub Actions 已有成功"
            "运行记录。CI 包含工程测试、MOCK 流水线、"
            "Docker 正式验收、故意失败与修复回归，以及"
            "新增的 12 项独立补充验收及源码哈希校验。"
            "普通 CI 不调用收费模型 API。",
        ),
    ],
    "EVIDENCE.md": [
        (
            "| 工程单元测试 | 9 项 |",
            "| 工程单元测试 | 13 项 |",
        ),
        (
            "`9 passed in 2.25s`",
            "`13 passed in 2.80s`（最终本地复验；此前为 9 项）",
        ),
        (
            "当前本地测试已验证；**远端 CI 是否通过，"
            "仍须以 GitHub Actions 的实际执行记录为准，"
            "不能仅凭配置文件存在就宣称成功。**",
            "2026 年 11 月 21 日，GitHub Actions 最新提交"
            "`373b5dd` 的工作流已显示成功。"
            "远端 CI 包含工程测试、Docker 正式验收、"
            "受控故障注入和 12 项补充独立验收。",
        ),
        (
            "建议 CI 默认不调用收费 API，而是执行"
            "离线工程测试和已有候选代码的 Docker 回归测试。",
            "当前 CI 默认不调用收费模型 API，"
            "通过保存的候选代码、MOCK 流水线和 Docker "
            "回归测试复现结果。",
        ),
        (
            "本次文档记录的两组成功实验：",
            "本次文档记录的三组真实 API 实验：",
        ),
        (
            "| 实验 A：完整自动研发 | 23,387 |\n"
            "| 实验 B：真实红灯→绿灯 | 9,120 |\n"
            "| **两组实验合计** | **32,507** |",
            "| 实验 A：完整自动研发 | 23,387 |\n"
            "| 实验 B：真实红灯→绿灯 | 9,120 |\n"
            "| 实验 C：网页端自动研发 | 17,066 |\n"
            "| **三组实验合计** | **49,573** |",
        ),
        (
            "这是上述两组成功实验的 Token 合计，"
            "不代表项目开发期间全部 API 消耗。",
            "这是上述三组留存实验的 Token 合计，"
            "不代表项目开发期间全部 API 消耗，"
            "也不等于人民币实际账单。",
        ),
        (
            "- CI 的远端运行状态需要独立核验。",
            "- GitHub Actions 最新工作流已验证成功；"
            "后续新提交仍须重新检查 CI 状态。",
        ),
        (
            "最关键的两项证据是：",
            "最关键的三项证据是：",
        ),
        (
            "两项实验均未自动部署代码，人工审核状态仍为 PENDING。",
            "**实验 C：网页端真实开发与一次自动修复，"
            "最终 15/15 通过。**\n\n"
            "三项实验均未自动部署代码，原始运行记录中的"
            "人工审核状态仍为 PENDING。",
        ),
        (
            "最终交付前仍需确认 GitHub CI 实际运行结果、"
            "Part A 与当前实现状态的一致性，以及提交包的完整性。",
            "GitHub CI 和核心工程测试已经验证。"
            "最终仍需完成人工代码审核记录、"
            "不超过 5 分钟的 MP4、ZIP 完整性检查及按时提交。",
        ),
    ],
    "01_Team_Proposal.md": [
        (
            "工程单元测试另有 9 项。",
            "工程单元测试已扩展为 13 项；"
            "另外有 12 项生成后独立执行的补充边界测试。",
        ),
        (
            "以上两组实验的成功调用合计 32,507 Tokens，"
            "不代表整个项目开发期间的全部 API 消耗。",
            "实验 A 与 B 合计消耗 32,507 Tokens，"
            "另有实验 C 消耗 17,066 Tokens。"
            "三组留存实验合计 49,573 Tokens，"
            "不代表项目全部历史 API 消耗。",
        ),
    ],
}


REVIEW_TEMPLATE = """# AI DevFlow｜人工代码审核记录

## 一、审核对象

- 项目：B11 · AI DevFlow
- 场景：赛事影像上传日志分析
- 候选代码：
  `evidence/real_api/20261121-102456-2bf362/round_01/candidate.py`
- 候选 SHA256：
  `242c45fbc7cbb358d191a825092bf5458edfb6b8b1b45b4fe4811e80afc8b5a`
- Git 基线：`373b5dd`（后续文档提交不改变历史候选）
- 原始任务状态：`TESTS_PASSED_REVIEW_PENDING`
- 生产发布权限：未授予

## 二、已经取得的自动化证据

- 工程测试：13 passed
- 正式 Docker 验收：15 passed
- 独立补充 Docker 验收：12 passed
- GitHub Actions：最新工作流运行成功
- 受控故障注入：10 failed，经 DeepSeek 修复后 15 passed

上述结果属于自动化证据，不能代替人工代码审核。

## 三、需要本人实际检查的事项

请先打开候选源代码并逐项检查，再勾选。

- [ ] 已阅读 `parse_line` 的日志字段解析及非法输入处理
- [ ] 已阅读 `analyze_logs` 的统计累加及异常明细上限
- [ ] 已确认 `analyze_text` 复用同一统计逻辑
- [ ] 已检查是否存在不必要的文件、网络和子进程操作
- [ ] 已查看 15 项正式验收与 12 项独立补充验收日志
- [ ] 已了解当前测试覆盖范围和未覆盖的边界
- [ ] 已确认没有把测试通过当作生产发布授权
- [ ] 已确认现有结果仅适用于日志分析 MVP

## 四、人工审核发现

实际发现的问题：

（审核后填写。没有发现问题也须如实记录检查范围。）

已知限制：

1. 当前使用模拟日志，不涉及真实生产业务数据。
2. 测试通过不代表不存在未知缺陷。
3. Docker 限制不等于生产级安全沙箱。
4. 尚未进行生产发布与实际回滚演练。

## 五、审核结论（本人填写）

- 审核人：
- 审核日期：
- 审核结果（选择一项）：
  - [ ] 已人工审阅，可作为 B11 MVP 演示候选
  - [ ] 需要修改后重新审核
  - [ ] 尚未完成审核
- 审核备注：

**说明：**

人工确认可作为 MVP 演示，不等于批准生产部署。

历史 `result.json` 中的 `PENDING` 是执行结束时的真实状态，
不应被事后覆盖为 `APPROVED`。

如完成此次人工审核，以本文件作为后续独立审核记录。
"""


def replace_checked(
    content: str,
    old: str,
    new: str,
    filename: str,
) -> str:
    if old in content:
        return content.replace(old, new, 1)

    if new in content:
        return content

    raise RuntimeError(
        f"{filename} 中找不到待替换的原文。\n"
        "为避免错误修改，程序已停止。\n"
        f"查找内容：{old[:90]}"
    )


def main() -> None:
    updated = {}

    # Check all documents before writing any changes.
    for name, changes in PATCHES.items():
        path = ROOT / name

        if not path.is_file():
            raise FileNotFoundError(path)

        content = path.read_text(encoding="utf-8")

        for old, new in changes:
            content = replace_checked(
                content,
                old,
                new,
                name,
            )

        updated[path] = content

    evidence_path = ROOT / "EVIDENCE.md"
    evidence = updated[evidence_path]

    review_reference = (
        "\n\n## 人工审核记录说明\n\n"
        "人工代码审核清单位于 "
        "`reports/human_review_checklist.md`。\n\n"
        "原始实验状态 `PENDING` 保持不变。"
        "审核人完成实际代码检查后，"
        "在独立清单中填写姓名、日期、发现及结论。\n"
        "MVP 演示审核不等于生产发布批准。\n"
    )

    if "## 人工审核记录说明" not in evidence:
        updated[evidence_path] += review_reference

    for path, content in updated.items():
        if path.read_text(encoding="utf-8") != content:
            path.write_text(
                content,
                encoding="utf-8",
            )

        print(f"已同步：{path.relative_to(ROOT)}")

    review_path = (
        ROOT / "reports" / "human_review_checklist.md"
    )

    review_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not review_path.exists():
        review_path.write_text(
            REVIEW_TEMPLATE,
            encoding="utf-8",
        )
        print("已生成：reports/human_review_checklist.md")
    else:
        print("人工审核文件已存在，未覆盖原有内容。")

    print()
    print("B11 文档同步完成。")
    print("请实际完成人工审核清单，再提交 Git。")
    print("不会修改任何历史 result.json 或测试日志。")


if __name__ == "__main__":
    main()
