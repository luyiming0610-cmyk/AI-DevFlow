# B11｜真实 DeepSeek 红灯→绿灯实验

- 任务：20261121-091420-597571
- 状态：**TESTS_PASSED_REVIEW_PENDING**
- 类型：人为注入缺陷的受控实验
- 原始候选 SHA256：`2052d600cb9ddd0b811f42e91080703a9d2cb880f592eb7ccaa9fad47dd9e07c`
- 正式测试 SHA256：`3021813e2891a22da8432a28caca4f18c4d9f976c49b4219be87b2455a596969`
- 人工审核：PENDING
- 生产部署：False

## 每轮验证

- baseline：静态检查=True；测试状态=PASSED；通过=15；失败=0
- red_fault：静态检查=True；测试状态=FAILED；通过=5；失败=10
- repair_01：静态检查=True；测试状态=PASSED；通过=15；失败=0

## 实际模型调用

- repair_1：{'prompt_tokens': 7151, 'completion_tokens': 1969, 'total_tokens': 9120}
