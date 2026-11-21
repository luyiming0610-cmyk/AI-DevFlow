# AI DevFlow｜真实 DeepSeek 研发流水线报告

- 任务：20261121-085152-bc4b86
- 模型：deepseek-flash
- 模式：api
- 状态：**TESTS_PASSED_REVIEW_PENDING**
- 验收规范 SHA256：`4f7797c65f66670019c7ec19de1f33cfea1480887fac884fb5edfd9d8681e877`
- 验收测试 SHA256：`3021813e2891a22da8432a28caca4f18c4d9f976c49b4219be87b2455a596969`
- 人工审核：PENDING
- 生产部署：False

## 调用和成本

使用的 Token 根据 API 实际响应记录；无响应时不推断费用。

- planner：{'prompt_tokens': 1385, 'completion_tokens': 614, 'total_tokens': 1999}
- developer：{'prompt_tokens': 3963, 'completion_tokens': 2192, 'total_tokens': 6155}
- repair_1：{'prompt_tokens': 5516, 'completion_tokens': 1977, 'total_tokens': 7493}
- repair_2：{'prompt_tokens': 5745, 'completion_tokens': 1995, 'total_tokens': 7740}

## 每轮验收

### Round 0
- 源码：`round_00/candidate.py`；SHA256：`e1d816d2ed22adb978584eedefec7c1a24438a4c11223bdc034f62a5d7be6e51`
- 静态检查：False
- 功能测试：未运行，通过 0，失败 0
- 日志：`None`

### Round 1
- 源码：`round_01/candidate.py`；SHA256：`3ff3c7728e8f1892e5d9658973c8d8761ffa2311d1747965665b161f7bd374e2`
- 静态检查：False
- 功能测试：未运行，通过 0，失败 0
- 日志：`None`

### Round 2
- 源码：`round_02/candidate.py`；SHA256：`2052d600cb9ddd0b811f42e91080703a9d2cb880f592eb7ccaa9fad47dd9e07c`
- 静态检查：True
- 功能测试：PASSED，通过 15，失败 0
- 日志：`round_02/validation`

## 质量门禁

只有全部独立验收测试通过才能进入人工审核，不能自动部署。
人工审核状态一律为 PENDING，测试通过不等于代码已获批准。
