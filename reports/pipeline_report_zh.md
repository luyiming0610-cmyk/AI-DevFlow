# AI DevFlow｜智能研发流水线运行报告

生成时间：2026-11-20 22:31:23

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
| 首次测试 | 2 项通过，1 项失败 |
| 修复后回归测试 | 3 项通过，0 项失败 |
| 综合质量门禁 | 通过 |
| 人工审核状态 | 待人工审核 |

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
| Python 语法检查 | 通过 |
| 基础安全规则检查 | 通过 |
| Ruff 静态代码检查 | 通过 |
| Pytest 自动化测试 | 通过 |

质量检查结果来自实际运行记录。

语法检查、Ruff 和基础安全规则
不等同于生产级安全审计。

## 六、真实 DeepSeek API 修复实验

本实验独立于 MOCK 主流水线，
真实调用 DeepSeek 分析 Pytest 失败日志并生成修复候选。

| 验证项目 | 实际记录 |
|---|---|
| 模型 | deepseek-flash |
| 调用状态 | CANDIDATE_GENERATED |
| 输入 Token | 667 |
| 输出 Token | 281 |
| 总 Token | 948 |
| 候选代码哈希一致 | 是 |
| 独立回归测试 | 3 项通过，0 项失败 |
| 功能验证结论 | 通过：真实模型修复候选已通过原有三项功能测试 |
| 人工审核 | 待人工审核 |
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

## 七、代码审核与权限边界

- 代码使用 Git 进行版本管理。
- 测试结果保存在报告目录。
- 使用 SHA256 记录代码完整性。
- 质量门禁失败时不应进入发布流程。
- 当前审核状态：待人工审核。
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
