# AI DevFlow｜B11 研发流水线运行证据

**项目：** B11 · 组建 AI 研发团队
**MVP 场景：** 赛事影像上传日志分析工具
**验证日期：** 2026 年 11 月 21 日
**状态：** 真实研发流水线已通过机器验收，人工审核仍为 PENDING

## 一、与 Part A 团队方案的对应关系

本 MVP 重点验证 `01_Team_Proposal.md` 中以下设计：

- **第二章 Agent 与工具链架构：** Planner、Developer、Tester、Repair 之间的协作，以及与 Python、Git、Pytest、Ruff 的集成。
- **第四章研发工作流与质量门禁：** 需求输入、代码生成、静态检查、Docker 隔离测试、失败响应、有限重试、人工审核。
- **第五章评估体系：** 测试通过率、修复结果、失败原因、Token 用量和可复现证据。
- **第七章风险与红线：** 最小权限、隔离执行、禁止 Agent 修改测试、禁止自动生产部署。

本项目是单一内部工具场景的工程 MVP，不代表已经实现企业级通用软件研发平台，也不能证明实际交付周期已经从六周缩短至两周。

## 二、运行环境

| 项目 | 实际环境 |
|---|---|
| 操作系统 | Windows |
| Python | 3.12.0 |
| 本地 Pytest | 9.2.0 |
| Docker 测试环境 | Linux / Python 3.12 |
| 代码检查 | Ruff |
| 大模型 | DeepSeek |
| 实际模型标识 | deepseek-flash |
| 版本控制 | Git |
| CI 配置 | GitHub Actions |
| 业务验收 | 15 项 |
| 工程单元测试 | 13 项 |

正式需求：`workspace/requirements/task.md`

正式验收测试：`acceptance/test_log_contract.py`

隔离测试模块：`core/isolated_tester.py`

真实编排器：`core/auto_pipeline.py`

## 三、实验 A：真实 DeepSeek 研发流水线

### 3.1 实验信息

任务编号：

`20261121-085152-bc4b86`

本实验使用真实 DeepSeek API，完成规划、代码生成、静态检查、自动修复与最终验收。

运行命令：

```powershell
.\.venv\Scripts\python.exe -m core.auto_pipeline --call-api --max-repairs 2
```

### 3.2 实际执行过程

| 阶段 | 实际结果 | 后续处理 |
|---|---|---|
| Planner | 成功生成开发计划 | 进入编码 |
| Developer | 生成第一版候选代码 | 进入静态检查 |
| Round 0 | 未批准的 `__future__` 导入 | 触发 Repair 1 |
| Repair 1 | 生成第二版代码 | 重新检查 |
| Round 1 | Ruff 检出三个未使用导入 | 触发 Repair 2 |
| Repair 2 | 生成第三版代码 | 重新检查 |
| Round 2 | 静态检查通过 | 进入 Docker |
| Docker Pytest | **15 passed，0 failed** | 等待人工审核 |

Round 0 中的 `from __future__ import annotations` 属于 Python 合法语法，被当前导入白名单拦截，是偏保守规则引发的静态检查误报，并非已证实的代码安全漏洞。

Round 1 的问题为 Ruff F401，涉及 `typing.Any`、`typing.Iterable`、`typing.Iterator` 三项未使用导入。

本实验证明了真实模型能够响应静态质量门禁失败并进行有限次数修复。由于前两轮均被静态检查拦截，本次实验**没有出现 Pytest 红灯**。

### 3.3 实际 API Token

| 模型阶段 | 输入 Tokens | 输出 Tokens | 合计 |
|---|---:|---:|---:|
| Planner | 1,385 | 614 | 1,999 |
| Developer | 3,963 | 2,192 | 6,155 |
| Repair 1 | 5,516 | 1,977 | 7,493 |
| Repair 2 | 5,745 | 1,995 | 7,740 |
| **总计** | **16,609** | **6,778** | **23,387** |

上述 Token 为本次实际 API 响应记录，人民币费用以 DeepSeek 平台账单为准。

### 3.4 原始证据位置

`evidence/real_api/20261121-085152-bc4b86/`

关键文件：

- `requirement.md`：本次运行的业务需求快照。
- `acceptance_snapshot.py`：验收规则快照。
- `plan.md`：真实 Planner 输出。
- `result.json`：状态、模型调用、Token 和各轮结果。
- `report.md`：中文运行报告。
- `round_00/candidate.py`：初版代码。
- `round_00/static_failures.txt`：第一次静态检查失败。
- `round_01/candidate.py`：第一轮修复代码。
- `round_01/static_failures.txt`：第二次静态检查失败。
- `round_02/candidate.py`：最终通过验收的候选代码。
- `round_02/validation/pytest.txt`：Docker Pytest 实际输出。
- `round_02/validation/validation.json`：测试状态、数量及 SHA256。

最终状态：

`TESTS_PASSED_REVIEW_PENDING`

人工审核：`PENDING`

生产部署：`False`

## 四、实验 B：故意失败测试与真实 DeepSeek 修复

### 4.1 实验目的

满足 B11 对故意失败测试和 Agent 失败响应的要求，并验证：

**真实 Pytest 失败 → DeepSeek 读取错误日志 → 生成修复代码 → 完整回归通过**

本实验属于明确标记的受控故障注入。

初始缺陷由实验脚本人为注入，不宣称是 DeepSeek 自主产生的缺陷。

### 4.2 实验信息

任务编号：

`20261121-091420-597571`

实验脚本：

`experiments/demo_red_green.py`

输入基线：

`evidence/real_api/20261121-085152-bc4b86/round_02/candidate.py`

运行命令：

```powershell
.\.venv\Scripts\python.exe -m experiments.demo_red_green --source ".\evidence\real_api\20261121-085152-bc4b86\round_02\candidate.py" --max-repairs 2 --call-api
```

### 4.3 实际执行结果

| 步骤 | 实际结果 |
|---|---|
| 基线验证 | 原始候选通过全部 15 项验收 |
| 故障注入 | 仅修改独立实验副本 |
| 真实 Pytest 红灯 | **10 项失败** |
| DeepSeek Repair | 真实 API 调用成功 |
| 修复后回归 | **15 项全部通过** |
| 人工审核 | PENDING |
| 生产部署 | 未执行 |

故障注入没有修改正式验收测试，也没有覆盖实验 A 的最终候选代码。

实验 B 的模型调用记录：

- 输入 Tokens：7,151
- 输出 Tokens：1,969
- 合计 Tokens：**9,120**

### 4.4 原始证据位置

`evidence/red_green/20261121-091420-597571/`

关键证据包括：

- `baseline_good.py`：通过验收的基线源码。
- `faulty_seed.py`：人为注入缺陷的副本。
- `red_fault_validation/pytest.txt`：真实 Pytest 红灯日志。
- `red_fault_validation/validation.json`：失败统计。
- `repair_01.py`：DeepSeek 生成的修复候选。
- `repair_01_validation/pytest.txt`：修复后的完整回归结果。
- `result.json`：实验阶段、SHA256、Token 记录。
- `report.md`：实验总结。

本次实验展示了真实测试失败后，Agent 能够根据失败日志生成有效修复，并再次通过原有测试。

## 五、历史 MOCK 基线

早期流水线保留为离线演示，不需要 API Key。

入口：

```powershell
.\.venv\Scripts\python.exe main.py
```

历史实验结果：

- 首次执行：2 项通过、1 项故意失败。
- MOCK Repair：使用预设的确定性修复逻辑。
- 完整回归：3 项通过。

历史证据：

- `reports/before_repair_pytest.txt`
- `reports/after_repair_pytest.txt`
- `reports/quality_gate.json`
- `reports/review_request.json`

这一实验不属于真实大模型自主修复。

## 六、工程测试与质量门禁

2026 年 11 月 21 日本地执行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

实际结果：

`13 passed in 2.80s`（最终本地复验；此前为 9 项）

本地执行的 Git 检查：

```powershell
git diff --check
```

无报错。

质量门禁包括：

1. 业务需求与验收标准预检查。
2. Python 语法检查。
3. Ruff 静态代码检查。
4. 基础导入及风险调用筛查。
5. Docker 内真实 Pytest 测试。
6. 测试失败后的有限次数修复。
7. 各轮候选源码和 SHA256 留存。
8. 未经人工审核不得合并或发布。

静态检查属于基础筛查，不能替代安全审计；Docker 的网络、文件系统和资源限制可以降低风险，但不保证绝对隔离。

## 七、Git 与 CI 说明

本项目使用 Git 保存源码、需求、验收测试、实验脚本和精选运行证据。

`.env` 已通过本地检查，处于 Git 忽略状态，且未被版本库跟踪。

`runs/` 存储本地执行记录，不作为正式提交证据。

`evidence/` 存储经核验的实验记录，需要纳入提交。

GitHub Actions 配置位于：

`.github/workflows/ci.yml`

2026 年 11 月 21 日，GitHub Actions 最新提交`373b5dd` 的工作流已显示成功。远端 CI 包含工程测试、Docker 正式验收、受控故障注入和 12 项补充独立验收。

当前 CI 默认不调用收费模型 API，通过保存的候选代码、MOCK 流水线和 Docker 回归测试复现结果。

## 八、成本记录

本次文档记录的三组真实 API 实验：

| 实验 | Tokens |
|---|---:|
| 实验 A：完整自动研发 | 23,387 |
| 实验 B：真实红灯→绿灯 | 9,120 |
| 实验 C：网页端自动研发 | 17,066 |
| **三组实验合计** | **49,573** |

这是上述三组留存实验的 Token 合计，不代表项目开发期间全部 API 消耗，也不等于人民币实际账单。

未将历史调用、失败尝试或其他实验擅自合并为总账。

## 九、已知边界与未完成事项

- 当前主要验证日志分析这一特定内部工具场景。
- 真实验收测试通过不代表所有未知输入都正确。
- 人工 Review 尚未完成。
- 未执行生产部署。
- 未证明生产级安全沙箱能力。
- 尚未证明企业整体效率提升幅度。
- GitHub Actions 最新工作流已验证成功；后续新提交仍须重新检查 CI 状态。
- 当前真实实验规模不足以推断模型长期修复成功率。

## 十、参考资料与引用清单

以下为项目使用或参考的公开技术文档：

1. Python 官方文档：https://docs.python.org/3/
2. Pytest 官方文档：https://docs.pytest.org/
3. Ruff 官方文档：https://docs.astral.sh/ruff/
4. Docker 官方文档：https://docs.docker.com/
5. Git 官方文档：https://git-scm.com/docs
6. GitHub Actions 官方文档：https://docs.github.com/actions
7. DeepSeek API 官方文档：https://api-docs.deepseek.com/
8. Streamlit 官方文档：https://docs.streamlit.io/


## 十一、实验 C：网页端真实自动研发闭环

### 11.1 实验目标

验证 Streamlit 网页能否调用已经完成的真实
DeepSeek 自动研发编排器，而不只是生成代码。

完整链路：

网页提交任务 → Planner → Developer →
静态质量门禁 → Repair → Docker Pytest →
质量报告 → 等待人工审核。

### 11.2 实际运行信息

- 任务编号：20261121-102456-2bf362
- 执行方式：Streamlit 网页
- 模型：deepseek-flash
- 真实 API Token：17,066
- 自动修复：1 次
- 最终静态检查：通过
- Docker 验收：15 passed，0 failed
- 最终状态：TESTS_PASSED_REVIEW_PENDING
- 人工审核：PENDING
- 生产部署：False

### 11.3 逐轮结果

| 阶段 | 实际结果 |
|---|---|
| Planner | 真实 API 规划成功 |
| Developer | 真实 API 生成代码 |
| Round 0 | 静态检查失败，功能测试未执行 |
| Repair 1 | DeepSeek 自动生成修复代码 |
| Round 1 | 静态检查通过 |
| Docker Pytest | 15/15 通过 |

本实验确认了网页端的真实自动修复与回归测试能力。

Round 0 属于静态检查失败，不应描述为
Pytest 失败。Pytest 红灯到绿灯的独立证据
见实验 B。

### 11.4 原始证据

evidence/real_api/20261121-102456-2bf362/

其中包含：

- requirement.md：需求快照
- acceptance_snapshot.py：验收用例快照
- plan.md：开发计划
- result.json：完整执行状态和 Token
- report.md：中文报告
- round_00/：原始候选与静态失败记录
- round_01/candidate.py：修复后的候选
- round_01/validation/pytest.txt：真实测试日志
- round_01/validation/validation.json：机器验收结果

所有自动检查通过后仍然等待人工审核，
未执行代码合并或生产部署。

### 11.5 三组真实实验总结

| 实验 | 核心证明 | 结果 |
|---|---|---|
| A | Planner、Developer 与两轮 Repair | 15/15 |
| B | 人为故障注入、真实 Pytest 失败与 AI 修复 | 10 failed → 15 passed |
| C | 网页端自动研发与一次真实修复 | 15/15 |

三组实验记录的 Token 合计为 49,573。
这是这三组实验的合计，不代表整个项目
所有 API 调用的累计费用。


## 十二、结论

本项目已完成 B11 Part B 所要求的最小 Agent 研发闭环，并通过真实 API 与 Docker 测试提供可核验的结果。

最关键的三项证据是：

**实验 A：真实 Planner + Developer + 两轮 Repair，最终 15/15 通过。**

**实验 B：人为注入缺陷导致真实 Pytest 10 项失败，经真实 DeepSeek Repair 后 15/15 通过。**

**实验 C：网页端真实开发与一次自动修复，最终 15/15 通过。**

三项实验均未自动部署代码，原始运行记录中的人工审核状态仍为 PENDING。

GitHub CI 和核心工程测试已经验证。最终仍需完成人工代码审核记录、不超过 5 分钟的 MP4、ZIP 完整性检查及按时提交。


## 附录：补充独立验收与门禁回归

2026-11-21 对静态质量门禁进行回归验证。

修复内容：
仅允许合法的
`from __future__ import annotations`
通过导入白名单，同时继续禁止未批准导入
及 eval 等危险调用。

工程单元测试：13 passed。

另外，针对网页实验 C 的已生成候选代码，
增加 12 项未提供给该次模型生成流程的
独立补充测试。

候选文件：
`evidence/real_api/20261121-102456-2bf362/round_01/candidate.py`

候选 SHA256：
`242c45fbc7cbb358d191a825092bf5458edfb6b8b1b45b4bfe4811e80afc8b5a`

补充测试 SHA256：
`df0bc4e4e5d9991d895f4379b20b0ba3afad786a43d3124ce6bf79a9b10f7afa`

独立 Docker 验收：
12 passed，0 failed，状态 PASSED。

原始证据：
`evidence/holdout/20261121-102456-2bf362/`

说明：
补充用例在原候选生成后编写，
未发送给该次 Planner、Developer、Repair。
这是单一业务场景的补充边界验证，
并非真实生产数据评测，也不代表多任务泛化性能。

业务价值说明：
`reports/business_value.md`

人工审核：PENDING。
生产部署：False。


## 人工审核记录说明

人工代码审核清单位于 `reports/human_review_checklist.md`。

原始实验状态 `PENDING` 保持不变。审核人完成实际代码检查后，在独立清单中填写姓名、日期、发现及结论。
MVP 演示审核不等于生产发布批准。
