# DeepTalk Studio 交接

当前版本：V0.4.1 / `0.4.1`
本轮状态：已完成，等待 ChatGPT 产品与架构复核
GitHub 仓库：https://github.com/HWang0310/deep-talk-studio
正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.4.1

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.4.0 的 Conditional Pass，只完成 **V0.4.1 Script Gate
Hardening**：

1. 让 Script Review 的 check → issue → gate 关系失败关闭；
2. 让 `reviewed` Script 可以重新证明它来自真实、通过的 Review；
3. 让 Script revision 中的 Beat identity 和版本比较稳定。

没有启动 Material Search、Visual Assistance、图片、视频、Remotion、HyperFrames、剪辑、字幕、标题、封面或发布。

## 2. 我完成了什么

- 建立版本化的、确定性 Review mapping。15 项 checks 每一项若为 `fail`，都必须有对应 typed issue；八项事实安全 checks 还必须有对应 blocking issue。`factual_grounding=fail` 且 `issues=[]` 会直接拒绝 Review Artifact，不能再误生成为 `reviewed`。
- 收紧 `not_applicable`：事实安全 checks 完全不可跳过；仅 `counterargument_fairness` 可在确实没有可审反方时使用，并保留理由。
- 增加机器拥有的 `review_state`、Review Artifact `reviewed_content_digest`（SHA-256）和 `review_consistency_version`。通过审查的 r2 同时绑定 Review ID、被审 r1、通过 Gate 和相同内容指纹。
- `load_script` 会自动定位同目录的匹配 Review Artifact 并复验 binding、checks、issue mapping、Gate 和内容指纹。仅把 JSON `status` 改成 `reviewed`，或伪造 review ID / revision / gate，均无法通过正式校验。
- Review 失败仍创建新的 `draft`；用户任何内容修订也自动清空旧 Review approval，回到 `draft`，必须重新审查。
- Beat identity 改为稳定、单调递增且不可复用。原 Beat 修改或移动时保留 ID；中间插入 Beat 不会重编号后续内容；删除 ID 进入退休集合，后续不会复用。比较功能因此能正确区分新增、删除、移动和真实修改。
- 更新 Writer/Reviewer prompt 与仓库 Skill，明确 Reviewer 的失败检查必须输出对应问题，而普通用户始终不需要管理 Beat ID。

## 3. 创建 / 修改了哪些重要文件

- `src/deeptalk_studio/schema.py`、`script_review.py`、`script_validation.py`：Review 一致性、linkage、内容指纹和正式 JSON 契约。
- `src/deeptalk_studio/models.py`、`script_storage.py`、`script_renderer.py`、`script_workflow.py`：携带、保存和重新验证 Review Artifact。
- `src/deeptalk_studio/script_revisions.py`：稳定 Beat identity、退休 ID 与比较连续性。
- `src/deeptalk_studio/script_prompt.py`、`.agents/skills/write-script/`：加强 Reviewer 和修订行为约束。
- `tests/test_script_review.py`、`test_script_validation.py`、`test_script_storage.py`、`test_script_revisions.py`：新增阻断、伪造、存储加载、插入/删除/移动/比较回归。
- `docs/SCRIPT_CONTRACT.md`、`docs/SCRIPT_EVALS.md`、`docs/ARCHITECTURE.md`、`docs/releases/v0.4.1.md`：正式契约、评测、架构和版本说明。
- `evaluations/v0.4.1-summary.json`：不含真实题材内容的公开评测汇总。
- `README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`CHANGELOG.md`：长期协作文档同步。
- `docs/superpowers/specs/2026-08-10-v0.4.1-script-gate-hardening-design.md`、`docs/superpowers/plans/2026-08-10-v0.4.1-script-gate-hardening.md`：本轮已批准设计和执行记录。

## 4. 当前架构是什么

```text
Approved Research Report
  → Writer（不联网）
  → Script r1 / draft
  → Independent Reviewer（不联网，15 项 check）
  → check/issue consistency validator
      → 无效输出：拒绝，不猜测成 pass
      → blocking issue：Script r2 / draft
      → passing Artifact + digest：Script r2 / reviewed + review_state
  → Editor Markdown / Teleprompter Markdown

用户内容修订
  → 稳定 Beat ID 分配（保留 / 新增 / 退休）
  → 新 Script revision / draft
  → 必须重新独立 Review
```

Research Report 继续使用 0.2，Topic Candidate Set 继续使用 0.3，Script Draft 与 Script Review Artifact 仍保持主版本 `0.4`；V0.4.1 通过新增机器字段和保守校验加固，不破坏上游接口。

## 5. 已经可以运行什么

- 只有已批准、`ready_for_script` 的 Research 才能写稿。
- Writer / Reviewer 均不联网，继续保留事实、归因、分析、高风险、avoid-claim、must-keep 和 Evidence Link 边界。
- `approve-report`、`prepare-script`、`review-script`、`revise-script`、`compare-script` 可完整运行。
- `review-script` 的通过结果能安全保存、重新加载和生成 Teleprompter；任何不匹配 Artifact 的 reviewed JSON 会失败关闭。
- 稿件修订后，版本比较不会因中间插入一个 Beat 而把后续所有段落错认成新段落。

## 6. 还不能运行什么

V0.5 尚未开始：没有 Material Search、合法素材清单、图片/视频/截图/B-roll 推荐、Visual Assistance、Remotion、HyperFrames、剪辑方案、字幕、标题、封面、发布或多平台分发。

## 7. 已知问题与兼容处理

- V0.4.0 的 `draft` JSON 可继续读取；下一次修订会建立新的 Beat identity state。
- V0.4.0 的 `reviewed` JSON 若没有 V0.4.1 Review linkage，系统不会静默信任。需要从同一 Research revision 重新执行 Script Review。这是刻意的保守处理，不是数据丢失。
- 内容指纹证明的是“稿件忠于已审 Research Artifact”，不替代现实世界随时间变化后的重新 Research / Fact Check。
- 口播时长仍是字符估算，最终录制需要真人读稿和编辑判断。

## 8. 重要技术决策

- 选择“拒绝不一致 Artifact”，而非自动把失败 check 变成 Gate fail：模型输出缺少明确 issue 时，系统不能猜测是哪一种问题或怎样修。
- 显式把 mapping 版本写入 Artifact（`0.4.1`），使 Review 的解释规则可审计。
- 使用 SHA-256 指纹绑定 Review 与 r1 内容；r2 只改变 machine-owned revision/status/linkage，不改变已审内容。
- Beat identity 用轻量 continuity hint 加唯一结构化匹配实现，不引入复杂 diff engine，也不把 ID 管理交给普通用户。
- 仍不升级 Artifact 主版本：新增字段是可选契约扩展；对旧 reviewed 采用失败关闭和重新审查，而不是假装完成迁移。

## 9. 测试与真实评测

- 完整 `unittest` suite：**165 项通过**；V0.4.0 记录的 151 项全部继续通过。
- 新增覆盖：八项关键安全 check 缺 blocking issue、编辑性失败、有/无 issue、缺失/重复 check、滥用 `not_applicable`、伪造 reviewed 状态/Review linkage、错误 revision、丢失 Artifact、内容指纹篡改、Review fail、再修订再 Review、Beat 修改/插入/删除/移动、重复/未知 origin 和版本比较。
- A Stable Tech / Business：Approved Research → r1 → 15/15 Review → linkage verified r2 `reviewed` → Teleprompter，成功。
- B Contested Public Issue：同一正式受控路径完成，15/15 Review、linkage 和 Teleprompter 均成功。
- C Blocked Input：只有 `reviewed`、没有用户确认的 Research 在 Writer 前被拒绝。
- Synthetic：`factual_grounding=fail` 加空 issues 被拒绝，未生成 reviewed Script。
- 评测未调用用户 API Key 或外部搜索；完整受控稿件与 Review Artifact 保持在 Git 忽略目录。公开仓库只提交 `evaluations/v0.4.1-summary.json`。

## 10. 哪些问题需要产品经理决定

当前没有阻塞 V0.4.1 发布的技术问题。请 ChatGPT Review：

1. 八项关键事实安全 check 与 blocking issue 的 mapping 是否符合产品风险口径；
2. legacy V0.4.0 reviewed Script “必须重新审查”的保守兼容策略是否接受；
3. Beat continuity 的轻量策略是否满足编辑体验；
4. 若通过，是否正式验收 V0.4 并授权进入 V0.5。

## 11. 建议下一阶段做什么

若通过 V0.4.1 Review，正式验收 V0.4，并进入 **V0.5 Material Search 与 Visual Assistance** 的产品设计和最小实现：仅从 `reviewed` Script 和 Research Evidence 推荐可合法使用的公开文件、截图、图片、视频片段与原创图表位置，记录来源、版权风险和画面用途。不要直接跳到自动剪辑或平台发布。

## 12. 版本发布规则

本轮正式版本为 `v0.4.1`。继续使用公有仓库 `HWang0310/deep-talk-studio`，不创建新仓库、不 force push、不重写 `main` 历史。GitHub Release 自动提供 ZIP / TAR 源码包；不发布没有实际安装价值的空 GitHub Package。

## 给用户的下一步操作

下一步：把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.4.1 Script Gate Hardening。
> GitHub 仓库是 https://github.com/HWang0310/deep-talk-studio ，
> Release 是 https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.4.1 。
>
> 请 Review Script Review check→issue→gate 一致性、
> reviewed Script 的 Review linkage、Beat identity、
> 版本比较、测试和真实评测。
>
> 如果通过，请正式验收 V0.4，并给我 V0.5 Material Search
> 与 Visual Assistance 的开发任务。不要让我自己总结。
