# V0.2 真实编辑评测方法

## 目的

V0.2 不用“格式合法”代替“研究可靠”。每个正式版本至少用三类真实公开事件走完：

1. 低冲突的科技或商业信息；
2. 有明确立场冲突的公共议题；
3. 快速变化、容易过期的突发热点。

每个样本必须依次完成 Research Draft、独立新检索、FactCheck Artifact、修订版报告和质量 Gate。完整报告保存在本机 `reports/`，受 `.gitignore` 保护；仓库只提交方法和去内容化汇总，避免长期保存大篇新闻底稿或受版权保护原文。

## 编辑评分表

每项使用 1–5 分：

- `factual_accuracy`：核心事实是否与打开的来源一致。
- `attribution_quality`：当事方说法和评论是否明确归属。
- `source_independence`：是否识别同源、转载和非独立来源。
- `perspective_coverage`：是否覆盖与主题相关的主要不同立场。
- `uncertainty_handling`：是否暴露时效、未知和证据限制。
- `classification_quality`：事实、报道、当事方说法、评论和未证实信息是否分开。
- `material_omissions`：是否缺少会改变结论的重要信息。
- `angle_value`：切入角度是否来自证据冲突而非拼贴他人表达。
- `script_handoff_usability`：未来 Script Agent 能否看懂必须保留和禁止外推的边界。

评分是编辑诊断，不参与机器 Gate，也不能覆盖机器 Gate 的失败。某个高风险主张未解决时，即使平均分较高，报告仍必须停在 `draft`。

## V0.2 执行记录

执行日期：2026-08-10。

- 稳定商业信息样本：质量 Gate 通过，状态为 `reviewed`。
- 争议公共政策样本：质量 Gate 通过，状态为 `reviewed`；二次核查补充了有限过渡期这一边界。
- 快速突发事件样本：质量 Gate 按预期失败，状态保持 `draft`；原因是关键动态数字没有取得可稳定复查的第二个独立官方依据。

三份样本均保留来源、Evidence Link、独立 FactCheck provenance 和不可覆盖的 r1/r2 修订历史。没有一份自动进入 `ready_for_script`，因为未来进入写稿步骤前仍需用户明确确认。

去内容化的详细分数和 Gate 指标见 `evaluations/v0.2-summary.json`。

## 复测规则

- 修改 Schema、Fact Check、来源去重、质量 Gate 或渲染器后，重新运行三类样本。
- 突发事件样本允许并鼓励出现 `fail`；只要失败原因透明并正确拦截，就属于有效验收。
- 不为了提高得分降低风险级别、改写事实分类或删除不利证据。
- 不把编辑评分包装成客观真相，评分者应留下简短说明。
