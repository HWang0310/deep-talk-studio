# Real E2E Preview Hardening Design

## Scope

本轮只修复第一轮真实 E2E Motion rough preview 暴露的 timeline、diagram 与 comparison 可读性问题。输入固定为同一份 reviewed Script、approved Research 与 reviewed Material Package；不修改内容工件，不进入音频、字幕、音乐、封面或发布。

## Layout contract

- Timeline 保留现有 payload 语义，两端 marker、日期与事件文字统一进入 1920×1080 safe area。
- Diagram 仍由 Python Core 的 ordered nodes / edges / grounded Display Text 驱动。Renderer 使用固定 node box、CSS 安全换行和 overflow clipping；Core 对超过确定性容量的文字 fail closed。Edge line 与 label plate 分层，label plate 使用不透明背景并固定偏移，不把 label 压在线上。
- Comparison 不再解释成匿名左右阵营。每个 payload item 是一个独立 card：mechanism label 只显示一次，`left_text` 与 `right_text` 作为同一卡片的两个 grounded fact block。2–6 个 item 采用最多三列的确定性 grid。
- Comparison heading 使用版本化 machine-editorial 中性短语“要点对照”。旧短语仅为历史工件兼容保留，Planner 不再生成“两个解释”。任意事实文本仍不能伪装成 machine editorial。
- Remotion 与 HyperFrames 消费同一份 Production Plan 和 comparison/diagram payload，不改变、缩写或重新解释 Research 文本。

## Failure behavior

Planner 在 renderer 前检查 diagram node、diagram edge、comparison label 与 comparison fact 的显示容量。超出容量时抛出 ProductionValidationError；不截断、不省略、不自动改写事实文本。

## Verification

- 使用真实中文长 node/edge label 做 regression，检查安全换行、overflow containment 与 edge label plate。
- 使用 3 个 comparison items 做 regression，检查中性 heading、label 单次出现、两个 grounded fact binding 保留和 machine-editorial allowlist 不被放宽。
- 使用同一真实 Trial 输入创建新的 immutable Production 输出，执行 Remotion validation、preview、real render、ffprobe、Manifest、QA、SHA/binding 与人工逐帧检查。
- 旧 Production 工件保留；正式 Release 保持 v0.6.1。
