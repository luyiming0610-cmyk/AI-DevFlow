# AI DevFlow｜Agent 驱动的软件研发流水线

**B11《组建 AI 研发团队》笔试项目**

AI DevFlow 是一个基于 Python 和 DeepSeek API 的轻量级 AI 软件研发流水线。系统以赛事影像上传日志分析工具为 MVP 场景，验证 Agent 从业务需求到代码生成、自动测试、失败修复和人工审核的完整过程。

项目同时保留离线 MOCK 基线与真实 API 研发流程，所有实验结果明确区分，不混用或伪造测试证据。

## 1. 核心功能

真实 API 流水线包括：

1. **Planner Agent**：读取需求文档，生成开发计划。
2. **Developer Agent**：根据规范及验收测试生成 Python 代码。
3. **Static Quality Gate**：执行语法检查、基础安全检查和 Ruff 静态检查。
4. **Docker Tester**：在受限 Docker 容器内执行真实 Pytest。
5. **Repair Agent**：读取失败日志并自动生成修复代码，按照配置进行有限次数重试。
6. **Reporter**：保存各轮源码、SHA256、测试记录、Token 使用量和中文报告。
7. **Human Review Gate**：测试通过后仍需人工审核，系统不自动合并或生产部署。

系统采用轻量级 Python 编排，不依赖大型 Agent 框架。

## 2. 技术栈

| 组件 | 技术 |
|---|---|
| 开发语言 | Python 3.12 |
| 模型 | DeepSeek API |
| 研发编排 | Python |
| 功能测试 | Pytest 9.2.0 |
| 代码检查 | Ruff |
| 隔离执行 | Docker Desktop / Docker Engine |
| 管理界面 | Streamlit |
| 版本管理 | Git |
| 持续集成 | GitHub Actions |
| 运行证据 | Markdown、JSON、SHA256、Pytest 日志 |

## 3. 安装

要求安装 Python 3.12。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

不调用模型的基础测试无需 DeepSeek API Key，也无需启动 Docker。

运行工程测试：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

截至 2026 年 11 月 21 日，本地已验证 13 项工程测试通过。

## 4. 真实 DeepSeek 自动研发流水线

### 4.1 配置 API

在项目根目录创建本地 `.env` 文件。

参考 `.env.example`，配置真实 API Key、模型和服务地址。

示例：

```dotenv
AI_MODE=mock
AI_API_KEY=YOUR_DEEPSEEK_API_KEY
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-flash
```

真实研发命令显式启用 API 模式，不会自动回退到 MOCK。

**禁止将真实 `.env`、API Key 或其他凭据提交到 Git。**

### 4.2 准备 Docker

安装并启动 Docker Desktop，使用 Linux Containers。

在项目根目录构建隔离测试镜像：

```powershell
docker build -t aidevflow-test:1 .\docker\runner
```

验证镜像：

```powershell
docker image inspect aidevflow-test:1
```

### 4.3 预检查

```powershell
.\.venv\Scripts\python.exe -m core.auto_pipeline
```

预检查验证业务规范、15 项验收测试以及 Docker 镜像是否准备就绪，不调用收费模型 API。

### 4.4 一条命令运行真实研发 MVP

```powershell
.\.venv\Scripts\python.exe -m core.auto_pipeline --call-api --max-repairs 2
```

这条命令实际调用 DeepSeek API，产生 Token 费用。

系统自动执行：

需求分析 → 代码生成 → 静态检查 → Docker 测试 → 必要时自动修复 → 完整回归测试 → 生成报告 → 等待人工审核。

每轮代码保存在独立任务目录，不覆盖已有版本。

默认最多执行两轮 Repair，可通过参数调整；超出修复上限或遇到基础设施异常时阻断。

### 4.5 运行状态

- `TESTS_PASSED_REVIEW_PENDING`：全部机器验收通过，等待人工审核。
- `ESCALATED_TO_HUMAN`：达到修复上限，仍未通过验收。
- `ESCALATED_UNCHANGED_REPAIR`：模型重复输出相同代码，停止无效重试。
- `BLOCKED_TEST_INFRASTRUCTURE`：隔离测试环境异常。
- `PIPELINE_ERROR`：发生编排或 API 异常。

通过机器测试不代表已经获得人工批准，也不代表代码已部署。

## 5. 正式验收测试

本项目选择一个内部工具场景：**赛事影像上传日志分析**。

正式业务规范：

`workspace/requirements/task.md`

正式验收测试：

`acceptance/test_log_contract.py`

当前规范要求提供三个公开函数：

- `parse_line`
- `analyze_logs`
- `analyze_text`

验收涉及日志解析、成功失败统计、非法日期、错误明细、流式输入、兼容接口和统计一致性等。

共有 15 项独立验收测试。

正式测试不由 Repair Agent 修改。

## 6. 已完成的真实 API 实验

### 实验 A：真实规划、编码和自动修复

任务编号：

`20261121-085152-bc4b86`

执行结果：

| 阶段 | 结果 |
|---|---|
| Planner | 真实 DeepSeek 调用成功 |
| Developer | 真实 DeepSeek 调用成功 |
| Round 0 | 静态检查阻断 |
| Repair 1 | 真实修复 |
| Round 1 | Ruff 检查阻断 |
| Repair 2 | 真实修复 |
| Round 2 | 静态检查通过 |
| Docker Pytest | 15/15 通过 |
| 人工审核 | PENDING |
| 生产部署 | 未执行 |

总消耗：23,387 Tokens。

其中 Round 0 的 `__future__` 导入阻断属于偏保守的静态规则引发的误报；Round 1 为未使用导入造成的 Ruff 检查失败。

本次实验没有产生 Pytest 红灯，因此另行进行了受控故障注入实验。

证据目录：

`evidence/real_api/20261121-085152-bc4b86/`

### 实验 B：受控故障注入与真实红灯→绿灯

任务编号：

`20261121-091420-597571`

本实验以已通过验收的代码为基线，只在独立副本中人为注入逻辑缺陷，不修改正式验收测试。

实验结果：

| 阶段 | 结果 |
|---|---|
| 原始代码 | Docker 验收通过 |
| 人为故障注入 | 在实验副本中制造错误 |
| Pytest 红灯 | 10 项失败 |
| DeepSeek Repair | 真实 API 修复 |
| 回归测试 | 15/15 通过 |
| 人工审核 | PENDING |
| 生产部署 | 未执行 |

本次 DeepSeek 调用消耗 9,120 Tokens。

证据目录：

`evidence/red_green/20261121-091420-597571/`

**说明：人为注入的错误与真实模型自主生成的错误是两种不同情况，本实验明确区分二者。**

### 复现实验 B

```powershell
.\.venv\Scripts\python.exe -m experiments.demo_red_green --source ".\evidence\real_api\20261121-085152-bc4b86\round_02\candidate.py" --max-repairs 2 --call-api
```

该命令将产生新的实验记录和真实 API 费用。


### 实验 C：Streamlit 网页端完整自动研发

任务编号：20261121-102456-2bf362

Streamlit 的「新建研发任务」页面现已接入
`core.auto_pipeline.run_pipeline()`。

启动命令：

```powershell
python -m streamlit run dashboard.py
```

在左侧导航进入「新建研发任务」，可以：

- 查看已绑定的 B11 业务需求
- 设置自动修复上限
- 显式确认真实 DeepSeek API 调用
- 启动完整研发流水线
- 查看每轮源码、测试和修复记录
- 下载候选代码及报告

最新实测：

- 真实 API Token：17,066
- 自动修复：1 次
- 最终静态检查：通过
- Docker Pytest：15/15 通过
- 人工审核：PENDING

原始证据：

`evidence/real_api/20261121-102456-2bf362/`

当前网页固定支持日志分析这一业务场景。
其他场景需要各自独立的验收规范，
不能直接复用现有 15 项测试。


## 7. 离线 MOCK 基线

项目保留早期 MOCK 流水线，用于无 API Key 的基础研发流程演示。

```powershell
.\.venv\Scripts\python.exe main.py
```

MOCK 使用预设的开发结果与确定性修复逻辑，不代表真实大模型自主生成、修复代码。

历史 MOCK 样例展示首次测试 2 通过、1 失败，经确定性修复后 3 项全部通过。

相关记录位于 `reports/`。

## 8. Streamlit 界面

启动：

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

浏览器访问：

`http://localhost:8501`

页面提供需求查看、历史验证案例及交互式真实任务功能。

**当前界面中的真实任务入口与 `core.auto_pipeline` 的完整自动修复流程不是同一个入口。** 完整自动研发闭环以第 4.4 节的 CLI 命令为准。

## 9. 项目目录

| 路径 | 职责 |
|---|---|
| `agents/` | 各角色 Agent |
| `core/` | 模型客户端、编排器、测试器、质量门禁 |
| `acceptance/` | 正式业务验收用例 |
| `tests/` | 工程测试 |
| `experiments/` | 故障注入及可复现实验 |
| `docker/` | 受限测试环境 |
| `evidence/` | 正式留存的实验源码和报告 |
| `reports/` | 历史 MOCK 报告 |
| `runs/` | 本地运行记录，不进入 Git |
| `pages/` | Streamlit 页面 |
| `workspace/` | 业务需求及工作区 |
| `.github/workflows/` | CI 配置 |

## 10. 安全、版本与质量要求

系统遵守以下约束：

- AI 生成的代码不直接在宿主机执行。
- 测试容器关闭网络并限制资源和权限。
- 静态扫描不等同于完整安全审计。
- 每一轮候选代码独立保存并记录 SHA256。
- Repair Agent 不能修改或削弱验收测试。
- 环境故障、测试失败和修复失败不能伪装为通过。
- 不自动执行 Git 合并或生产部署。
- 真实 API Key 不进入仓库。
- 人工审核状态未批准时不得发布。

Docker 隔离降低风险，但不等同于经过安全认证的生产级沙箱。

## 11. CI 与工程复现

当前仓库包含：

`.github/workflows/ci.yml`

CI 配置主要覆盖离线 MOCK 流水线和工程测试。新版 Docker 验收是否已经在远端 GitHub Actions 运行成功，需要以实际工作流记录为准。

完整的真实 API 流水线不会在普通 CI 推送事件中自动执行，避免意外调用付费模型。

## 12. 已知局限

1. 当前正式验收主要针对日志分析这一特定内部工具，不是任意需求的通用软件开发系统。
2. 机器测试通过后仍需人工审核。
3. 尚未验证生产级安全沙箱及真实生产部署。
4. 当前实验不能证明企业级交付周期已经从 6 周缩短到 2 周。
5. 真实 API 的性能、费用和修复成功率不能直接由少量实验推广到生产规模。

## 13. B11 交付文件

**Part A：** `01_Team_Proposal.md`，七章团队建设和工程落地方案。

**Part B：** 本项目源码、验收测试、Docker 配置、真实模型研发记录、故障注入实验和人工审核门禁。

**证据说明：** `EVIDENCE.md`。

最终演示视频及提交包按照 B11 原题要求单独制作。

## 14. 技术参考

- Python：https://docs.python.org/3/
- Pytest：https://docs.pytest.org/
- Ruff：https://docs.astral.sh/ruff/
- Docker：https://docs.docker.com/
- GitHub Actions：https://docs.github.com/actions
- DeepSeek API：https://api-docs.deepseek.com/
- Streamlit：https://docs.streamlit.io/


## 补充独立验收

除原有 15 项业务验收外，新增 12 项独立边界测试。

测试文件：
`acceptance/test_log_holdout.py`

可在 Docker 环境中运行：

```powershell
python -m core.isolated_tester --candidate evidence/real_api/20261121-102456-2bf362/round_01/candidate.py --acceptance acceptance/test_log_holdout.py --output runs/holdout_replay
```

2026-11-21 本地实测：12 passed。

工程单元测试现为 13 项。
补充验证与原有真实 API 实验分开记录，
不需要再次调用 DeepSeek。

业务价值与指标口径：
`reports/business_value.md`
