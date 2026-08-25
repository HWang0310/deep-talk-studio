# Finished Cut Review + Production Feedback Contract（V1 Candidate）

Finished Cut Review 是 Asset Pack + Edit Map 之后的只读学习环节，不是自动二剪。

```text
Asset Pack + Edit Map → 用户手工 NLE Assembly → Finished Cut
→ Finished Cut Review → Production Feedback Loop
```

## 不可违反的边界

- Finished Cut 是用户完成后的不可变输入。DeepTalk **不修改成片**、不输出第二版成片、不移动素材、不修改 A-roll、不创建 NLE 工程、不自动决定转场或发布。
- Review 只读取 Finished Cut、Clean A-roll、Actual Transcript/Alignment/Timeline、Asset Pack、Edit Map 和 lineage。Finished Cut 的实际媒体时间是实际时钟；Edit Map 只是计划时钟。
- 计划与实际不一致是正常的用户剪辑选择，不是错误。每项素材采用 `USED`、`NOT_USED` 或 `UNKNOWN`；没有充分画面证据必须保留 `UNKNOWN`，不能猜测。
- Finished Cut Review 不做审美打分、播放量/爆款预测或创作者评分。

## `finished-cut-review/1`

机器工件必须绑定 Finished Cut SHA、`edit-map/1` digest 和 `visual-asset-manifest/1` digest，并为每个 Edit Map 行记录：原计划时间/决策/素材、实际采用状态、实际开始/结束（如可确认）、时间偏移、实际呈现方式、证据和 `USER_EDIT_OBSERVATION`。

全画幅素材匹配只能在保守阈值内标记为 `USED`；PIP、crop、partial use、用户新增素材或不足以证明的情况必须是 `UNKNOWN`，除非有其他可审计证据。

## `production-feedback/1`

Production Feedback Loop 保存跨 Episode 可讨论的生产发现，至少允许：visual density、KEEP A-roll、REAL material、MG、timing、Edit Map UX、asset naming、semantic beat、fallback 和 creator override。

每条来自单一 Episode 的结论都是 `EPISODE_OBSERVATION`；它最多生成 `CANDIDATE_PRODUCT_RULE`，需要用户/产品经理明确 Review 或多个 Episode 的证据才可能成为 `ACCEPTED_PRODUCT_RULE`。本合同没有自动升级全局策略的接口。

## 本地交付

- `_DeepTalk记录/finished-cut-review-rNNNN.json`
- `_DeepTalk记录/production-feedback-rNNNN.json`
- `10_成片/《主题》第一版成片复盘.md`
- `10_成片/《主题》Asset Pack 使用复盘.md`

这些是本地 episode 工件，不提交 Git。产品代码和合同变更可进入开发分支；不创建 tag、Release 或自动进入下一期生产。
