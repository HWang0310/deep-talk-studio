# V0.4 Original Script Agent 真实评测

评测日期：2026-08-10。完整真实 Research 与 Script artifacts 保存在被 Git 忽略的 `reports/evaluations/v0.4.0-approved/` 和 `script_drafts/evaluations/v0.4.0/`；公开仓库只提交去内容化汇总 `evaluations/v0.4.0-summary.json`。

## 方法

三类输入使用同一正式代码路径，不为评测改状态或绕过 Gate：

1. Stable Tech / Business：已完成 Research、Fact Check、Quality Gate 和用户 Approval Revision 的稳定商业报告。
2. Contested Public Issue：同样通过 Gate 并批准，且同时包含法律事实、产业立场和公共利益评论的争议公共议题。
3. Blocked Input：质量 Gate 已通过但只有 `reviewed`、没有用户 Approval 的报告。

A / B 均执行：Approval Revision → Writer → Script Draft r1 → 独立 15 项 Script Review → Script r2 → 实际阅读全文 Teleprompter。C 直接尝试写稿并核查退出状态和文件数。

## 机器结果

| 场景 | Approval | must-keep | Grounding Gate | Review | 输出 |
|---|---:|---:|---:|---:|---|
| Stable Tech / Business | 新建 r3 | 2 / 2 | pass | 15 / 15，0 blocking | r2 `reviewed`，1273 字符，约 4.9 分钟 |
| Contested Public Issue | 新建 r3 | 3 / 3 | pass | 15 / 15，0 blocking | r2 `reviewed`，1520 字符，约 5.8 分钟 |
| Blocked Input | 无 | 不适用 | fail closed | 不运行 | 退出码 2，0 文件 |

两份 Teleprompter 均未出现 URL、Claim / Evidence ID 或编辑标签；Editor 版本保留了逐 Beat 证据引用、风险、研究缺口和覆盖信息。

本次使用 5 分钟和 6 分钟目标，是因为两份既有真实 Research Report 分别只有 2 和 3 项可用主张。若强行填充到默认 12 分钟，会增加重复或诱导模型补写研究外事实。V0.4 仍保留默认 12 分钟，并已用自动测试覆盖时长解析与机器计算；真实稿件优先遵守证据密度。

## 人工 Editorial Review（1–5 分）

分数不会覆盖机器 Grounding Gate，也没有为了让结果更好而自动修改。

| 维度 | Stable | Contested | 说明 |
|---|---:|---:|---|
| factual_grounding | 5 | 5 | 事实段只使用已核查 Claim |
| attribution_integrity | 5 | 5 | 公司、行业和研究机构说法都有自然归因 |
| uncertainty_preservation | 5 | 5 | 后续表现、指南和执行实践均保留未知 |
| narrative_structure | 4 | 4 | 推进清楚；有限研究材料限制了故事层次 |
| oral_naturalness | 4 | 4 | 可直接口播，少数句子仍可由真人再断句 |
| information_density | 4 | 4 | 密度合适，没有为拉长时长重复事实 |
| insight_value | 4 | 4 | 提供可复用判断框架，但不假装拥有底稿外洞察 |
| counterargument_fairness | 4 | 5 | 两边均公平；争议题主动拆除了稻草人表达 |
| original_expression | 5 | 5 | 重新组织研究，没有长段引用或模仿来源 |
| script_usability | 4 | 4 | 可进入真人编辑；仍需最终语气和个人经验调整 |
| **平均** | **4.4** | **4.5** | 机器 Gate 均为 pass |

## 实际阅读结论

- Stable 稿件不是财报摘要，而是围绕“真实增长与一次性贡献可以同时成立”推进；口语自然度合格，没有把公司归因写成审计事实。
- Contested 稿件把法律要求、产业可执行性观点和公共利益局限性分开，避免把任一方塑造成反透明或迷信标签。
- 两份稿件都没有 AI 报告式引用语法；篇幅受 Research Claim 数量限制，但这比用未经研究的新信息填满 12 分钟更可靠。
- Blocked Input 证明用户确认是真正的写稿 Gate，而不是文档承诺。

## 已知限制

- 字符时长是可解释估算，真人语速、停顿和临场发挥会改变最终时长。
- `avoid_claims` 的直接文本使用可硬阻止；语义近似仍依赖独立 Reviewer 判断。
- 工程 Grounding 能证明稿件忠于 Research Artifact，不能替代对现实世界的新一轮事实判断。
- `reviewed` 表示可进入人工编辑，不表示自动获准录制或发布。
