# AI DevFlow｜研发流水线验证证据

## 一、项目与笔试要求的对应关系

本项目对应 B11《组建 AI 研发团队》笔试题，重点验证 Part A 第四章“研发工作流与质量门禁”、第五章“评估体系”和第七章“风险及权限边界”。

**MVP 业务场景：** 赛事影像上传日志分析工具。

核心流程：

需求读取 → 代码生成 → 自动测试 → 失败处理 → 回归验证 → 质量门禁 → 人工审核。

当前提供 MOCK 本地演示及单独的 DeepSeek 真实修复实验，两者的结果分别记录。

## 二、运行环境

| 项目 | 实际配置 |
|---|---|
| 操作系统 | Windows |
| Python | 3.12.0 |
| Pytest | 9.2.0 |
| 代码检查 | Ruff |
| 版本管理 | Git |
| 可视化 | Streamlit |
| 大模型 | DeepSeek |
| 本地演示 | MOCK |

## 三、运行和复现方法

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

运行本地流水线：

```powershell
python main.py
```

运行自动测试：

```powershell
python -m pytest tests -v
```

打开可视化界面：

```powershell
python -m streamlit run dashboard.py
```

以上本地流程不需要 API Key。真实模型实验需要额外配置自己的 API Key。

## 四、测试失败与修复验证

### 4.1 初次测试

初始日志分析程序未正确校验日期的有效性。

当输入 `2026-99-99` 时，程序将无效日期错误地计入有效上传记录。

实际测试结果：

| 测试用例 | 结果 |
|---|---|
| 上传成功与失败统计 | 通过 |
| 异常格式日志处理 | 通过 |
| 非法时间戳识别 | 失败 |

**首次测试：2 项通过，1 项失败。**

原始证据：`reports/before_repair_pytest.txt`

### 4.2 失败响应

系统读取真实 Pytest 失败输出，识别出日期校验缺陷。

在 MOCK 模式下，Repair 模块应用预设的确定性修复补丁，在日志解析逻辑中增加日期有效性检查。

此过程没有调用大模型，不属于真实 AI 自主修复。

### 4.3 修复后的回归测试

系统使用原有三个测试用例重新执行验证，未修改测试断言。

**回归测试：3 项通过。**

原始证据：`reports/after_repair_pytest.txt`

这一实验验证了测试失败、错误响应和修复后回归验证的流程可复现。

## 五、质量门禁

| 检查项目 | 验证结果 |
|---|---|
| Python 语法检查 | 通过 |
| 基础安全规则扫描 | 通过 |
| Ruff 静态代码检查 | 通过 |
| Pytest 自动化回归测试 | 通过 |

机器可读记录：`reports/quality_gate.json`

上述扫描不等同于完整安全审计或安全沙箱，不能据此证明代码不存在所有安全问题。

## 六、真实 DeepSeek API 修复实验

本项目另外执行了一次真实大模型修复实验。

实验输入包括初始 Python 代码和真实 Pytest 失败日志。

| 项目 | 实际记录 |
|---|---|
| 模型 | deepseek-flash |
| 输入 Token | 667 |
| 输出 Token | 281 |
| 总 Token | 948 |
| 调用状态 | 成功生成修复候选 |
| Python 语法检查 | 通过 |
| Ruff 静态检查 | 通过 |
| 功能回归测试 | 尚未验证 |
| 人工审核 | 待审核 |

真实模型生成的候选代码添加了 `datetime.strptime` 日期校验逻辑。

候选代码保存在本地独立实验目录，未覆盖已经通过 MOCK 测试的正式示例代码。

目前不能将“候选生成成功”认定为“完整修复成功”。模型调用费用应以实际 API 账单为准，不根据 Token 数量自行编造金额。

## 七、人工审核与权限边界

质量门禁通过后，系统生成 `review_request.json`，其初始审核状态为 `PENDING`。

审核请求包含代码 SHA256、质量检查结果和人工审核清单。

当前流程不会自动合并未经审批的代码，也不会自动部署到生产环境。

## 八、Git 版本管理

已验证的本地提交记录：

| 提交标识 | 内容 |
|---|---|
| `57abd55` | Agent 流水线与质量门禁 |
| `0f7ac1c` | CI 配置 |
| `c457157` | 七章团队方案 |
| `8835eb7` | 研发验证证据初稿 |

GitHub Actions 已编写配置，但尚不能宣称线上运行成功，需在代码上传后以实际 CI 执行结果为准。

## 九、项目局限及后续改进

- MOCK 模式使用预设开发和修复逻辑，不支持任意需求的自主研发。
- 真实模型修复候选仍需功能回归验证。
- 尚未完成生产级安全隔离环境。
- 人工审核不能由 Agent 自动代替。
- 本 MVP 未实际部署至生产环境。
- 6 周缩短到 2 周是 Part A 的企业实施目标，不是当前 MVP 已经实现的效率提升结果。

## 十、参考资料

- Python 官方文档：https://docs.python.org/3/
- Pytest 官方文档：https://docs.pytest.org/
- Ruff 官方文档：https://docs.astral.sh/ruff/
- Git 官方文档：https://git-scm.com/docs
- GitHub Actions：https://docs.github.com/actions
- DeepSeek API：https://api-docs.deepseek.com/
- Streamlit：https://docs.streamlit.io/

以上证据以实际代码、测试输出和运行记录为依据。最终提交前应补充新增的验证结果，并检查引用清单与实际使用资料一致。
