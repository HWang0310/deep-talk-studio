# DeepTalk Studio 开发交接

当前版本：V0.6.1 / `0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.6.1

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.6.0 的完整 Review，完成 **V0.6.1 Motion Semantics & Production Gate Hardening**。本轮只收口 V0.6，不进入 V0.7，重点是四类真正 Motion、非数字 Display Text grounding、Production QA check→issue→gate、PDF/document boundary 和可公开复验的真实渲染证据。

## 2. 完成了什么

- timeline：baseline 先建立，marker 按 order 出现，日期和事件文字跟随对应 marker。
- bar：每根柱从共同 baseline 独立增长，label/value 随后出现并保持稳定 stagger。
- comparison：左右区域和每个 item 独立建立，不再把完整 SVG 当作一个对象。
- diagram：node 按逻辑顺序出现；edge 只在两个 endpoint 后出现，edge label 与 edge 同步。
- Production Plan 升级到 0.6.1，每个 Scene 带严格 `scene_payload`；Python Core 拥有数据、顺序、文字和 binding，两套 renderer 只动画。
- V0.5 SVG 仅保留静态 fallback/debug 身份，四类 Motion 不再 stage 该 SVG。
- Display Text 新增确定性 origin；只有固定机器短语可不绑定，所有事实文字即使没有数字也必须能语义回查相关 Claim/Evidence。
- 无数字虚假断言、合法但无关 Claim、无对应 Claim 的因果 edge、虚假 material caption 均被拒绝或安全降级。
- renderer 外部命令统一成 typed check；环境、验证或预览失败会自动生成 package blocker，无法与 pass Gate 共存。
- raw PDF 永不进入 CanvasImage/img；只有 V0.5 已登记并审查的 PNG/JPEG/WebP capture 可运动。没有 capture 时返回固定 gap。
- rough preview 只有 MAPREVIEW 真正在 Manifest 中 ready 时才宣称成功。
- 命令摘要会脱敏本机路径、用户目录和局域网预览地址。
- 生成了完全虚构的 36/64/88 三柱公开 Motion Evidence，两套真实 MP4 均通过 QA，并带 contact sheet、ffprobe 和 SHA。

## 3. 创建 / 修改了哪些重要文件

- Core：`production_schema.py`、`production_planner.py`、`production_validation.py`、`production_qa.py`、`production_workflow.py`。
- Renderer：`production_renderers/base.py`、`remotion.py`、`hyperframes.py`、两套锁定模板与 lockfile。
- Evidence：`scripts/build_v061_motion_evidence.py`、`evaluations/v0.6.1-summary.json`。
- 契约：`docs/PRODUCTION_CONTRACT.md`、`docs/PRODUCTION_EVALS.md`、`docs/REMOTION_ADAPTER.md`、`docs/HYPERFRAMES_ADAPTER.md`。
- 版本文档：`README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`CHANGELOG.md`、`docs/releases/v0.6.1.md`。
- 测试：Production planner、validation、renderer、QA、workflow 和真实 integration 测试。

## 4. 当前架构是什么

```text
V0.5.1 canonical reviewed Material Package
→ Python Core 事实/权利/asset/display-text Gate
→ Production Plan 0.6.1 + strict scene_payload
→ 单一 selected renderer（Remotion 或 HyperFrames）
→ typed command checks + real render outputs
→ Motion Asset Manifest（ffprobe / size / SHA / binding）
→ Core-derived issues
→ Production QA package Gate
→ 普通中文 summary
```

正常用户流程只运行一个 renderer。双引擎只用于正式兼容评测，并使用同一份 payload。

## 5. 已经可以运行什么

- 从 canonical reviewed Material Package 生成不可覆盖 Production Plan。
- 用 Remotion 或 HyperFrames 生成 timeline/bar/comparison/diagram 的真正逐元素 MP4。
- 对已审页面截图和静态图片做轻推、平移和可选区域高亮。
- 生成独立 Motion Clips、rough visual preview、hero still、Manifest 和 Production QA。
- 在环境/验证/预览失败时 fail closed，同时保留已成功独立 clip 的真实状态。
- 执行 A–G 评测和公开 synthetic evidence 生成器。

## 6. 还不能运行什么

- 不含真人 A-roll 的最终成片。
- 不做字幕、BGM、SFX、最终剪辑、标题、封面或平台发布。
- 不做 TTS、用户声音克隆或真实音频时间码对齐。
- raw PDF 不能直接展示；必须先在 V0.5 流程登记安全页面截图。
- 不执行 OCR，也不从截图推导新事实。

## 7. 已知问题

- Remotion H.264 输出含一个静音音轨，因此 ffprobe 可见第二个无视频尺寸的 stream；QA 正确使用第一个视频流，MP4 可正常使用。
- HyperFrames 0.7.106 会提示 `validate` / `inspect` 未来改名为 `check`，当前命令仍返回 0 且完整通过。本版按 Review 要求继续保留独立 typed checks，后续升级依赖时再迁移。
- HyperFrames doctor 在本机提示 Docker 不存在，但 doctor 自身 exit 0；Docker 不是当前浏览器 MP4 渲染的必需条件。
- placement anchor 仍是口播原句，不是真实音频时间码；Plan 会保留这个 gap。

## 8. 重要技术决策

- 选择结构化 scene payload，而不是让两个 renderer 各自解析 SVG，避免事实和顺序漂移。
- 只有版本化 core phrase allowlist 可不绑定；其他文字默认绑定并做保守 substring 语义证明，不引入复杂 NLP。
- QA 不再接受调用方单独传 package failures；Core 只从 typed checks 和真实 Manifest 推导问题。
- raw PDF 保持 provenance-only；不在 V0.6.1 内新增 PDF rasterizer，继续消费 V0.5 capture，边界更简单可审计。
- HyperFrames 多场景使用新 scene 覆盖式入场，不给旧 scene 添加提前 exit 动画。
- 公开证据仅使用虚构数据，视频作为 Release asset，不把真实用户内容或受版权素材提交 Git。

## 9. 哪些问题需要产品经理决定

- 请正式判断 V0.6 是否通过验收。
- 若通过，请直接安排第一轮真实用户端到端试用，再根据真实阻塞决定 V1.0 前优先补音频对齐、字幕、编辑计划还是发布辅助。
- 本轮没有要求用户做技术选择，也不建议在 Review 前提前开发 V0.7。

## 10. 建议下一阶段做什么

正式验收 V0.6 后，用一个权利边界清楚的真实主题跑完整链路：Topic/Research → Script → Material → Motion。记录普通用户需要确认的次数、失败恢复方式、真实剪辑仍需手工完成的部分，再由 ChatGPT 判断距离 V1.0 还缺什么。

## 验证结果

- 常规 unittest：267 total，266 executed pass，1 个真实渲染 integration 默认跳过；V0.6.0 的 255 项基线全部保留。
- 显式真实 cross-renderer integration：1 passed。
- 同一 3 元素 synthetic bar Plan：Remotion 4.0.507 与 HyperFrames 0.7.106 都完成 install、validation、preview、real MP4 render、ffprobe、SHA、Manifest 和 QA pass。
- Motion Evidence：Remotion clip SHA `7cb45c99a801c3e5535a267e5e1c15e14065267514711fe14975f7f6f4114abd`；HyperFrames clip SHA `33e9cc4650a094d0c620ce9558cc3cc1d7ddd3f8754f3d7582fcf616a6f65dd5`。
- Python 3.9 compile/install、JSON、lockfile、secret、git tree、Release tag target 在发布前完成复验。

## 给用户的下一步操作

下一步只需要把下面整段原样发给 ChatGPT，不需要自己总结：

“这是 Codex 完成的 DeepTalk Studio V0.6.1
Motion Semantics & Production Gate Hardening。

GitHub 仓库是
https://github.com/HWang0310/deep-talk-studio ，

Release 是
https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.6.1 。

请 Review 四类真正 Motion semantics、
Display Text 非数字事实 Grounding、
Production QA check→issue→gate、
PDF/document boundary、
Remotion / HyperFrames 真实 render、
rough preview、测试和 synthetic motion evidence。

如果通过，请正式验收 V0.6，
并直接带我进入第一轮真实用户端到端试用，
然后判断距离 V1.0 还缺什么。

不要让我自己总结。”
