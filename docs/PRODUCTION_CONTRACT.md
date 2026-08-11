# Production Contract 0.6

## 范围

V0.6 将已审查 Material Package 转换为辅助动画、粗剪视觉预览和定帧图。它不生成假主播、TTS、最终口播剪辑、字幕、BGM、标题封面或发布任务。

## Canonical Input Gate

1. 使用 V0.5.1 `load_material_package` 重放 r1 input/inspection/rights → Review → r2。
2. 只允许 `reviewed` 和 `reviewed_with_warnings`。`blocked`、`draft`、`research_update_required`、伪造 Review 或错版 Script/Research 在 Renderer 前拒绝。
3. Production Plan 绑定 Script digest、Material digest/revision/Review ID、Profile version 和精确来源 ID。

## Asset Gate

每次制作都重新检查 allowed root、路径越界、文件存在、真实扩展/MIME、byte size、SHA-256、generated render status 和 eligibility。只有 `ready_to_use` 可 stage。reference-only、permission-required、rejected、missing 或 tampered asset 必须使用原创 Visual、A-roll placeholder 或 Production gap。

## Display Text Gate

- Editorial 标题不得包含事实数字或伪造 Research binding。
- 含数字的标题、bar value、timeline date/label 必须绑定有效 Claim/Evidence。
- Research Claim 未逐字包含的 timeline 日期，只有在 date/event/Claim/Evidence 与 approved Research Timeline 精确一致时可使用。
- 任何 unsupported new number/date 在 project 生成前失败关闭。

## Production Plan 0.6

Plan 由程序生成 `production_id`、Scene ID、Motion Asset ID、frame duration 和 digest。Scene 支持：

- `timeline_motion`、`bar_motion`、`comparison_motion`、`diagram_motion`；
- `document_reveal`、`screenshot_pan`、`image_pan_zoom`；
- `aroll_placeholder`。

Plan 同时记录 source IDs、屏幕文字 grounding、layout/motion/transition intent、预期 clips、rough preview、hero still 和明确 gaps。当前时长来自 Material 建议值，没有真实语音时码时必须保留 gap。

## Renderer Architecture

Remotion 与 HyperFrames 不是两个独立系统。它们共用 Production Plan、Production Profile、asset staging、Manifest 和 QA，只有 project/preview/render 实现不同。普通流程只实例化 `selected_renderer`；双引擎只用于明确 cross-renderer 评测。

## Manifest 与 QA

Renderer 返回命令成功不代表 asset ready。Manifest 只登记真实存在且通过 ffprobe 的文件，包括 format、dimensions、fps、duration、size、SHA、source binding、plan digest 和 command summary。Production QA 从真实 Manifest 推导 clip `ready/failed` 与 package `pass/warnings/fail`；模型不能自报通过。

## Immutable Storage

- `production_packages/YYYY/MM/DD/production_id/`：Plan、Manifest、QA。
- `production_assets/production_id/assets/`：MP4/PNG。
- `production_projects/production_id/renderer/`：可复查的 renderer project。

三类目录均 gitignored，已存在路径拒绝覆盖。
