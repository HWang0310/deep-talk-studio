---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'f6024d66-23c5-4a9f-bbab-37a669b911a8'
  PropagateID: 'f6024d66-23c5-4a9f-bbab-37a669b911a8'
  ReservedCode1: '00482778-51c0-498b-a40d-b9cd7aafa516'
  ReservedCode2: '00482778-51c0-498b-a40d-b9cd7aafa516'
---

# Changelog

## Unreleased — 2026-09-01 — Core Phase 3A-2 real MG integration — AWAITING_CHATGPT_REVIEW

- CORRECTION-1: Core now performs lexical `lstat` checks before path resolution and rejects a symlink output root, any existing symlink ancestor below that root, and a symlink artifact even when its resolved target remains inside the output root. Traversal, containment, existence, SHA-256, and duration checks are unchanged.
- Connected the existing Contract V1 subprocess adapter and Candidate Portfolio orchestration to MG `org.deeptalk.mg` version `1.0.0-contract-v1`, exact-pinned at `7ae59f1115da8a011113c81f31d320783b0ce8a4`, through `node scripts/contract-runner.js` and request/result/artifact files only.
- Added fail-closed plugin-root, full-HEAD, clean-worktree, reported-version, response identity, Contract version, canonical argv, environment/config digest, request/result identity, and task evidence. No revision bypass remains for synthetic runners.
- Added deterministic timeout evidence and controlled regressions proving SIGTERM escalation to SIGKILL both when the direct child ignores termination and when a wrapper exits while a same-group descendant survives; Core reaps its direct child, verifies group termination, and emits no raw result or Candidate. Runner launch `OSError` failures are isolated fail-closed.
- Kept `visual-asset-plugin-config/1` and historical execution evidence readable while requiring enabled pinned entries and all newly completed evidence to bind version, exact revision, resolved argv, request/result identity, and identical proposal/generation-to-audit execution copies.
- Proved one synthetic causal opportunity through real MG suitability (`SUITABLE`), policy-requested generation, READY/PASSED primary media, Core SHA/ffprobe/artifact-boundary acceptance, and immutable portfolio reload. The MG entry uses a 180-second budget because measured local generation completed in about 125 seconds; the previous 120-second placeholder failed closed before normal completion.
- Status is **IMPLEMENTED_UNRELEASED / AWAITING_CHATGPT_REVIEW**, not ACCEPTED or RELEASED. No MG source, Illustrated, Hand-drawn, real Episode, Candidate Pack, Edit Map, V1 writer, `main`, tag, or Release was modified.

## Unreleased — 2026-08-30 — Relocation-safe Core artifact semantics — ACCEPTED / IMPLEMENTED_UNRELEASED

- Added a strict machine-local runtime resolver for digest-covered Motion Manifest, reviewed Material Package, and Material Capture paths after a canonical workspace move. Historical artifacts and digests remain unchanged; only separately verified runtime observations use the new canonical location.
- Core now rejects unknown roots, arbitrary prefix replacement, traversal, identity mismatch, symlink escape, missing/non-file targets, byte-size/SHA mismatch, and outer-manifest tampering across Motion validation, Material replay, Edit Bridge QA, production planning, and renderer staging.
- `align-video` may select an exact configured current Production and no longer uses filesystem mtime. Its compatibility fallback uses artifact-owned time/revision/identity fields; a formal immutable current-production index remains deferred.
- Machine-specific canonical repository root belongs to gitignored local config; the architecture remains portable. No user-specific absolute paths are committed as product invariants.
- **ChatGPT independently reviewed and accepted the implementation** at SHA `e4dbbd089d6253cf053e55f0b2a1ae1c38a58bc1` on branch `agent/relocation-safe-artifact-resolution`. The accepted implementation was fast-forwarded to canonical branch `agent/multi-asset-studio` without merge commit, rebase, or force push. This acceptance commit is docs-only; no implementation source code was modified during acceptance.
- This is ACCEPTED / IMPLEMENTED_UNRELEASED — not RELEASED. No historical JSON, private Episode fixture, visual plugin, `main`, tag, or Release was changed. Phase 3A remains IN PROGRESS: the first MG Contract V1 runner has an implementation on its plugin review branch but is NOT yet accepted/pinned. Core real-plugin Phase 3A-2 integration has NOT started.

## Unreleased — 2026-08-29 — Multi-Asset Phase 2 portfolio Core QA

- Review correction: completed real fake-subprocess multi-plugin orchestration, runtime-version and bounded execution evidence, declarative policy loading, canonical `opportunities[]` portfolio/audit shape, verified Reviewed Script directive binding, and Core-owned request factual lineage.

- ChatGPT formally accepted Phase 2 as ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation. It remains fake-only and synthetic; Phase 3A is the separate next gate for one independently reviewed and pinned real-plugin runner plus one synthetic Core integration.

- Added production-safe `visual-opportunity-directives/1` authoring from verified synthetic timeline, reviewed-script digest, and approved factual bindings; only clock-free `visual_intent` / `why_visual` semantics cross the authoring boundary.
- Added deterministic no-quota LEAN/STANDARD/RICH generation policy, fake-only multi-plugin `candidate-portfolio/1` histories, no-call evidence, audit records, and raw READY plus separate Core acceptance projection.
- Added Core-owned local-runner artifact resolution, SHA-256, ffprobe duration, placement, lineage, provenance, duplicate-ID, and generated-as-real rejection checks, plus structural fail-closed reload validation for portfolios and opportunity plans.
- This is sanitized synthetic fake-runner implementation only. It does not integrate a real plugin, create a Candidate Asset Pack or `candidate-edit-map/1`, alter V1 writers, migrate production schemas, or release a product version.

## Unreleased — 2026-08-28 — Multi-Asset Phase 0 contract baseline

- Multi-Asset Phase 1 review-branch implementation: added clock-free directives, Visual Opportunity artifacts and storage, fake-only subprocess configuration/protocol, and the minimal raw-plugin/Core-acceptance Candidate Portfolio slice. No real plugin, Episode, Candidate Pack, release, or V1 writer change is included.
- Phase 1 review correction: verified canonical Semantic Timeline lineage, made raw Contract cross-stage evidence and Core acceptance explicit, preserved adapter execution locators in portfolios, and made storage reload checks recompute artifact digests.
- ChatGPT formally accepted Phase 1 as ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation. Phase 2 remains a separate future gate; no real-plugin integration or release is implied.

- Added strict `visual-asset-plugin-contract/1` request/response validators with frozen enum, identifier, failure-envelope, artifact, raw candidate-status, READY/QA_REJECTED, duration, and real A-roll placement invariants.
- Added a sanitized synthetic Contract V1 corpus, a clock-free `visual-opportunity-directives/1` fixture, a deterministic test-only fake fixture emitter, and disabled placeholder plugin/policy configuration examples.
- Phase 0 review correction: removed the non-contract artifact uniqueness restriction. `QA_REJECTED` candidates still do not require READY delivery fields, but now validate duration, suggested placement, artifacts, and provenance structurally whenever those optional fields are present.
- Preserved all V1 writers/readers: no Visual Opportunity runtime, subprocess adapter, Candidate Portfolio, Candidate Pack, real plugin invocation, Episode work, merge, tag, Release, or `main` change is included. ChatGPT formally accepted Phase 0 as ACCEPTED / IMPLEMENTED_UNRELEASED; the next gate is Phase 1's Visual Opportunity + fake subprocess vertical slice.

## Unreleased — 2026-08-28 — Accepted Multi-Asset Implementation Plan

- Added and formally accepted an implementation-only plan for the accepted Visual Asset Plugin Contract V1. It records the inspected Core and three-plugin runtime baseline, a local subprocess plus Core-owned request/result-file protocol, static local plugin configuration, Core-side acceptance/lineage QA, opaque local artifact locators, deterministic LEAN/STANDARD/RICH policy, non-exclusive portfolios, Candidate Asset Pack, and `candidate-edit-map/1`.
- Sequenced additive contract fixtures, fake-runner vertical slice, Core portfolio/QA, separately pinned real plugin runners, creator pack/map, three-plugin synthetic integration, and a distinct real-episode gate. It preserves V1 readers/artifacts and defers REAL retrieval, automatic editing, registry/cloud work, and a new Finished Cut Review contract.
- Clarified that Phase 0 — Contract fixtures + frozen V1 compatibility baseline — is the next gate and requires a separate implementation session, branch, and review. This documentation-only acceptance does not start Phase 0 or implement a schema, runtime, adapter, portfolio, plugin runner, episode output, tag, Release, merge, or `main` change.

## Unreleased — 2026-08-28 — Visual Asset Plugin Contract V1 design

- Recorded the accepted multi-repo, plugin-first Visual Asset Ecosystem principle in canonical product and architecture documents.
- Added an evidence-derived Contract V1 design from read-only MG, Illustrated Metaphor, and Hand-drawn Common Brief trials: two-stage suitability/generation, normal ABSTAIN, eligible BORDERLINE, non-exclusive candidates, role-based artifacts, separate operation/candidate state, independent versioning, and opaque plugin metadata.
- Clarified Contract V1 lineage and boundaries after Architecture Review: per-call request IDs, stable opportunity/proposal/candidate IDs, Generation Result proposal linkage, bounded placement, opaque artifact URI locators, and operation states separate from candidate asset states.
- ChatGPT Architecture Review formally accepted Contract V1 as ACCEPTED_UNRELEASED architecture. The next gate is Multi-Asset Implementation Planning; no runtime implementation, schema adoption, tag, Release, or `main` change has begun.
- Kept `REAL_MATERIAL` outside generated-plugin V1 pending a dedicated evidence/retrieval adapter design. No production code, registry, runtime integration, migration, tag, release, or `main` change was made.

## Unreleased — 2026-08-27 — Project Memory Consolidation

- Added `PROJECT_STATE.md` as the concise canonical current-state owner and `docs/INDEX.md` as the documentation reading map.
- Reclassified the accepted Multi-Asset Studio Product Review outcome as accepted/unreleased with implementation not started; no production contract, schema, or code changed.
- Reconciled README, PRD, ROADMAP, ARCHITECTURE, AGENTS, and historical entry points so `v0.6.1` remains the latest formal release and V1 Candidate remains unreleased.
- Preserved plans, specs, release notes, evaluations, and the chronological HANDOFF log. They remain historical evidence rather than competing current-state sources.

## Unreleased — 2026-08-27 — Multi-Asset Studio research

- Added Product / Technical Reconnaissance for Multi-Asset Studio repositioning. Its research/proposal material remains preserved; the 2026-08-27 Product Review subsequently accepted the core direction, while implementation has not started.

## Unreleased — 2026-08-25 — Finished Cut Review + Production Feedback Loop

- 新增 `finished-cut-review/1` 与 `production-feedback/1`：在用户手工完成 NLE 成片后，只读比较 Edit Map、Asset Manifest 与 Finished Cut 的实际素材使用；计划偏差记录为 `USER_EDIT_OBSERVATION`，不是剪辑错误。
- 新增保守的媒体探测与全画幅素材匹配。无法以可区分画面安全确认的素材一律保持 `UNKNOWN`；不会因为相同深色背景或相近静帧而误报已采用。
- 新增本地 JSON/Markdown 复盘写入器，只会写入 episode 的 `_DeepTalk记录/` 与 `10_成片/`，绝不生成视频、NLE 工程或自动二剪。
- 单期复盘只能生成需要人工或多期验证的 `CANDIDATE_PRODUCT_RULE`，没有自动升级为全局策略、创作者评分或爆款预测的接口。
- 以《牛来》用户手工完成的第一版成片完成真实只读验证；本期媒体和复盘工件保持 Git 外本地保存，未创建 tag、Release，未改动 `main` 或 `v0.6.1`。

## Unreleased — 2026-08-25 — Asset Pack + Edit Map production boundary

- 将 V1 Candidate 的默认后半段交付正式改为 `Final Clean A-roll → Semantic Timeline → QA-ready Asset Pack + Edit Map → 用户手工 NLE 剪辑`；历史全片 Remotion Preview 保留为兼容、预览和 QA，不再是默认产品成功标准。
- 新增 immutable Clean A-roll Gate、真实语义时间轴、`FACT_CONFLICT` display blocker、actual-span-only Motion timing、Asset Pack workflow 与 machine `edit-map/1`。系统不选择 take、不自动删停顿/重录/废段、不裁剪或拼接 A-roll、不生成 NLE 工程或最终成片。
- 普通 `KEEP_A_ROLL`、`REAL_MATERIAL`、`MG_MOTION` 决策不再需要逐条人工批准；`ADVANCED_MOTION` 继续要求独立 Review。未 READY 素材按 `ADVANCED → MG → REAL → KEEP_A_ROLL` 安全降级，禁止 broken Edit Map。
- 增加 22 项定向 regression，覆盖无真实对齐拒绝、真实时间映射、KEEP、非 KEEP 的 READY/SHA 绑定、失败回退、无默认 final video/NLE project、事实冲突阻断、MG real-span timing、无自动 take 选择/剪辑和 Advanced Review。
- 已用《牛来》的最终真人 Clean A-roll 完成一次真实验证：本地 `whisper.cpp large-v3` 转写、25/25 Script Beat 的真实时间对齐、Semantic Timeline、Visual Director、3 条 QA-ready MG 动画、Asset Manifest 和 25 行 Edit Map 均通过。交付是可直接导入剪映的 A-roll + 素材包 + 剪辑表，不是自动生成的完整成片或 NLE 工程；episode 私有素材始终未进入 Git。

## [Unreleased] - 2026-08-24

### Local real-episode Script V1 acceptance run

- Ran one user-owned real episode through the already-implemented Content Director + Script Agent V1 path using its explicitly approved local Markdown fact pool and SHA source-lock. Its first draft was held for four content-quality failures, then revised once and passed the evidence, counterevidence, duration, originality and 17-item quality review.
- No episode thesis, research, draft, reviewed script, source text, media, hash or private creative artifact was added to Git. No product code, main branch, tag or Release changed in this run.

### Local real-episode Creator Polish

- Performed one permitted Creator Polish revision on the same user-owned real episode. The pass retained all evidence and thesis constraints, reduced repeated explanation and article-like phrasing, strengthened the second hook and Creator Listen Test, and produced a final reviewed local script.
- No product code or episode creative content was committed. The final real-episode boundary remains: user reads the script and decides whether to record; no A-roll or visual stage begins.

### Content Director + Script Agent V1

- Added Content Thesis Card 1, controlled Thesis Review Artifact, immutable local storage and ordinary-language review pages. A Thesis Card is bound to exact approved Research content, verified confirmed facts and counterevidence; a passing machine review still cannot start writing until an explicit human confirmation is recorded.
- Added Script Profile 1 and Script Draft/Review compatibility for V1 while preserving the 0.4 path. V1 requires an approved Thesis binding and enforces an actual 5–6 minute spoken-duration range.
- Added 17 blocking Script Quality Gate checks on top of the legacy fact-safety review, including hook, conflict, cognitive turns, propulsion, re-hooks, counterevidence, audience value, audio-only interest, originality and a non-summary ending. A failed audio-only check cannot become advisory.
- Added no-search Writer/Reviewer prompt boundaries: competitive references can inform high-level content mechanisms only and cannot supply facts or expressions.
- Added real 《牛来》 Content Thesis Card, human-readable Thesis Review and source-lock manifest outside Git. The thesis passes the preparation review but is deliberately **pending human confirmation**; no final Script, A-roll or visual work was generated.

### Visual Asset Engine Chinese Display Text renderer hardening

- Replaced the Visual Asset Engine's no-text ffmpeg fallback with the repository's installed Remotion/Chrome browser route. A visual asset is now ready only when its browser-rendered MP4 and deterministic PNG text reference frame both exist.
- Added one binding-preserving, bounded Chinese text primitive with title, heading/node, body and pure-numeric emphasis roles. It uses an available macOS Chinese system font, retains the exact approved text, wraps only within explicit capacity, and fails rather than paraphrasing, clipping or silently shrinking unsafe text.
- Regenerated the five synthetic grammar fixtures plus a Chinese stress fixture covering Chinese labels, punctuation, dates, numbers and `B站 / AI`; added evidence sidecars that bind the visible text, reference frame, source range and Motion Spec digest.
- Added regressions for Chinese layout preservation, overflow failure, safe-area placement and final render evidence. No real episode, reviewed Script, approved Research, reviewed Material Package, main branch, tag or Release was changed.

### Visual Asset Engine MVP foundation

- Added alignment-bound `visual-director-plan/1` decisions with `KEEP_A_ROLL` as the default and explicit MG/Advanced review requirements; proposal-supplied A-roll clocks are rejected.
- Added binding-first `motion-spec/1`, common primitive payloads, a local deterministic five-asset fixture route, `visual-asset-manifest/1`, creator folders and Markdown/CSV Edit Map. The fixture produces three MG clips, a path clip and a controlled metaphor clip without external API keys.
- The installed local ffmpeg lacks SVG decoding and `drawtext`; the fixture renderer therefore proves deterministic 1920×1080 MP4/path reveal and asset QA, but does not yet provide final Chinese text typography. This is a production gap, not a real-episode pass.

### Visual Asset Engine MVP design

- Recorded the non-implementation MVP contract for a Visual Director that makes one of four explicit decisions per safe A-roll opportunity: keep the speaker, show reviewed real material, use parameterized MG, or reserve a small number of advanced motion moments.
- Defined the proposed MG grammar, Advanced Motion Spec, asset-manifest/Edit-Map, human review, Gate and fallback contracts. No renderer, production logic, formal artifact, media output, tag, release, or main branch was changed.

### Real-user visual presentation and output-truth hardening

- Corrected the aligned Preview presentation contract: approved full-screen material and Motion placements now occupy the primary canvas; the A-roll returns outside those placement windows, while the subtitle layer remains above both.
- Added controlled `primary_visual`, `primary_visual_with_pip`, and `supporting_overlay` modes. The renderer never derives display semantics from new editorial text; picture-in-picture has an explicit A-roll inset implementation.
- Added persisted final-MP4 Output-Truth evidence and a blocking canonical QA check for formal Full Visual previews. Evidence binds the final output SHA and records saved pre/in/post frames for sampled ready placements.
- Generated the real-user r0003 preview without changing reviewed Script, approved Research, Transcript, Alignment, approved Material, Visual Plan, or A-roll. Canonical QA completed with the existing expected B011 `partial_placement_unready` warning only.

## [Unreleased] - 2026-08-22

### Post-alignment full visual planning

- Added episode-only visual preferences, an immutable alignment-derived 18-beat visual plan, reviewed evidence-bound original visuals, and typed safe handling for unplaced opportunities.
- Real-user preview r0002 passed all six canonical checks with the expected B011 `partial_placement_unready` warning; no release, tag, Script, Research, Transcript, or Alignment change.

本项目使用日期和版本记录实际完成的修改。规划中的功能只写入 ROADMAP，不写入已完成记录。

## [Unreleased] - 2026-08-21

### SAFE-CUE REAL MATERIAL COMPLETION + REAL USER VISUAL PREVIEW

- 针对当前 approved Alignment 仅补齐 VC003/B006 与 VC007/B016 的真实页面/法条截图；没有修改 reviewed Script、
  approved Research、Transcript、Alignment、Basic Subtitle 或既有 Motion。
- 新建不可变 Material Package `MAT-20260821-safe-cue-completion-01` r1 → reviewed r2，Material Review Gate `PASS`；
  新 capture manifest 绑定两张实际打开并保存的 PNG，保留 source URL、capture region、文件大小和 SHA-256。历史 rights
  继续保守记录为 `editorial_reference_only/reference_only`，没有声称取得版权许可，且不让 rights 冒充 Production Gate。
- 从新的 Material lineage 建立 `PROD-20260821T170000-safe-cue-completion-01`、Motion Manifest 和 Production QA；逐项核对
  旧 approved Motion 的 scene/payload/文件 SHA 后只做 canonical rebind，没有重新渲染 Motion，也没有让 Motion 进入新 Preview。
- 复用已有真实 whisper.cpp Transcript、Alignment `ALIGNMENT-96854be79b9048a2b6800e1313efb2a6` 和 Basic Subtitle，生成新的
  620.533333 秒全长 Remotion Preview。新 Edit Bridge/Preview/Manifest/Canonical QA 均保存为新的 immutable session；QA 为
  6 项通过、0 blocking、1 个预期 `partial_placement_unready` warning。新 Preview 当前停在人工作看 Gate，未创建 V1 Release、tag 或修改 main。

### Global Monotonic Alignment Projection + Real User E2E Resume

- 将 Script Alignment 升级为 `script-alignment/2`：完整 reviewed Script 与完整 Timed Transcript 只运行一次
  确定性、顺序保持的 evidence pass，再投影 Beat/Cue；不再让单个 Beat 回退扫描整条真人录音。
- 新增版本化 global correspondence：每个 Script lexical unit 保留 match/numeric/substitution/deletion 与真实
  Transcript index/unit/time；Transcript-only token 保留 leading、Beat-local、Beat-boundary 或 trailing ownership。
  不改写原始文字、时间戳或既有 Profile threshold。
- Beat status 以本地 evidence 重算：普通替换、小缺词、filler 不再自动污染全片；真实长缺口、边界风险与实际
  ambiguity 继续 fail closed。Cue 直接消费自身 global mapping，因此不因父 Beat 的无关 review 自动失去时间。
- 重放用户的既有 immutable Transcript，没有重新运行 Whisper：由 `18/18 needs_review`、213 gaps、8/8 unplaced
  变为 `17 aligned / 1 needs_review / 0 unmatched`、117 global gaps、`2 aligned / 6 unplaced` Cues。B011 保留为
  13-unit 真实文本缺口（需要听音确认）；B018 的约 154-unit Script 外结尾保存为 trailing ad-lib，不进入前段。
- 新增匿名 global-localization、long omission、tail、Cue substitution 18/20、Cue deletion 与 parent-review
  decoupling regressions。真实安全 Cue 为 VC003、VC007，但它们在当前 reviewed Material/Production 中没有可用
  real image 或 Original Motion；因此没有伪造 placement、没有重渲染新 Preview，Human Preview Gate 未达到。

### REAL USER ALIGNMENT BLOCKER DIAGNOSIS

- 对第一次真人 Clean A-roll E2E 的 `18/18 needs_review`、`213 gaps`、`8/8 Cue unplaced` 完成只读诊断；
  未重转写、重渲染、改 Script/Transcript、改 Alignment/Gate/阈值或开发新功能。诊断 JSON 与 Markdown 只保存在
  Git 外的 real-user E2E artifact `diagnostics/` 目录。
- 所有 Script r2、真人 Transcript、Media SHA、Timestamp Mapping、Material r2、Production Plan 与 8 个 Cue
  binding 均重算通过；没有误用 synthetic Transcript、旧 Script revision 或错误 production lineage。
- 根因确认为 mixed：**CASE D 为主因**。当前 per-Beat fallback 在没有整段逐字命中时把单个 Beat 与整条
  Transcript 比较，其他 17 Beat 必然成为 `transcript_insertion/ad_lib`；任何 deviation 又阻止 `aligned/high`，
  因而即使 17/18 Beat 已满足 accepted lexical floors，仍会系统性全部 `needs_review`。B001 的 1,289 candidate
  windows 覆盖几乎全片，是缺少定位的算法歧义，不是 1,289 次真人复读。
- **CASE B 为次因**：全片顺序诊断得到 Script→Transcript exact/numeric lexical coverage `94.8232%`、
  Transcript→Script `90.1872%`，Beat 边界顺序违例为 0；但 B011 有 13-unit 缺口、B018 有 154-unit Script 外
  尾段，需要未来听音频/人工 review 确认。其余主要是专有名词与单字 ASR 噪声或正常口语变化。
- 当前 fail-closed 生产 Gate 保持正确；建议下一步仅由 ChatGPT 决定是否设计“全局单调、顺序感知”的证据
  pass，再投影 Beat/Cue，同时保留 B011/B018 人工 review 与所有安全边界。本轮不实施。

## [Unreleased] - 2026-08-21

### REAL USER CLEAN A-ROLL E2E

- 使用用户提供的真实无烧录字幕 Clean A-roll `/Users/hwang/Movies/口播/AI事故8月21日.mp4` 完成正式本地
  large-v3 生产路径：immutable media → 24 kHz mono audio → whisper.cpp v1.9.2 full multilingual
  `large-v3` + `--dtw large.v3` → Timed Transcript → Script Alignment → Edit Bridge → 完整 Remotion Preview
  → canonical QA。原始媒体 SHA-256 为 `39d08733447f78c60b5cc0f737781c8fc3a9d95629d7f92a04902bbe0f8e57ec`，
  时长 `620.530068` 秒；输入文件未移动、覆盖或改写。
- 真实 Transcript 生成 2,646 个 token/unit，raw token overlap `0`，未使用 fixture、synthetic timing、
  cloud ASR、second ASR、forced aligner 或 Script 覆盖 Transcript。Timed Transcript digest 为
  `85154b27fed6b9871c4975692b37410d5d79526caa7128cb3d0ccc2d525b92f7`。
- 18/18 Beat 为 `needs_review`（13 medium、5 low），存在 213 个 alignment gaps；8/8 Cue 为 `unplaced`，
  因此所有真实截图/文件与 Original Motion 均保持未落位，没有猜时间或伪造素材位置。产品 Alignment、
  Material Placement、Motion Placement Gate 阻塞；不得把技术 QA warning 误写成完整 E2E 通过。
- 生成完整 Preview `ALIGNED_PREVIEW.mp4`，1920×1080、30fps、H.264/AAC、`620.533333` 秒，SHA-256
  `36d29165238bd1a2dcb05060be067aee05eedfe44f0898ce0b3858e589d71bf9`；当前路径仍烧录 Basic Subtitle，
  没有无字幕 visual master。Canonical QA 6 项通过、0 blocking failure，唯一 issue 是预期的
  `EBI0001 partial_placement_unready` warning。
- 本次 production session 没有持久化 whisper 单阶段 runtime/RTF，已在 HANDOFF 标为 observability gap，
  未从文件时间伪造精确数值。完整代码回归 `454 passed, 3 skipped`；本轮未修改 Script、Research、Material、
  main、v0.6.1 tag 或 GitHub Release，V1 仍为 `Candidate — Unreleased`。

## [Unreleased] - 2026-08-14

### Quality-first large-v3 long-form production validation

- 按用户明确的 quality-first 决策，将 V1 唯一生产默认从 historical medium 升级为官方完整精度 `ggml-large-v3.bin`，固定 `whisper.cpp v1.9.2`、source commit `306c88f4d1286aec1bf96e544632897886af5501` 和正确的 `--dtw large.v3`；medium Selection Gate 工件与缓存保留，不被改写或删除。
- Bootstrap 现在核验 full large-v3 的官方 URL、`3,095,033,483` bytes 和 SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`，并记录 DTW provenance。桌面环境未继承 shell proxy 时会读取已启用的 macOS HTTPS 系统代理，仅用于官方模型下载。
- 新增 raw overlap audit：任何相邻 token overlap 仍 fail closed，但会输出包含 chunk、segment、raw token/provider order、raw 起止时间、控制 token、边界、runtime/model/DTW 和 raw JSON digest 的版本化证据；没有引入 canonicalization、segment fallback、LLM/dictionary/second ASR 或 cloud fallback。
- 新增外部证据 runner 与 render liveness monitor。真实 no-key 272 秒 smoke：large-v3 在 Apple M4 Metal 上 87.210505 秒、RTF 0.320194、1,167 token、overlap 0，且 `ProviderTranscript → Timed Transcript → Script Alignment` 通过。相同音频上 large-v3 保留 OpenAI、DeepSeek、AI Agent、GPU；`昇腾` 仍未精确命中，原始文本未被人工修正。
- 真实非私人 274.267 秒 synthetic Clean A-roll 已跑完完整 production E2E，生成 1920×1080/30fps H.264/AAC、274.3 秒 Aligned Preview，SHA-256 `2377c5459c5bd31894ece27c105ec7305f03269f215732c41efea619df773c81`；完整 session 665.763 秒，canonical QA 0 blocking failure，保留 1 个预期 `partial_placement_unready` warning。
- 本轮未修改 reviewed Script、approved Research、reviewed Material Package 或历史 Production 工件；未创建 tag、Release 或修改 main。真实用户 Clean A-roll Gate 仍需要下一轮真人试用与人工 Review。

### V1 Local Transcription Production Integration

- 将已通过 Selection Gate 的 `whisper.cpp multilingual medium` 变成正式 `LocalWhisperCppTranscriptionProvider`，接入现有 `TranscriptionProvider → ProviderTranscript → Timed Transcript` 契约和唯一 `run_real_edit_bridge_session` 入口；未修改 reviewed Script、approved Research 或 reviewed Material Package。
- 新增 repository-owned bootstrap：锁定 whisper.cpp v1.9.2/source commit `306c88f4d1286aec1bf96e544632897886af5501`，Apple Silicon 启用 Metal，自动准备 runtime 与 1,533,763,059-byte medium 模型，SHA-256 固定为 `6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208`；runtime、model、provenance 只进入外部 `~/.cache/deep-talk-studio/transcription/`，不进 Git。
- 默认路径不查看或要求 `OPENAI_API_KEY`；OpenAI adapter 保留为未来可选能力。Provider 只接受 whisper.cpp full JSON 的真实 token offsets，缺失、越界或重叠时 fail closed，禁止插值、LLM 伪造和 silent cloud fallback。
- 新增本地长音频 `transcription-chunk-profile/local-whisper-cpp/1`，继续复用现有 PCM natural-pause `TranscriptionChunkPlan` 与 local→global mapping；ProviderTranscript 绑定 runtime/model/audio/chunk/raw-response provenance。
- 无 API Key 的真实非私人音频 smoke 通过：1,136 token units、token granularity、runtime 42.780224 秒、RTF 0.157068，transcript digest `153374e56a30e2f29a6ac923008dbc510db8b202539734f0445a97c82926e5dd`。
- 正式短版 production E2E 通过：真实 whisper.cpp → Timed Transcript → Alignment → Material → Motion → Basic Subtitle → Edit Bridge → Remotion Aligned Preview → canonical QA，输出 20 秒、1920×1080、30fps、H.264/AAC 的 preview，QA 无 blocking failure，只有预期 `EBI0001 partial_placement_unready` warning；Preview 保留原 Clean A-roll 音频。
- 长版合成验证如实记录为 gap：标准 24 MiB profile 的尾 chunk 曾出现越界，已用版本化本地 long-form profile 修复；完整 272 秒验证又发现 5 处 runtime token overlap，按 fail-closed 停止；约 272 秒 Remotion render 在本机环境耗时过长而停止。真实用户 Clean A-roll 尚未提供，因此 `REAL USER CLEAN A-ROLL GATE` 仍为 `BLOCKED/PENDING`。
- 本轮保持 `V1.0 Candidate — Unreleased`；没有新 tag、Release 或 main 修改，selection history `evaluations/local_asr_selection/` 保留。

## [Unreleased] - 2026-08-14

### Local ASR Selection Gate

- 按 ChatGPT 最终产品原则完成真实本地 ASR 选择 Gate；没有执行旧的“直接采用 whisper.cpp”方案，没有修改 reviewed Script、approved Research、reviewed Material 或正式 Production 工件。
- 用同一份非私人 272.367 秒、24 kHz 单声道中文评测音频比较官方 `whisper.cpp v1.9.2` multilingual medium 与 Microsoft `VibeASR.cpp` / `VibeVoice-ASR-BitNet@66e7802`；模型、音频和原始长日志均放在项目外部缓存。
- `whisper.cpp` 在 Apple M4 Metal 上真实 wall runtime 44.37 秒、RTF 0.1630，输出直接 token offsets，并完成 `ProviderTranscript → Timed Transcript → Script Alignment`；新增 evaluation-only parser 与最小 adapter regression。
- VibeASR 在同音频真实运行 JSON/text 两种模式，RTF 1.2109/1.0402；没有 machine-owned media timestamps，且输出重复文本并耗尽 max tokens，按时间戳 Gate fail closed，不生成 Timed Transcript 或 Alignment。
- 选择结论：推荐 `whisper.cpp multilingual medium` 作为 V1 默认本地 Provider 候选；正式默认接入与自动 bootstrap 仍为 `PENDING_CHATGPT_REVIEW`，本轮不创建 V1.0、tag 或 Release。
- main、正式 `v0.6.1` tag 与 GitHub Release 保持不变；V1 仍不依赖任何 API Key，现有 OpenAI Provider 只保留为后续可选能力。

## [Unreleased] - 2026-08-13

### REAL USER E2E Preflight unblock - 2026-08-14

- 安装并验证项目专用 OpenAI Python SDK `2.54.0`；未记录或输出任何 Key。`OPENAI_API_KEY` 缺失，真实 OpenAI smoke 尚未运行，也没有 deterministic fallback。
- 新增不可变 `material-capture-manifest/1` 和 Material Production View 重放：已检查素材只有在 exact package/material/source/capture/Cue binding、静态 MIME、允许目录、size 和 SHA-256 都通过时，才可成为 `ready`；rights/reuse 仍只作历史元数据。
- 已实际打开当前 M001 OpenAI 官方页，将真实页面截图登记为 VC001 生产素材（PNG、127,433 bytes、SHA-256 `d3305a0d3b9c58c950aa75421c05effb27013d581916a9e0156026106788b3e1`）；Material r2 和 reviewed 历史保持不变。

### REAL USER CLEAN A-ROLL E2E Preflight

- ChatGPT 已批准进入真人 E2E Gate；本轮完成只读 Preflight，未新增产品功能、未修改历史工件。
- 分支 `agent/audio-alignment-edit-bridge` 的 reviewed HEAD `5ff947c`、workspace、ffmpeg 8.1.1、ffprobe 8.1.1 与实际 Remotion exact-entrypoint render 均正常；当前 approved Research r3、reviewed Script r2、reviewed Material r2、Production Plan、Motion Manifest 与 Production QA 精确绑定，Production QA 为 pass。
- 真实 OpenAI transcription Preflight 判定为 blocked：当前运行环境没有 `OPENAI_API_KEY` 和 OpenAI Python SDK。adapter 单元测试通过，真实 smoke 诚实跳过；不允许用 deterministic provider 代替真人转写。
- 本期 Real Material Preflight 判定为 missing_asset：外部网页/官方文件仍未取得本地 capture，未被升格为 ready；现有原创 Motion 输出可用。真人 E2E 因转写与真实素材两项 blocker 暂不开始。
- main、`v0.6.1` tag 和 GitHub Release 均未改变。

### V1 scope reconciliation + Basic Subtitle V1

- “全面冻结功能”临时边界已撤销，恢复 `reviewed Script + Clean A-roll + Real Material + Original Motion + Basic Subtitle → 完整可观看粗剪` 的 V1 产品目标；仍不扩展 A-roll cleanup、BGM/SFX、标题封面、发布或 NLE 专属导出。
- Hook-aware Script 复用现有 `audience_promise`、有序 Beats 与 `closing`，不升级 Script Draft schema；新 Review consistency mapping `0.4.2` 将缺失 opening hook、value promise、必要 re-hook / information turn 或 conclusion payoff 记录为 blocking `hook_structure`，旧 `0.4.1` Review Artifact 保持可读。
- 新增 `subtitle-profile/1`、`subtitle-artifact/1`、不可覆盖 JSON/SRT 存储和确定性显示 normalization。word/token 只组合真实 unit boundaries；segment-only 一段一 cue 并保持 coarse，不伪造 word/karaoke precision。
- Subtitle digest/Profile digest 进入 Edit Bridge root bindings；Remotion 在 A-roll、图片、视频与 Original Motion 全部时段烧录两行基础字幕，并为视觉 overlay 统一保留字幕安全区。
- 唯一正式 production entrypoint、自然语言 Bridge revision、Aligned Preview Manifest 与 repository-owned canonical QA 均绑定同一 Subtitle/Transcript/Profile；Transcript revision 改变、字幕篡改或 renderer 未启用字幕都会 fail closed。
- 完整 unittest 为 436 项，433 pass、3 environment/explicit-render skip；字幕定向 26 项通过，renderer lint/typecheck 通过。exact-entrypoint 真实 synthetic Remotion E2E 同时生成初版与自然语言修订版：H.264、1920×1080、30fps、2 秒、单一 Clean A-roll AAC 音轨，SHA-256 分别为 `283b2bace94f3853745f4740fcdfc33b6bb5595b2d3a96def2748f005be19919` 与 `cf13a810249dc897556592cfec7ba47f9ed5b692ee48d50c1b71693a07460b2a`，两版 canonical QA 均为 warnings（预期未选视频缺口，无 blocking failure）。
- 本阶段继续 Unreleased；没有修改 reviewed Script、approved Research、reviewed Material 历史、main、v0.6.1 tag 或 Release。真实 provider 与真实用户 Clean A-roll E2E 仍 pending。

### Audio Alignment + Visual Edit Bridge implementation

- 完成 Implementation Review 后的 Integration Hardening：新增唯一具体生产入口，自动解析最新匹配的 approved Research、reviewed Script、reviewed Material 与已通过 Production roots，并按固定顺序运行 Media → Mapping → Chunk → Transcript → Alignment → Placement → Bridge → Remotion → audio mux → canonical QA；旧 stage-lambda harness 不再是正式路径。
- Material Production View 现在保留 `asset_type`、`capture` 与 `video_reference`，真实图片、有范围视频、无范围视频分别确定性进入 `real_image`、ready `real_video`、`clip_selection_needed`；未经选择的公开视频不会自动猜选段。
- Cue OUT 从短 anchor 扩展到下一 Cue anchor 或 Beat 结束的完整语义范围；Alignment 总时长改为绑定 Clean A-roll presentation duration，不能再由最后一个 spoken unit 截短。
- OpenAI adapter 保持 real word timestamps 优先；只有 real segment timestamps 时明确标记 `segment/coarse`，两者都没有则 capability fail，不做插值。
- 正式 QA 改为 repository-owned canonical factory，自行重探测 Media、重建 Mapping/Chunk/Alignment/Material/Placement/Bridge，并核验 Preview Manifest、SHA 和音频 presentation；调用方不能再传自定义 lambda 充当正式 QA。
- 自然语言“短一点/长一点/早一点/晚一点/一直留真人”会真正改变 Preview effective timing 或 overlay suppression，并创建不可覆盖的 Bridge/Preview/Manifest/QA revision；reviewed Script、approved Research 和 canonical semantic window 不变。
- 真实 Remotion exact-entrypoint E2E 同时覆盖可用图片、已选范围视频、未选范围视频、QA-ready Motion 与带内部静音的 Clean A-roll；生成 1920×1080/30fps H.264 + 单一 Clean A-roll audio 的 `ALIGNED_PREVIEW.mp4`，SHA-256 `029e5211071126bc0183eb2dc354b24ebff5089d9d80a8ff724ff7e7ba38b58f`，595,390 bytes，canonical QA `warnings`（未选视频保持 `clip_selection_needed` 且未入画，无 blocking failure）。
- 完成批准计划 Task 0 与 Task 1–29：稳定 Discovery 冻结时间基线，并实现不可变 Clean A-roll 导入、媒体 presentation 证据、lossless transcription audio、可重推导 Timestamp Mapping、确定性自然停顿 Chunk Plan 与 boundary-risk 全链路保存。
- 新增 provider-neutral Transcript、当前 OpenAI `whisper-1` word timestamp adapter、可逆中英文 normalization、确定性 Script/Transcript 对齐、校准 Profile、Beat/Cue timeline 与不可覆盖 Alignment revision。
- 新增 reviewed Material production projection、图片/视频/Motion 统一 Placement、frame-rate-neutral IN/OUT/duration、冲突与 7 秒 long-still Preview safeguard，以及 Edit Bridge JSON/Markdown/CSV/revision。
- 新增 1920×1080/30fps Remotion Aligned Preview：Clean A-roll 为 layer 0，仅 ready 画面进入；纯视觉中间片无音轨，最终只混入原 Clean A-roll 主音轨。AAC/MP3 优先 copy，PCM 等不兼容 codec 转 AAC，正 presentation offset 与内部静音均重新 probe 并验证。
- 新增五组 QA/Gate、普通用户 `align-video` Skill/CLI、A–AI、CB1–CB7、PA1–PA7 与 property/invariant 评测。合成真实 Remotion/ffmpeg Preview 已通过；真实 OpenAI provider smoke 因本机没有授权环境而诚实跳过。
- 本阶段保持 Unreleased；没有修改 reviewed Script、approved Research 或 reviewed Material 历史，没有创建 V1.0、tag 或 Release。下一步停在真实用户 Clean A-roll E2E Gate。

### Audio Alignment + Visual Edit Bridge design

- 根据 Implementation Plan Conditional Pass 加固两个 blocker：新增 `transcription-chunk-profile/1` 独立 Task 7，并将 Provider protocol 顺延为 Task 8，以确定性 PCM RMS natural-pause 搜索取代任意按大小硬切，让 fallback boundary risk 贯穿 Provider、Timed Transcript、Alignment、Bridge 和 QA。
- Preview audio mux 计划新增 presentation timing 等价契约与真实媒体回归：正 audio offset、normalized raw PTS、internal gap、AAC copy/convert 和“总时长正确但声音被提前”均须由 QA 重新探测；总任务数由 28 调整为 29。
- ChatGPT 最终 Design Review 已通过；新增 `docs/superpowers/plans/2026-08-13-audio-alignment-edit-bridge.md`，将 approved contract 拆为 28 个有明确文件、接口、红/绿测试命令和 commit boundary 的 TDD Tasks。
- Plan 单独规划真实 ffmpeg/ffprobe 媒体 fixtures、可重算 Timestamp Mapping、provider-neutral/OpenAI transcription、span-preserving normalization、等价全局 DP、Profile calibration、Material production projection、统一 Visual Placement、duration/conflict policy、Remotion Aligned Preview、Clean A-roll audio mux、QA/Gate、CLI/Skill、A–AI eval、real provider smoke 与 real-user E2E Gate。
- Planning 阶段只查询 OpenAI 官方 Speech-to-Text/API 文档并固化当前 capability boundary；没有调用转录 API、没有上传媒体、没有修改产品代码、没有 render 或创建 Release。
- 根据 ChatGPT Conditional Pass 完成 Design Contract Hardening：将 container/stream PTS、Clean A-roll presentation timeline 与 extracted-audio timeline 分离，新增可验证的 affine Timestamp Mapping；正常 AAC priming/padding、edit list 和非零/负 PTS 不再因非 identity offset 被误伤。
- canonical Edit Bridge 时间统一为 decimal seconds 与 `HH:MM:SS.mmm`；30fps frame/timecode 只保留为 Aligned Preview 派生字段。
- 将 placement uncertainty 与 timing conflict 拆成正交状态：可靠 placement 可携带 duration/overlap warning 并进入 Rough Cut；same-start selection ambiguity 才阻止自动 Preview。
- 长静态画面新增版本化 7 秒 Preview exposure safeguard，继承 Material Profile 0.5 的已有默认 Cue 时长；canonical semantic OUT 保留，调整与 warning 全部可审计。
- 完成 repository inspection 与 Design Review Candidate：把 immutable Clean A-roll 定义为 canonical timeline，设计 Narration Media、Extracted Audio、Timed Transcript、Script Alignment、Visual Placement、Edit Bridge 和 Aligned Preview 契约。
- 设计 provider-neutral Speech-to-Text boundary、保留原文 span 的中英文 normalization、确定性序列对齐、版本化 threshold/Profile、Beat/Cue anchor 映射和可重推导 Gate；LLM 与 provider 均不能自报 canonical timecode 或 pass。
- 将真实图片、截图、真实视频、现有 Motion 与 A-roll 纳入同一 placement model，定义真实 IN/OUT/duration、layout、source clip 双时间轴、timing conflict 和 preview-only adjustment。
- 明确历史 rights/reuse 字段继续兼容读取但不再成为新制作 Gate；文件存在、SHA、MIME/codec、path、grounding、binding 与 Production QA 保持严格。
- 设计 26 个指定 adversarial cases、不可覆盖 revision、partial recovery 和真实 Clean A-roll E2E 边界；本轮没有 implementation、implementation plan、真实转录、渲染或新 Release。

### Real user trial

- 第一轮真实用户链路已从 Topic Discovery 继续跑通到 reviewed Research、reviewed Script、reviewed Material Package 和 Production QA；全程未使用 fixture，也未改写已审核稿件。
- Material Review 通过：8 个画面提示、7 个仅供编辑核对的公开来源、3 个基于已批准 Research 的原创画面；没有明确复用依据的网页和文件未进入渲染。
- Remotion 实际生成 8 个场景片段、1 个 rough visual preview 和 1 张 hero still；Production QA 通过，所有 10 个工件均为 ready。
- 真实来源仍保留 5 个 reference-only 画面缺口，真人录音尚未提供，因此另保留 1 个语音时间码缺口；系统没有用伪造截图或自动改稿掩盖缺口。

### Fixed during manual visual review

- 修复 Remotion timeline 两端日期和事件文字贴近画布边缘的问题，增加左右安全区并扩大事件文字容器。
- 新增 timeline safe-area 回归测试；首次存在问题的 Production 输出保持不可覆盖，修复后创建新的 Production 工件并重新通过 QA。
- 修复真实 Trial diagram 中文长 node label 与 node box、edge label 与连接线的可读性问题；两个 renderer 统一使用可换行 node 容器和独立背景 label plate，超过确定性容量时在 Renderer 前失败。
- comparison 不再由 Planner 无条件生成“两个解释”，改用版本化中性标题“要点对照”；每个 mechanism 只显示一次并在独立 card 内保留两条 grounded facts，Remotion / HyperFrames 共用同一 payload 语义。
- 新增真实中文长 Diagram、三项 Comparison、单次 mechanism label、fact binding 与 machine-editorial allowlist 回归；任意事实文字仍不能伪装成机器标题。
- 使用原 reviewed Script、approved Research 与 reviewed Material Package 生成新 Production `PROD-20260813T133848055707`；10 个真实工件 ready、QA pass，旧输出未覆盖。
- Git canonical lineage 修复：保留无共同祖先的旧审计分支，从远端 canonical main 新建 `agent/real-e2e-preview-hardening-mainline` 并迁移完全相同的 hardening tree；不触碰 main、v0.6.1 tag 或 Release。

## [0.6.1] - 2026-08-11

### Added

- Production Scene 新增严格 `scene_payload`，统一保存 timeline、bar、comparison、diagram 的元素、顺序、文字和 binding。
- Remotion 与 HyperFrames 新增四类逐元素 motion semantics；公开三柱虚构动效生成器可产出双引擎 MP4、contact sheet、ffprobe、SHA 和 QA 证据。
- Display Text 新增 `machine_editorial`、`research_fact`、`research_attribution`、`material_caption`、`visual_label` 来源。
- renderer 命令新增结构化 check：name、renderer、exit code、outcome、category、安全摘要。

### Changed

- V0.5 SVG 不再作为四类 Motion 动画主体；两套 renderer 只消费同一 Python Core payload。
- HyperFrames rough preview 改为新场景覆盖式入场，不再提前淡出旧场景。
- rough preview 仅在 MAPREVIEW 真正进入 Manifest 且 ready 时宣称成功。

### Security

- 无数字事实文字、无关 Claim、无依据因果 edge 和虚假素材 caption 均在项目生成前失败或安全降级。
- raw PDF 永不 stage/render；无已审 capture 时生成固定缺口。
- fail check 确定性生成 blocking issue，Production QA 无法同时保存失败检查和通过 Gate；公开命令摘要会脱敏本机路径和局域网地址。

### Verification

- unittest 共 **267 项**（266 项执行通过、1 项真实渲染集成测试默认跳过）；V0.6.0 的 255 项基线全部保留。
- 双引擎真实渲染同一份 3 元素 synthetic bar Plan，Remotion 4.0.507 与 HyperFrames 0.7.106 均通过完整 validation/preview/render/ffprobe/QA。

## [0.6.0] - 2026-08-11

### Added：Motion Production Layer

- 新增 Production Profile、Production Plan 0.6、Motion Asset Manifest 与 Production QA 严格契约。
- 新增 V0.5.1 canonical input Gate、render-time path/MIME/size/SHA/eligibility Gate 和 Display Text Grounding Gate。
- 新增共用同一计划与 QA 的 Remotion / HyperFrames adapters；锁定依赖，普通流程只运行一个 renderer。
- 新增 timeline/bar/comparison/diagram、document/screenshot、static image、A-roll placeholder 映射、Production gaps、rough visual preview 和 immutable storage。
- 新增 `produce-assets` CLI 和 `.agents/skills/produce-video-assets`。

### Fixed during real rendering

- Remotion 复用本机 Chrome、固定单并发渲染并显式绑定 project `public/`，避免慢速浏览器下载、多标签失败和 asset 404。
- HyperFrames 修正 `.clip` timing 标记和 root-relative asset path，并通过官方环境变量复用本机 Chrome。
- 原创完整 SVG 不再叠加重复标题；Timeline 文本保留 safe area。含数字标题与 Research Timeline 日期在精确绑定后可通过，新数字仍失败关闭。

### Validation

- 完整 unittest 共 **255 项**（254 项执行通过、1 项真实渲染集成测试默认跳过），原 219 项全部保留。
- 显式启用真实渲染测试：同一 tiny Plan 在 Remotion 和 HyperFrames 均完成 validation、preview、MP4/PNG render 与 QA pass。
- Apple 财报 bar 完成 Remotion 全链路真实 MP4 并 QA pass；欧盟 AI Act 和 rights-sparse 验证 reference-only 隔离、原创 timeline/diagram 与 A-roll fallback。
- blocked Material Package 在 renderer 前拒绝；asset tampering 在 SHA/size Gate 失败关闭。

## [0.5.1] - 2026-08-11

### Fixed：Material Gate Hardening

- Rights manifest 新增 `rights_evidence_url`；safe reuse 必须同时有素材页和权利页 actual-open，权利工具引用必须匹配，license URL 必须为可审计的同一权利页。模型权利自称、伪造链接和只有素材页的情形均不能进入 `ready_to_use`。
- 补齐 timeline、bar、comparison、diagram 的 nested Claim/Evidence grounding；timeline 精确匹配 Research date/Claim/Evidence/label，bar 使用数字边界并验证 value label，diagram node 必须有合法 Research basis。
- 新增 r1 Material Input / Inspection / Rights provenance artifacts。reviewed r2 在 loader 中重新生成 r1、验证精确 Review Artifact，再确定性导出 r2；篡改 eligibility、rights、provenance、ranking、status 或 review linkage 即使重算 digest 也失败关闭。
- SVG sanitizer 改为 XML 结构检查，允许标准 namespace，仍拒绝 script、event handler、foreignObject、外部 href 和危险 CSS URL。截图强制 1-based 页码与图片 magic/扩展名一致。

### Validation

- 原 205 项测试继续通过；新增 rights actual-open、nested Visual、canonical loader、SVG 与 capture 边界测试后，完整 suite 为 **219 项通过**。
- 重跑 A Stable Business、B Contested Public、C Rights / Sparse 评测，并新增 D 未打开权利页、E comparison C404/E404、F 手改 reviewed r2 三个 fail-closed 场景；公开汇总为 `evaluations/v0.5.1-summary.json`。

## [0.5.0] - 2026-08-11

### Added：Material Search & Visual Assistance

- 新增 Material Package / Visual Spec / Material Review 0.5 完整 JSON 契约，以及 B 站 1920×1080 Material Profile。
- 新增 reviewed Script 输入 Gate：复验 V0.4.1 Review Artifact、Review ID、被审 revision、内容 SHA-256 和精确 Research revision；draft、伪造状态、缺 Artifact 或错版底稿在搜索前失败关闭。
- 新增 Cue Sheet、素材类型、Evidence/Context/Illustration/Transition 边界、Claim/Evidence binding、URL 规范化去重和透明五维排序。
- 新增 actual-open inspection manifest 与独立 Rights manifest；API Web Search 结果只标 discovered，未知权利和普通新闻不会成为 ready-to-use。
- 新增安全静态文件获取和网页/PDF capture 登记：公开 URL、MIME、大小、SVG 脚本、路径、覆盖、SHA-256 与证明边界均受控。
- 新增 Research update escalation；素材搜索发现冲突或更新时不静默改稿、Research 或 Visual。
- 新增 timeline、bar、comparison、diagram Visual Spec grounding 和实际 1920×1080 SVG renderer；保留 Remotion/HyperFrames future hints，但不创建视频工程。
- 新增 10 项独立 Material Review、typed blocking issues、item isolation、package Gate、不可覆盖 Package/Review/Asset 存储和普通用户简明 Markdown。
- 新增 `prepare-materials` Skill、`search_materials/review_materials` Provider boundary、OpenAI API 和 `prepare-materials` / `review-materials` / `materials` CLI。
- 新增三类真实世界编辑评测和隔离安全下载评测；完整真实工件与资产保持 gitignored，公开仓库只提交去内容化汇总。

### Validation

- 原 165 项测试全部继续通过；新增 40 项后完整 suite 为 **205 项通过**。
- 新测试覆盖 input gate、provenance、rights、binding、dedupe、research update、下载、截图、四类 Visual、Review、存储、Provider、CLI 和 Skill。
- 三类评测分别证明：官方页无复用依据时保持 reference-only；EU CC 页面可 ready 而普通新闻仍 unknown；rights 稀缺时优先原创 SVG，不伪装许可。

## [0.4.1] - 2026-08-10

### 修复：Script Gate Hardening

- 增加版本化、确定性的 Script Review check → issue mapping。15 项检查任一 `fail` 都必须有对应 issue；八项事实安全检查必须有对应 blocking issue，否则直接拒绝 Review Artifact，不能错误产生 `reviewed`。
- 收紧 `not_applicable`：事实安全检查不可跳过，仅 `counterargument_fairness` 可在明确无可审反方时使用。
- 新增 machine-owned `review_state`、Review Artifact 内容 SHA-256 和 consistency mapping 版本。`reviewed` Script 在读取时复验真实通过的 r1 Review Artifact、Report/Script binding、Gate 和内容指纹；手改状态或伪造 Review 字段失败关闭。
- 旧 V0.4.0 `reviewed` JSON 如没有 linkage 不再被静默信任，必须重新执行 Review；旧 draft 仍可读取并在下一修订建立新的 identity state。
- 增加稳定 Beat identity：保留或移动的段落保持 ID，新增段落取得单调递增 ID，删除 ID 退休且永不复用；比较结果不再把中间插入误报为整篇修改。
- 更新 Writer/Reviewer prompt、仓库 Skill、Script Contract、架构、PRD、ROADMAP、AGENTS、README 和交接文档；V0.5 未开始。

### 验证

- 原 151 项测试继续通过；新增 Review 一致性、provenance、存储加载、修订 identity 与比较回归后，完整 suite 为 165 项通过。
- 重新执行 A/B/C 受控工作流评测并加入 `factual_grounding=fail + issues=[]` synthetic 场景；完整真实稿件继续保持 gitignore，公开仓库仅提交去内容化汇总。

## [0.4.0] - 2026-08-10

### Added

- 新增不可覆盖的 Approval Revision：只有完成独立 Fact Check、通过 Quality Gate 且处于 `reviewed` 的 Research Report 才能记录用户原始确认并进入 `ready_for_script`。
- 新增 Script Profile 0.4、Script Draft Artifact 0.4、独立 Script Review Artifact 0.4，以及 Editor / Teleprompter 双输出。
- 新增 `write-script` Codex Skill，普通用户可直接说“根据这份研究写稿”“做成 8 分钟”或“第二段更紧凑”；不需要修改 JSON 或执行命令。
- 新增稿件 grounding：Beat 级 Claim / Evidence 回链、Fact / Attribution / Analysis 边界、已核查高风险事实检查、`avoid_claims` 硬阻止和 must-keep coverage。
- 新增独立 Writer / Reviewer 工作流；Reviewer 必须完成 15 个必检维度，阻断问题由程序计算 Gate，模型不能自报通过。
- 新增不可覆盖的 Script revision、版本比较、自然语言时长解析，以及 `approve-report`、`prepare-script`、`review-script`、`revise-script`、`compare-script`、`write-script` CLI。
- 新增 `docs/SCRIPT_CONTRACT.md`、`docs/SCRIPT_EVALS.md` 和去内容化 `evaluations/v0.4.0-summary.json`。

### Validation

- 原 113 项测试全部继续通过；V0.4 新增 Approval、Script Artifact、grounding、审稿 Gate、存储、修订、CLI 和无 Web Search 边界测试。
- 稳定商业报告和争议公共议题报告均经过正式 Approval Revision、完整写稿和独立 15 项复核，最终成为 `reviewed` 稿件；实际阅读两份 Teleprompter 后分别完成 10 维人工编辑评分。
- 未获用户批准的 `reviewed` Research Report 被拒绝写稿，退出码为 2，且没有创建任何稿件文件。

### Security

- Script Writer 与 Reviewer 均只读已批准 Research Report，不启用 Web Search；API 请求载荷不包含搜索工具，带搜索 provenance 的结果会被拒绝。
- 真实完整稿件继续保存在 gitignored `script_drafts/`；公开仓库只提交去内容化评测指标。
- V0.4 不实现素材搜索、视觉生成、剪辑或自动发布，V0.5 仍未开始。

## [0.3.1] - 2026-08-10

### Fixed

- Codex Discovery 不再因为运行模式自动把 Source Seed 视为已打开；只有后台 inspection manifest 中实际检查的规范化 URL 才会成为 `manual_open`，其余保持 `unmatched`。
- 新增纯确定性 Candidate derivation；读取 Candidate Set 时重新推导资格、理由、推荐、总分、展示顺序、首选和 watch/reject 统计，任何篡改均 fail closed。
- Preflight 现在只计入 provenance 已匹配、来源类型合格且 URL / publisher / host 不重复的研究方向；social / creator Seed 与重复链接不能凑足门槛。
- 新增开始/更新时间顺序和最多 5 分钟未来容差；未来时间不再获得 freshness。
- 类别展示改为先多样后补位，同事件仍只出现一次；移除了没有实际作用的 `discover --count` 参数。
- 原始候选池少于 7 项时明确拒绝生成 Candidate Set，不再把 1–2 个候选误称为完整 Discovery。

### Validation

- 自动测试由 101 项增加至 113 项，覆盖 inspection manifest（含无工具引用的实际打开记录）、机器字段篡改、来源方向去重、时间、类别补位、Raw Candidate 最小池、CLI 与旧 Research / FactCheck / Quality Gate 回归。
- 三类真实 Discovery 评测已重新执行；公开汇总使用 `pass`、`fail` 和 `not_applicable`，不会在候选不足时宣称已经验证 Top 5。

### Compatibility

- Candidate Artifact 继续为 `0.3`，Research Report 和 FactCheck Artifact 继续为 `0.2`；旧的 Candidate Set 仍可按其保存的 legacy provenance 状态读取，但不会被提升为新检查过的来源。

## [0.3.0] - 2026-08-10

### Added

- 新增模式 B Topic Discovery：用户可直接说“今天讲什么？”“帮我找几个选题”或指定科技、商业、社会等方向；默认展示最多 5 个候选和一个首选。
- 新增版本化 `config/channel-profile.json`、独立 `Topic Candidate Set 0.3`、`Research Handoff Brief 0.3`、Discovery 历史和 latest 指针；不改变 Research Report / FactCheck Artifact `0.2`。
- 新增轻量 Source Seed Preflight、72 小时与持续事件时间规则、五维透明评分、机器总分、Eligibility Gate、事件聚类、类别多样性、watch/reject 状态和简短 Markdown 选题卡。
- 新增 `discover-topics` Codex Skill；用户只回复 `1` 或 `研究 1` 就能把候选的研究问题、核心张力、风险和 Seeds 交给已有 `research-topic` Skill。
- 新增 OpenAI Discovery API 调用、`discover` / `prepare-discovery` / `select-topic` / `research-selected` CLI 入口，以及 Topic Discovery 契约和三类真实评测方法。

### Changed

- `research-topic` 支持接收结构化 Research Handoff，不再要求用户把已选标题复制一遍。
- README、PRD、ROADMAP、AGENTS、架构、评测、CHANGELOG 和 HANDOFF 同步 V0.3；V0.4 Script Agent 仍未开始。

### Validation

- 自动测试由 85 项增加至 101 项，覆盖 Candidate Schema、评分权重与总分所有权、Eligibility Gate、72 小时/持续事件、陈旧事件、Seed URL、去重、多样性、watch、历史、编号交接、Codex/API、CLI 和模式 A 回归。
- 三类真实公开 Discovery 场景完成并只提交去内容化汇总；快速高风险且资料薄弱的线索保持 `watch` / `rejected`，没有为增加候选数量而降低门槛。

### Security

- Creator signal 为可选辅助信号，不能作为事实证据；不抓取稿件、字幕或独特表达，也不伪造播放量或热度。
- 真实 Candidate Set 继续保存在 gitignored `discoveries/`；API 模式无法匹配真实 Web Search provenance 的 Seed 不会装作已打开。

## [0.2.1] - 2026-08-10

### Fixed

- confirmed fact 独立确认现在只接受 `supports + matched + independent + 不同 independence_group`；`unknown`、`related`、`duplicate`、`syndicated` 均不能贡献独立确认。
- context-only 与未匹配来源不再抬高 claim source coverage；未匹配 attribution 不再解除无来源归属；duplicate / syndicated 不再抬高来源类型或 provenance 指标。
- Fact Check 新来源与 Research Draft 来源统一执行 URL 规范化、追踪参数去除、重复、同发布者、转载和 independence grouping；保存的 Artifact 与 reviewed report 使用相同确定性结果。
- 重复 URL 的判断优先于显式转载提示，使来源规范化可重复执行且结果稳定。

### Changed

- 新增内部 `API_RESEARCH_DRAFT_JSON_SCHEMA`；OpenAI Research Pass 只生成研究内容，身份、revision、时间、状态、Fact Check、provenance、quality 和审批字段由程序生成。
- 保持 Research Report / FactCheck Artifact Schema `0.2` 和全部质量阈值不变。
- `research-topic` Skill、报告契约、示例和架构文档同步 hardened 规则。

### Validation

- 85 项自动测试全部通过，原 68 项继续通过，新增独立来源、API 字段所有权、质量指标和 Fact Check 归组回归测试。
- 三类真实公开题材重新运行：稳定商业与争议公共政策进入 `reviewed`；快速公共安全热点因未解决高风险信息保持 `draft`。
- sample、validate、prepare-draft、review-report、迁移、修订防覆盖、Skill、Python 3.9、干净安装和密钥扫描完成验证。

### Security

- 模型无法通过 API Research payload 伪造 quality summary 或 approval 状态。
- 完整真实评测报告继续只保存在 gitignored `reports/`，公开仓库仅保存去内容化汇总。

## [0.2.0] - 2026-08-10

### Added

- 新增 Research Report 0.2：稳定 `report_id`、修订号、生成元数据、研究模式、更正历史、风险字段、质量摘要和人工确认 Gate。
- 新增正式 Evidence Ledger，区分来源对主张的支持、反驳、归属和背景关系。
- 新增 OpenAI Responses API 搜索调用、完整 action sources 与 URL citation provenance 提取和来源匹配。
- 新增独立版本化 FactCheck Artifact、第二次搜索、反证记录和高风险主张自动队列。
- 新增来源 URL 规范化、追踪参数清理、重复页面、同发布者和疑似转载分组。
- 新增透明质量指标和 Gate，包括来源覆盖、独立来源、高风险核查、来源类型、重复转载、无来源归属和 provenance 匹配。
- 新增不可覆盖的 r1/r2 报告历史、独立核查工件保存和更正记录。
- 新增 Research Report 0.1 → 0.2 确定性迁移与兼容读取。
- 新增 V0.2 Codex Draft 示例、真实编辑评测方法和三类题材的去内容化汇总。

### Changed

- `research-topic` Skill 改为 Research Draft → 新检索 Fact Check → Quality Gate 的两阶段流程。
- 所有构建、API、Skill、迁移和复核入口统一执行完整嵌套 Schema 与业务规则校验。
- 报告输出路径加入主题、报告 ID 和修订号，避免同名报告静默覆盖。
- OpenAI API 自动研究改为两个独立调用，并请求完整搜索来源元数据。
- 示例报告、README、PRD、ROADMAP、AGENTS、架构和 HANDOFF 同步到 V0.2。

### Validation

- 68 项自动测试全部通过，覆盖完整 Schema、错误输入、API Schema 兼容、provenance、Fact Check、人工确认 Gate、来源去重、修订和迁移。
- 三类真实公开题材完成端到端评测：两份通过并停在 `reviewed`，一份高风险动态热点按预期被 Gate 拦在 `draft`。
- 官方 Skill Creator 校验通过；离线示例、迁移、修订安全和干净虚拟环境安装检查通过。

### Security

- 完整真实 Research Report 和 FactCheck Artifact 继续只保存在被 Git 忽略的 `reports/`。
- 无法对应真实工具 provenance 的来源会降级，不能默认为已检查或支撑 confirmed fact。
- 任何报告都不会自动进入未来 Script Agent；通过质量 Gate 后仍需用户明确确认。

## [0.1.0] - 2026-08-10

### Changed

- GitHub 仓库 `HWang0310/deep-talk-studio` 已改为公有，便于 ChatGPT 直接进行产品与架构 Review。
- 新增正式版本的 GitHub Release 与未来软件包发布规则。
- 已发布首个正式版本：[DeepTalk Studio V0.1.0](https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.1.0)。

### Added

- 初始化 DeepTalk Studio 独立 Git 项目。
- 新增仓库级 `research-topic` Codex Skill 和报告契约参考。
- 新增 Research Report 0.1 数据模型、JSON Schema 和交叉引用校验。
- 新增事实、报道、当事方说法、评论和未证实信息的分类。
- 新增时间线、多方观点、冲突、未决问题、内容角度和 Script Agent 交接结构。
- 新增 Markdown 渲染与按日期保存的 Markdown/JSON 双格式报告。
- 新增不依赖安装的 `scripts/deeptalk` 命令行入口。
- 新增 OpenAI Responses API `web_search` 可选提供器，支持结构化输出且不保存密钥。
- 新增虚构示例报告和 15 项自动测试。
- 新增 README、PRD、ROADMAP、AGENTS、HANDOFF、架构、设计和实施计划文档。

### Security

- 默认忽略真实研究报告、环境变量文件、缓存和本地虚拟环境。
- API 错误对外只显示状态与可操作信息，不回显密钥。
