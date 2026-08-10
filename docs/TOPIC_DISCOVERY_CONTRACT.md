# Topic Discovery Artifact Contract 0.3

## 目的

`Topic Candidate Set 0.3` 是 Research Report 0.2 的上游选题工件。它回答“这个题是否值得继续研究”，不回答“事实已经确认”。其可执行 Schema 位于 `src/deeptalk_studio/schema.py`，完整业务校验位于 `src/deeptalk_studio/discovery_validation.py`。

## Channel Profile

默认 Profile 位于 `config/channel-profile.json`，当前版本为 `0.3`。它描述 B 站真人深度口播的频道定位、允许领域和避免内容。V0.3 用户不需要编辑它；后续版本可以增加自然语言配置层，但不得改变已经保存 Candidate Set 使用的 profile version。

## Raw Candidate 与机器字段

搜索步骤只可提交 Raw Candidate：标题、分类、摘要、why now、核心张力、研究问题、事件开始/最新进展时间、时效、风险、事件聚类键、Preflight 信号、五项 0–5 分及理由、Source Seeds、警告和可选 Creator signal。

程序独占 `discovery_id`、生成时间、candidate ID、Source Seed provenance、资格结论与理由、推荐标签、首选标记、展示顺序、watch/reject 统计和 `total_score`。Raw Candidate 中出现这些字段会被 Schema 拒绝。新生成的 Candidate Set 会保存规范化 `seed_provenance` 上下文，读取时核心从 Raw 内容、该 provenance、生成时间与固定规则重新推导全部上述字段；任一不一致即拒绝工件。固定总分公式为：

```text
researchability × 30% + depth_conflict × 25% + freshness × 20%
+ channel_fit × 15% + attention_signal × 10%
```

每项原始分范围为 0–5，总分为代码计算的 0–100 整数；每项必须附可读理由。

## 时间、资料与风险 Gate

- Raw Candidate 至少为 7 项；少于 7 项时本次 Discovery 明确失败或继续搜索，最终合格候选仍可以少于 5 项。
- 默认窗口为最近 72 小时；也接受在最近 14 天内开始、且最近 72 小时有重要更新的持续事件。开始时间不得晚于更新，任何事件时间不得比 `generated_at` 晚超过 5 分钟。
- 推荐/备选题至少需要两个不同、可继续研究的方向：只计入 provenance 为 `matched` 或真实 `manual_open` 且来源类型为官方、原始、可靠媒体、学术或专家的 Seed。先规范化 URL；相同 URL、同 publisher 或同 host 保守地只算一个方向。
- API 模式的 Seed 必须能与真实 Web Search action source 或 citation 对上；Codex 模式仅在实际打开页面并出现在后台 inspection manifest 后标为 `manual_open`。Raw Candidate JSON 本身不能自认证页面已打开。
- 只有匿名传言、无公开资料、未经证实的严重指控、纯情绪或模仿他人表达的候选为 `rejected`。
- 重大快速事件或高风险事件在资料不足时为 `watch`；`watch` 和 `rejected` 永不进入 Top 5。
- 相同 `event_cluster_key` 最多展示一次。第一轮优先每类最多两项以保持多样性；未满时第二轮按机器总分和稳定名称补位，可让单一分类超过两项。

## Source Seeds 与 Creator Signal

每条 Seed 只记录 URL、发布者、发布时间、来源类型、用途和 provenance 状态。它是下一阶段的检索入口，不是 Evidence Ledger，不能被渲染为 confirmed fact。Codex manifest 条目含实际打开 URL、可获得时的 tool/open reference 与检查时间；它由 Skill 后台管理，普通用户无需创建或理解它。

Creator attention signal 可以为空；如有，只能来自无需绕过限制即可访问的公开标题、简介或页面元数据。它是可选关注信号，不得作为事实来源、不得伪造播放/热度数字，也不得保存或模仿稿件、字幕和独特表达。

## 选择和 Research Handoff

每次发现保存独立 JSON / Markdown 到 `discoveries/YYYY/MM/DD/`，不覆盖历史。`discoveries/latest.json` 只保存最新指针。用户回复 `1` 或 `研究 1` 时，程序从 `display_candidate_ids` 取出候选，生成 `Research Handoff Brief 0.3`：标题、研究问题、核心张力、why now、风险、警告和 Seeds。

Handoff 是模式 B 到 V0.2 Research Workflow 的正式 JSON 接口。它不解析 Markdown，也不要求用户复制标题；Research Agent 必须重新搜索、建立 Evidence Ledger 并执行独立 Fact Check。模式 A 的直接主题输入不经过该工件。
