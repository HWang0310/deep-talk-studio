# Production Contract 0.6.1

## 范围

V0.6 将已审查 Material Package 转换为辅助动画、粗剪视觉预览和定帧图。它不生成假主播、TTS、最终口播剪辑、字幕、BGM、标题封面或发布任务。

## Canonical Input Gate

1. 使用 V0.5.1 `load_material_package` 重放 r1 input/inspection/rights → Review → r2。
2. 只允许 `reviewed` 和 `reviewed_with_warnings`。`blocked`、`draft`、`research_update_required`、伪造 Review 或错版 Script/Research 在 Renderer 前拒绝。
3. Production Plan 绑定 Script digest、Material digest/revision/Review ID、Profile version 和精确来源 ID。

## Asset Gate

每次制作都重新检查 allowed root、路径越界、文件存在、真实扩展/MIME、byte size、SHA-256、generated render status 和 eligibility。只有 `ready_to_use` 可 stage。reference-only、permission-required、rejected、missing 或 tampered asset 必须使用原创 Visual、A-roll placeholder 或 Production gap。

## Display Text Gate

- 只有版本化 `machine_editorial` 白名单短语可不绑定；“无数字”不再等于 editorial。
- research fact/attribution、material caption 和 visual label 都必须绑定有效 Claim/Evidence，且显示文字语义能从绑定内容确定性回查；无关 Claim ID 无效。
- Research Claim 未逐字包含的 timeline 日期，只有在 date/event/Claim/Evidence 与 approved Research Timeline 精确一致时可使用。
- 任何 unsupported new number/date 在 project 生成前失败关闭。

## Production Plan 0.6.1

Plan 由程序生成 `production_id`、Scene ID、Motion Asset ID、frame duration 和 digest。Scene 支持：

- `timeline_motion`、`bar_motion`、`comparison_motion`、`diagram_motion`；
- `document_reveal`、`screenshot_pan`、`image_pan_zoom`；
- `aroll_placeholder`。

Plan 同时记录 source IDs、屏幕文字 grounding、layout/motion/transition intent、预期 clips、rough preview、hero still 和明确 gaps。当前时长来自 Material 建议值，没有真实语音时码时必须保留 gap。

每个 Scene 还包含唯一 `scene_payload`。Python Core 拥有数据、顺序、文字和 binding；Remotion/HyperFrames 只按 payload 动画。timeline 是 baseline → ordered marker → date/event，bar 从共同 baseline 逐根增长，comparison 按左右与条目建立，diagram 先 node 后 endpoint 已存在的 edge/label。V0.5 SVG 只可作为静态 fallback/debug。

## PDF / Capture Boundary

raw PDF 只保留 provenance，不能 stage，也不能进入 CanvasImage/img。Production 只消费 V0.5 已登记并通过 Review 的 PNG/JPEG/WebP capture。没有 capture 时使用固定 gap：“文件已取得，但尚无可安全展示的页面截图。”

## Renderer Architecture

Remotion 与 HyperFrames 不是两个独立系统。它们共用 Production Plan、Production Profile、asset staging、Manifest 和 QA，只有 project/preview/render 实现不同。普通流程只实例化 `selected_renderer`；双引擎只用于明确 cross-renderer 评测。

## Manifest 与 QA

Renderer 返回命令成功不代表 asset ready。environment/install/lint/typecheck/compositions/doctor/validate/inspect/preview 均保存为 typed check。Core 从 fail check 确定性生成 blocking issue，再推导 Gate；调用方不能传第二份 package failure 清单。Manifest 只登记真实存在且通过 ffprobe 的文件，包括 format、dimensions、fps、duration、size、SHA、source binding、plan digest 和脱敏 command summary。

## Immutable Storage

- `production_packages/YYYY/MM/DD/production_id/`：Plan、Manifest、QA。
- `production_assets/production_id/assets/`：MP4/PNG。
- `production_projects/production_id/renderer/`：可复查的 renderer project。

三类目录均 gitignored，已存在路径拒绝覆盖。
