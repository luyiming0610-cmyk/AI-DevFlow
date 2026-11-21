# AI DevFlow｜真实 DeepSeek 研发流水线报告

- 任务：20261121-102456-2bf362
- 模型：deepseek-flash
- 模式：api
- 状态：**TESTS_PASSED_REVIEW_PENDING**
- 验收规范 SHA256：`4f7797c65f66670019c7ec19de1f33cfea1480887fac884fb5edfd9d8681e877`
- 验收测试 SHA256：`3021813e2891a22da8432a28caca4f18c4d9f976c49b4219be87b2455a596969`
- 人工审核：PENDING
- 生产部署：False

## 调用和成本

使用的 Token 根据 API 实际响应记录；无响应时不推断费用。

- planner：{'prompt_tokens': 1385, 'completion_tokens': 671, 'total_tokens': 2056}
- developer：{'prompt_tokens': 4020, 'completion_tokens': 2511, 'total_tokens': 6531}
- repair_1：{'prompt_tokens': 5983, 'completion_tokens': 2496, 'total_tokens': 8479}

## 每轮验收

### Round 0
- 源码：`round_00/candidate.py`；SHA256：`45c0cc17a227221d9e82f522564dd3af3b537c09fc5f7043c8365ae7b3af297c`
- 静态检查：False
- 功能测试：未运行，通过 0，失败 0
- 日志：`None`

### Round 1
- 源码：`round_01/candidate.py`；SHA256：`242c45fbc7cbb358d191a825092bf5458edfb6b8b1b45b4bfe4811e80afc8b5a`
- 静态检查：True
- 功能测试：PASSED，通过 15，失败 0
- 日志：`round_01/validation`

## 质量门禁

只有全部独立验收测试通过才能进入人工审核，不能自动部署。
人工审核状态一律为 PENDING，测试通过不等于代码已获批准。
