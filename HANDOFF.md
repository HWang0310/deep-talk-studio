# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.6.1

本轮：Real E2E Preview Hardening，开发分支 `agent/real-e2e-preview-hardening`。没有 tag，没有新 Release。

## 1. 本轮任务是什么

根据 ChatGPT 对第一轮真实 E2E Motion Preview 的 Review，仅修复 Diagram 长中文与 edge label 可读性、Comparison 错误标题与强制左右栏，并把此前 timeline safe-area 修复正式提交到 GitHub development branch。使用同一 reviewed Script、approved Research 和 reviewed Material Package 重新生成不可覆盖的真实 Production，不进入 Audio Alignment 等下一阶段。

## 2. 完成了什么

- Timeline：两端 marker、日期与事件文字统一进入安全区。
- Diagram：4 个真实中文节点使用 360×170 node box 和安全换行容器；edge label 使用独立不透明背景 plate 和固定上方 offset，不再与线重叠。
- Core 新增长度容量 Gate：diagram node/edge、comparison label/fact 超出固定容量时在 renderer 前失败，不截断、不缩写、不改写 approved text。
- Comparison：Planner 不再生成“两个解释”，改为受控中性标题“要点对照”；SAFE、SB-53、NASA 分别成为独立 card，机制名只显示一次，两条 grounded fact 保存在同卡。
- Display Text：仅增加固定 allowlist 短语“要点对照”；任意事实文本仍无法声明为 `machine_editorial`。
- Remotion 与 HyperFrames 保持同一 Production Plan / payload 语义，renderer 不重新解释 Research。
- 使用完全相同的正式输入生成新 Production `PROD-20260813T133848055707`，旧 preview 保留未覆盖。

## 3. 创建 / 修改了哪些重要文件

- Core：`production_planner.py`、`production_validation.py`。
- Renderer：Remotion `ProductionComposition.tsx`、HyperFrames adapter。
- Regression：Production planner、validation、renderer 三组测试。
- 设计与计划：`docs/superpowers/specs/2026-08-13-real-e2e-preview-hardening-design.md`、`docs/superpowers/plans/2026-08-13-real-e2e-preview-hardening.md`。
- 契约与记录：Production Contract/Evals、两套 adapter 文档、CHANGELOG、ROADMAP、HANDOFF。
- ignored runtime：新 Production Plan、Project、8 个 MP4 clips、rough preview、hero still、Manifest、QA。

## 4. 当前架构是什么

```text
same approved Research + reviewed Script + reviewed Material Package
→ canonical input/binding Gate
→ Core scene_payload + Display Text + layout capacity Gate
→ single selected Remotion renderer
→ real project validation + preview + render
→ ffprobe + byte/SHA/source binding Manifest
→ Production QA
→ human frame review
```

Comparison/Diagram 的事实和 binding 由 Core 独占；两个 renderer 只消费统一布局语义。

## 5. 已经可以运行什么

- 2–6 项 comparison 生成最多三列的独立 mechanism cards，每项保留 label 与两条 grounded facts。
- 最多 6 个 diagram nodes 使用安全换行；edge label 与连接线通过背景 plate 分离。
- 超过布局容量的长文本 fail closed，不生成视觉溢出的项目。
- 对同一正式内容创建不可覆盖 Production revision，并完整执行 validation、preview、render、ffprobe、Manifest 和 QA。

## 6. 还不能运行什么

- 不含真人 A-roll、真实音频时间码、字幕、BGM/SFX、标题封面或平台发布。
- 5 个 reference-only 来源仍不会进入成片，只保留真人口播占位。
- 本轮没有实现 Audio Alignment + Edit Bridge。

## 7. 已知问题

- 新 Production 仍诚实记录 6 个 gap：5 个 reference-only 画面位，1 个真实语音时间码。
- rough preview 只验证辅助画面，不代表最终真人视频节奏。
- 空 Remotion 模板在未注入 plan/profile/asset-map 前不能独立 typecheck；真实新 Production 注入文件后 lint、typecheck、compositions 全部通过。

## 8. 重要技术决策

- 不把真实三项机制强行解释为左右阵营；沿用 payload 的 label/left/right 字段，但 renderer 将其解释为一个 card 的标题和两条事实。
- 保留“两个解释”仅用于已存在历史工件的 allowlist 兼容，Planner 不再生成；新中性短语“要点对照”受同一白名单约束。
- capacity Gate 使用确定性 East Asian width 单位，避免依赖浏览器测量；安全优先于自动缩小到不可读字号。
- 不修改 Script、Research 或 Material；新旧 Plan 的 Script digest 与 Material digest 完全相同。
- 不创建 v0.6.2，正式 Release 仍为 v0.6.1。

## 9. 哪些问题需要产品经理决定

- 请 Review 用户观看的新 Motion rough preview，确认 Diagram 与 Comparison 两个视觉问题是否通过。
- 用户确认“预览通过”后，正式安排 Audio Alignment + Edit Bridge；本轮不要回溯扩展范围。

## 10. 建议下一阶段做什么

等待用户完成一次普通审美确认。若通过，由 ChatGPT 给出 Audio Alignment + Edit Bridge 的正式产品规格：把真人录音时间码绑定 Script Beat、Material Cue 与 Motion Scene，减少剪辑软件中的人工定位。

## 验证结果

- TDD red：新回归最初准确失败于“两个解释”、无 layout capacity Gate、旧左右栏、单行 diagram 与无 label plate。
- 定向 Production 回归：36 项通过。
- 完整项目：272 项；271 项执行通过，1 项真实双 renderer integration 按默认规则跳过。
- 真实 Remotion project：environment、npm ci、lint、typecheck、compositions、Studio preview 六项 checks 全部 pass。
- 新 Production：8 clips + 1 rough preview + 1 hero still，10 个工件全部 ready；Production QA pass，0 issue。
- rough preview：H.264、1920×1080、30 fps、74.048 秒，SHA-256 `fe14987736b3f676d81f24124d3feae15a3640d86e13c8a199f6cdffb3140544`。
- 人工画面检查：timeline 两端在 safe area；4 个 diagram node text 在 box 内，3 个 edge label plate 与线分离；comparison 标题为“要点对照”，三张 mechanism card 一眼可分，每张两条事实完整。
- 权利复验：renderer asset map 为空；7 个外部来源仍为 reference_only，没有任何来源页面或截图进入项目。

## 给用户的下一步操作

现在只需观看新 rough preview。满意回复“预览通过”；不满意直接指出具体画面。Codex 聊天回复会直接附完整的 ChatGPT 交接文字，不需要用户来本文件复制。
