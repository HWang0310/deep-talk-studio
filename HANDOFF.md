# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

本轮：Audio Alignment + Visual Edit Bridge Design Review Candidate，保持 Unreleased。

## 1. 本轮任务是什么

从已通过 Review 的 `agent/real-e2e-preview-hardening-mainline` HEAD `f087b6c295a9e015357e4433b103428b16a5e6be` 建立 `agent/audio-alignment-edit-bridge`，检查现有 Script、Material、Production、Schema、Storage、renderer、Skill 与 eval 边界，只完成新阶段 Design Spec、自审、提交和推送。

本轮明确不写 implementation plan、不开发、不运行 transcription、不渲染 Aligned Preview、不创建 Release。

## 2. 完成了什么

- 定义 Clean A-roll 是 immutable canonical timeline；视频默认支持 MP4/MOV/M4V，纯音频作为无完整 Preview 的兼容路径。
- 定义 Narration Media、lossless Extracted Audio、Timed Transcript、Script Alignment、Beat/Cue Timeline、Visual Placement、Edit Bridge、Preview Manifest 与 QA 的版本化边界。
- 设计 provider-neutral transcription adapter：确定性测试 provider + 可配置真实 provider；provider/LLM 都不能决定 canonical timecode、status 或 Gate。
- 设计 span-preserving 中文/英文 normalization、确定性动态规划、歧义/漏读/即兴/重排检测和版本化 Profile/threshold。
- 复用 Script Beat → Material Cue → Production Scene 身份，不建立第二套 Scene。
- 将 A-roll、真实图片/截图、真实视频和 QA-ready Motion 纳入统一 placement model，自动推导 IN/OUT/duration 与默认 layout。
- 分开真实视频的 narration timeline 与 source clip timeline；无 clip range 时保留插入位置并诚实标记 `clip_selection_needed`。
- 定义 Motion/视频 duration conflict 与 overlap；Preview 允许确定性临时裁切，但不改源文件或 canonical decision。
- 定义 JSON、普通中文 Markdown、NLE-neutral CSV 和 1920×1080/30fps `ALIGNED_PREVIEW.mp4`。
- 明确历史 rights/reuse 继续兼容读取但不再阻塞新制作；缺文件、SHA/MIME/codec/path/grounding/binding 问题仍严格失败。
- 覆盖产品要求的 A–Z adversarial cases、partial recovery、immutable revision 和真实真人视频 E2E 边界。

## 3. 创建 / 修改的重要文件

- Design Spec：`docs/superpowers/specs/2026-08-13-audio-alignment-edit-bridge-design.md`
- 项目状态：`AGENTS.md`、`PRD.md`、`ROADMAP.md`、`CHANGELOG.md`
- 本交接：`HANDOFF.md`

没有修改 Python、renderer templates、schemas、tests、Skills 或 runtime artifacts。

## 4. 当前设计架构

```text
Clean A-roll → immutable Media + lossless audio derivative
→ provider-neutral Timed Transcript
→ deterministic Script sequence alignment
→ stable Beat timeline → Cue anchor timeline
→ existing Production Scene + material compatibility projection
→ unified Visual Placement (A-roll / real image / real video / motion)
→ Edit Bridge JSON + Markdown + CSV
→ Remotion Aligned Preview
→ ffprobe/SHA/binding Alignment + Edit Bridge QA
```

所有 canonical 秒数只来自 provider 真实 timestamp boundary 和 deterministic mapping。segment-only 不插值词级时间，降级为 coarse。

## 5. 已经可以运行什么

仍然可以运行此前已验收的 Topic Discovery → Research → Script → Material → Motion Production。Design 文档可供 ChatGPT 完整 Review。

本轮没有新增可运行产品能力。

## 6. 还不能运行什么

- 不能导入/转录 Clean A-roll；
- 不能生成 Beat/Cue 真实时间码；
- 不能生成 Edit Bridge Package 或 `ALIGNED_PREVIEW.mp4`；
- 没有 Audio Alignment Skill/CLI/provider/renderer；
- 不做自动 A-roll cleanup、字幕、BGM/SFX、NLE 工程导出、标题封面或发布。

## 7. 已知问题与开放风险

- 真实 provider 的模型、SDK 和 timestamp 能力会变化；实现 OpenAI adapter 时必须查询当日官方文档。
- 中文 ASR token boundary 不统一；设计使用自己的可逆 normalization，segment 内不伪造词级精度。
- 历史 rights 与 eligibility 紧耦合；设计用只读 material production projection 拆分 rights 与非 rights Gate，不改旧包。
- 真实 B-roll 常缺内部 clip range；首版不自动猜“最佳几秒”。
- VFR、非零 PTS 和多种音视频编码需要真实媒体 adversarial eval。
- 阈值虽已给出确定值，仍需在 A–Z eval 中校准；若变化必须发布新 Profile，不改写旧工件。

## 8. 重要技术决策

- Clean A-roll 是后续唯一 canonical timeline；任何新剪辑产生全新 Media → Transcript → Alignment → Bridge → Preview 链。
- LLM 只可生成可读 gap 解释，不能生成机器时间码或 Gate。
- 第一版只有 word/token timestamp 可进入精细 Preview；segment-only 保存 coarse 结果但不覆盖 A-roll。
- ready overlay 的 IN 是 anchor 实际说话起点，OUT 来自真实 semantic window，不硬编码五秒。
- 默认 layout：真实图片/视频全屏 B-roll；信息 Motion 全屏；没有视觉时保持真人。
- rights/reuse 完全退出新制作资格 Gate，但不放松获取限制、文件完整性、Research grounding 或 Display Text grounding。
- Preview adjustment 是 rough cut 临时决策，必须记录且不能冒充最终剪辑决定。
- 产品版本仍为 Unreleased；Artifact `*/1` 只是 contract 第一版，不代表达到 V1.0。

## 9. 需要产品经理 Review 的问题

- Artifact、module 和 root binding 是否完整；
- normalization、deterministic alignment、ambiguity 与 threshold 规则是否满足产品精度边界；
- segment-only 不进入首版 Preview 是否符合预期；
- Material rights compatibility projection 是否正确保留非版权 Gate；
- IN/OUT/duration、layout、video source range 与 timing conflict policy 是否适合作为首版；
- QA 的 pass/warnings/fail 与 partial recovery 是否正确；
- A–Z adversarial eval 是否足以进入下一轮 implementation planning。

## 10. 建议下一阶段

等待 ChatGPT Design Review。只有 Review 明确通过并发来新的正式指令后，才创建 TDD implementation plan；当前不要实现 Audio Alignment + Visual Edit Bridge。

## 给用户的下一步操作

用户不需要检查文件或 GitHub。Codex 本轮聊天回复会直接附上完整的 ChatGPT Design Review 交接，用户只需整段复制给 ChatGPT。
