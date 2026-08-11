# V0.6.1 Production Evals

评测日期：2026-08-11。全部业务内容为虚构或去内容化数据；真实 package/project/output 默认被 Git 忽略，公开 Motion Evidence 随 GitHub Release 提供。

## A. Stable Business Bar

3 个已绑定 data point 形成结构化 payload。Remotion 使用 3 个独立 SVG bar 从共同 baseline stagger 增长；HyperFrames 生成 3 个独立 `.bar-item/.bar-column` 并用 paused GSAP stagger。真实 synthetic 数据为 36/64/88，双引擎 MP4 均为 1920×1080、30 fps、QA pass，不再复制 V0.5 SVG。

## B. Contested Timeline

timeline 只接受与 approved Research Timeline 的 date/event/Claim/Evidence 完全一致的条目，reference-only 新闻不进入 Scene。baseline 先建立，2 个事件按 order 出现，日期和 label 跟随对应 marker；不一致条目在项目生成前拒绝。

## C. Rights Sparse Diagram

3 nodes / 2 edges 由 payload 保存。新闻素材保持 reference-only；node 按逻辑顺序出现，edge 只在两个 endpoint 出现之后建立。没有对应 causal Claim 的“A 导致 B”不能作为 edge label。

## D. Comparison

至少 2 个 comparison item 分别保存 label/left/right/binding。两个 renderer 都生成独立左右区域和条目动画，不使用整图 reveal。

## E. PDF / Capture

raw PDF 即使路径、大小、SHA 和 MIME 正确也不能进入 renderer；无 capture 时生成固定 gap。V0.5 已登记页码、区域、上下文且通过 Review 的 PNG/JPEG/WebP capture 可进入 image payload，使用轻推/平移/高亮，不做 OCR。

## F. QA Contradiction

在 Manifest 已有真实文件时强制 typecheck 或 preview fail，Core 仍生成 `renderer_validation_failed` / `renderer_preview_failed` package blocker，Gate = fail。删除该 issue 或手改 Gate 会被 validator 拒绝。

## G. Display Text Semantic Bypass

“公司已经承认全部责任”、无关合法 C1、“A 导致 B”无 causal Claim、“监管机构认定违法”虚假 caption 均被拒绝或安全降级；“关键时间点”“真人口播”等固定机器短语可不绑定。

## Cross-renderer Real Evidence

同一份 3 元素 synthetic bar Plan 完整运行：

| Renderer | Clip SHA-256 | 尺寸 / fps | 时长 | QA |
|---|---|---|---:|---|
| Remotion 4.0.507 | `7cb45c99a801c3e5535a267e5e1c15e14065267514711fe14975f7f6f4114abd` | 1920×1080 / 30 | 3.050667 s | pass |
| HyperFrames 0.7.106 | `33e9cc4650a094d0c620ce9558cc3cc1d7ddd3f8754f3d7582fcf616a6f65dd5` | 1920×1080 / 30 | 3.000000 s | pass |

Release assets 包含两份 MP4、三帧 contact sheet 和 `evidence-summary.json`。生成器为 `scripts/build_v061_motion_evidence.py`。

## Tests

- 常规 unittest：267 total，266 executed pass，1 skipped real-render test；V0.6.0 的 255 项基线全部保留。
- 显式真实渲染：cross-renderer integration 1 passed；synthetic 3-bar evidence 双引擎完整命令链通过。
- Remotion：npm ci、eslint、tsc、compositions、Studio preview、render/still、ffprobe。
- HyperFrames：npm ci、doctor、lint、validate、inspect、preview/status/stop、render、ffprobe。
