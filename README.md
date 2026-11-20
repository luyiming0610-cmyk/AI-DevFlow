
# AI DevFlow｜AI 智能研发流水线

## 一、项目介绍

本项目针对 B11《组建 AI 研发团队》笔试题，
开发一个最小可运行的 AI Agent 研发流水线。

业务场景：赛事影像上传日志分析工具。

项目旨在演示：

需求读取 → 代码生成 → 自动测试 → 失败响应
→ 回归验证 → 质量门禁 → 人工审核。

本项目包含本地 MOCK 演示与真实 DeepSeek
修复实验，明确区分两者的验证结果。

## 二、技术栈

- Python 3.12
- DeepSeek API（可选）
- Pytest
- Ruff
- Streamlit
- Git / GitHub Actions

Agent 编排使用 Python 自行实现，
不依赖大型 Agent 框架。

## 三、环境安装

建议使用 Python 3.12。

### Windows PowerShell

创建虚拟环境：

```powershell
python -m venv .venv
```

安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### macOS / Linux

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## 四、一条命令运行 MVP

MOCK 模式不需要 API Key。

Windows：

```powershell
.\.venv\Scripts\python.exe main.py
```

macOS / Linux：

```bash
.venv/bin/python main.py
```

默认模式使用本地预设开发代码与修复逻辑。

预期流程：

1. 读取需求。
2. 生成开发计划。
3. 生成日志分析代码。
4. 执行首次测试并发现预设缺陷。
5. 根据错误日志进行确定性修复。
6. 重新运行测试。
7. 检查质量门禁。
8. 生成人工审核请求和报告。

MOCK 是为了使评审能够离线复现研发流程，
不应理解为大模型自主完成全部开发。

## 五、运行自动化测试

Windows：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

预期当前验收测试共三项。

首次运行流水线时预设一项失败用例，
修复后重新运行原有测试。

## 六、可视化控制台

Windows：

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard.py
```

浏览器访问：

http://localhost:8501

控制台提供：

- 研发需求展示
- MOCK 流水线运行
- 首次测试及回归测试
- 代码质量门禁
- 生成代码查看
- DeepSeek 实验记录
- 中文运行报告

网页一键执行目前仅支持 MOCK 模式，
不会自动调用收费 API。

## 七、DeepSeek API 实验

真实模型实验使用 OpenAI 兼容接口连接 DeepSeek。

在项目根目录创建 `.env` 文件：

```dotenv
AI_MODE=mock
AI_API_KEY=你的API密钥
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-flash
```

不要将真实 API Key 上传至版本库。

执行真实修复实验时：

```powershell
.\.venv\Scripts\python.exe verify_api_repair.py --call-api
```

注意：

- 该命令将实际调用付费 API。
- 当前脚本为避免覆盖证据，会拒绝使用已有实验目录。
- 模型生成的代码不会被直接执行。
- 调用失败及 Token 消耗以实际日志为准。
- 不需要为复现 MOCK 流水线运行该命令。

## 八、真实修复验证结果

已有一次真实 DeepSeek 修复实验：

- 模型：deepseek-flash
- 输入 Token：667
- 输出 Token：281
- 合计 Token：948
- 模型生成修复候选：成功
- 候选代码功能回归：3 项通过
- 人工审核：PENDING
- 生产环境部署：未执行

验证记录：

- `reports/api_repair_evidence.json`
- `reports/api_repair_validation.json`
- `reports/api_repair_pytest.txt`
- `reports/api_repair_candidate.py`

验证结果仅适用于本次候选代码和当前测试集。

## 九、质量门禁

当前实现的检查包括：

1. Python 语法检查。
2. 基础代码安全规则扫描。
3. Ruff 静态检查。
4. Pytest 自动化测试。

质量门禁通过后，仍需工程师进行人工审核。

本项目没有向 Agent 授予生产部署权限。

## 十、人工审核和安全边界

- 使用 Git 管理代码版本。
- 记录测试结果及 SHA256 哈希。
- 质量门禁失败时阻断交付。
- 人工审核未完成前不自动发布。
- 当前临时测试目录不等于系统级沙箱。
- 不应直接执行未经检查的模型生成代码。

## 十一、项目文件

- `01_Team_Proposal.md`：Part A 七章方案。
- `main.py`：MVP 主流水线。
- `agents/`：Agent 实现。
- `core/`：模型调用与质量门禁等模块。
- `tests/`：自动化测试。
- `dashboard.py`：可视化界面。
- `reports/`：运行报告和实验记录。
- `EVIDENCE.md`：测试、失败响应及引用证据。
- `.github/workflows/ci.yml`：CI 配置。

## 十二、已知局限

1. MOCK 模式使用预设代码和确定性修复。
2. 真实模型修复已完成单次实验，但未构成
   任意需求的全自动软件开发系统。
3. 尚未具备生产级安全执行沙箱。
4. 当前测试集只覆盖三个主要验收场景。
5. 当前 MVP 没有验证企业级交付周期缩短效果。

## 十三、笔试交付对应

Part A：七章 AI 研发团队建设方案。

Part B：最小可运行研发流水线，
包含通过测试、故意失败测试、修复响应、
质量门禁、中文报告和可复现命令。

详细证据见 `EVIDENCE.md`。
