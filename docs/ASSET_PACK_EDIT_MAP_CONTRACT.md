# Asset Pack + Edit Map Contract（V1 Candidate）

DeepTalk Studio 的正式后半段交付是 **Production Asset Pack + Edit Map**，不是替用户剪出的最终视频。

```text
Final Clean A-roll → local ASR → global monotonic alignment → semantic timeline
→ Visual Director → individual asset QA → Asset Pack + Edit Map → 用户在剪映手工剪辑
```

## 不可违反的产品边界

- DeepTalk 不选择用户的 take，不删除停顿、重录或废段，不裁剪、拼接或改写 A-roll，不决定剪映时间线，也不发布。
- 用户先自行导出稳定的 Final Clean A-roll。若能明确识别出完整重录或多个完整 take，系统仅拒绝并要求人工清理后重新提供；绝不提供 cut list 或保留建议。
- 真实时间只能来自 Final Clean A-roll → Timed Transcript → approved global monotonic Alignment。禁止 Script 估时、草稿估时或 fixture duration 进入正式素材或 Edit Map。
- Reviewed Script/approved Research 是事实真相；Actual Transcript 是时间真相。数字、日期、人名、组织、作品、政策或明确因果出现 `FACT_CONFLICT` 时，记录真实时间、保留音频，并阻止错误 display asset。

## Visual Director 与素材

每个真实语义 span 只允许 `KEEP_A_ROLL`、`REAL_MATERIAL`、`MG_MOTION`、`ADVANCED_MOTION`。默认是 `KEEP_A_ROLL`；没有明确证据、解释、认知或记忆价值时不覆盖人物。

- `REAL_MATERIAL` 必须有 provenance、准确事实 binding 和通过 QA 的实际文件。
- `MG_MOTION` 使用现有 shared primitives；其 semantic beats 与内部 relative timing 都从真实 span 重新计算，不能把固定动画拉伸到新时长。
- `ADVANCED_MOTION` 仅在自然适配时提出，且必须单独 Review。普通安全 KEEP/REAL/MG 不逐条请求用户审批。
- 非 KEEP 资产生成/QA 失败时，按 `ADVANCED → MG → REAL → KEEP_A_ROLL` 降级；Edit Map 不得留下不存在或未 READY 的素材。

## 交付物

Episode 本地目录中：

- `05_A-roll/`：Actual Transcript、Alignment Review、真实时间轴；
- `06_真实素材/`、`07_MG动画/`、`08_高级动画/`：已通过 QA 的可见素材；
- `09_剪辑表/`：给创作者阅读的 Markdown + CSV；
- `_DeepTalk记录/`：Asset Manifest、machine `edit-map/1.json`、QA/provenance/binding。

Edit Map 每行都含实际 A-roll start/end、口播摘要、决策、素材文件名（如有）、剪映放置方式、出现原因、来源/provenance、QA 与 fallback 结果。`KEEP_A_ROLL` 也是合法且完整的一行。普通用户只需打开剪映，按照该表拖放素材；不要求理解 JSON、renderer 或工程参数。

历史 Remotion/HyperFrames full-preview 与 Edit Bridge 仍保留为兼容、单素材渲染、预览和 QA 能力，不是默认用户主路径，也不代表最终成片。

## Audio-only（纯口播音轨）分支（Issue #30）

- 当唯一媒体是已定稿的 WAV/MP3 口播时，视觉决策使用 `AUDIO_ONLY` 而不是 `KEEP_A_ROLL`：没有真人画面可保留，行为必须诚实标记"需人工补画面"，且该行**不计为 QA-ready 素材**（`qa_status=not_applicable`、无素材文件、`requires_human_review=True`），不进 asset manifest。
- 素材映射为确定性投影：一个语义 span 只能对应一个 cue；有多个候选、多个 cue 或未选片段的视频参考时按 `VISUAL_GAP` 处理，绝不自动挑选。
- 素材入包前必须通过 canonical Rights/Reuse 核验：只有 validated `rights_status` 属于 `SAFE_REUSE_STATUSES`、provenance 为 inspected、eligibility 为 ready_to_use、且文件/SHA 校验通过的本地素材才能成为 `REAL_MATERIAL` 行并带真实 provenance；`production_status=ready` 仅证明文件完整性。unknown / permission_required / reference-only 等没有可核验复用依据的素材一律转 `AUDIO_ONLY`（说明原因），不得标 `qa_status=pass`，不进 asset manifest。
- 交付工件（`剪辑表.md/.csv`、`edit-map.json`、`visual-asset-manifest.json`）的 `map_digest` / `manifest_digest` 与交叉绑定可被独立重算校验；素材 `local_path` 必须位于当前 Episode 内且与已验收候选一致，篡改 fail-closed。
- 剪辑表前言按媒体类型区分（`build_production_asset_pack` 的 `media_kind`，fail-closed）：真人 MP4 文案保持原状；纯音频交付的前言必须说明本次交付没有真人画面——有素材的段落照表使用、标记「需人工补画面」的段落需人工补入——绝不使用「保持人物画面」类表述。
- 真人 MP4 的 `KEEP_A_ROLL` 语义、fallback 链与视觉文案保持原状。
