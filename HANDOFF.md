# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

本轮：Audio Alignment + Visual Edit Bridge Implementation Planning，保持 Unreleased。

## 1. 本轮任务是什么

ChatGPT 已将 Design HEAD `993daf5a89862a827d72d3949c8c05a1b93a391b` 正式评为 DESIGN PASS / Approved / Implementation-Planning Ready。本轮只允许在 `agent/audio-alignment-edit-bridge` 编写完整 Implementation Plan 和必要状态文档，不得修改 `src/`、renderer implementation、Skill 行为或运行真实 transcription/render。

## 2. 完成了什么

- 完整复核 approved Design、AGENTS/PRD/ROADMAP、现有 Script/Material/Production schema、storage、validation、workflow、provider、renderer、CLI、Skill、eval 和 runtime roots。
- 新增 28 个按依赖顺序执行的正式 TDD Tasks；每个实现 Task 都有准确 Create/Modify/Test 文件、consumes/produces interface、先失败测试、红/绿命令、预期结果和独立 commit 边界。
- 明确拆分媒体导入、真实媒体 fixture、音频提取、Timestamp Mapping、转录、Timed Transcript、Normalization、Sequence Alignment、Profile calibration、Beat/Cue timeline、Material Projection、Placement、Duration/Conflict、Bridge Outputs、Revision、Preview、Audio mux、QA、Workflow、CLI/Skill 与最终 eval。
- 只查询 OpenAI 官方文档，固定 Planning 当日的真实 Speech-to-Text capability boundary；没有调用 API。

## 3. 创建 / 修改的重要文件

- 新增：`docs/superpowers/plans/2026-08-13-audio-alignment-edit-bridge.md`
- 状态同步：`AGENTS.md`、`PRD.md`、`ROADMAP.md`、`CHANGELOG.md`、`HANDOFF.md`

没有修改 `src/`、`tests/`、`renderer_templates/`、`scripts/`、`.agents/skills/`、配置或 runtime 工件。

## 4. 当前计划架构

```text
Clean A-roll import + ffprobe evidence
→ lossless extracted audio + Timestamp Mapping
→ provider-neutral Timed Transcript
→ span-preserving normalization + deterministic DP
→ Beat/Cue Timeline + calibrated Profile
→ Material production projection + existing Motion
→ unified Visual Placement + IN/OUT/duration/conflicts
→ Edit Bridge JSON/Markdown/CSV
→ Remotion visual render + Clean A-roll audio mux
→ Preview Manifest + Alignment/Edit Bridge QA
→ ordinary-user Skill → real-user E2E Gate
```

## 5. 已经可以运行什么

现有 Topic → Research → Script → Material → Motion 正式流程保持可运行。本轮新增的是可交给未来 Codex 逐 Task 执行的工程计划，不新增产品 runtime 能力。

## 6. 还不能运行什么

- 尚不能导入、提取或转录 Clean A-roll；
- 尚不能生成 Timestamp Mapping、Alignment、Edit Bridge 或 Aligned Preview；
- 尚未执行真实 provider smoke 或真实用户 E2E；
- 不做自动剪口气、字幕、BGM/SFX、标题封面、NLE 专属工程或发布。

## 7. OpenAI provider 计划边界

2026-08-13 查阅官方 Speech-to-Text guide 与 Transcriptions API：Python SDK 使用 `client.audio.transcriptions.create`；文件转录 guide 上限 25 MB；当前 endpoint 列出 `gpt-transcribe`、`gpt-4o-transcribe`、`gpt-4o-mini-transcribe`、`gpt-4o-mini-transcribe-2025-12-15`、`whisper-1` 和 diarize 模型；官方 guide 明确 `timestamp_granularities` 仅由 `whisper-1` 支持，word timestamp 要求 `verbose_json`。因此 Plan 使用 `whisper-1` word timestamps 作为首版真实 adapter；任何 segment-only 返回都降为 coarse，不伪造精度。

## 8. 测试与自审

- Planning 前完整项目基线：272 tests，271 pass，1 个显式真实渲染测试按预期 skip。
- Plan 逐条覆盖 approved Design §§1–32 和 A–AI；所有 28 Tasks 按依赖排序。
- Placeholder、接口、TDD、范围、真实 E2E Gate 和产品代码 diff 均在提交前重新核验。
- Planning 不运行真实 transcription、Aligned Preview render 或真实用户 E2E。

## 9. 已知风险与重要决定

- Timestamp Mapping 与真实媒体 fixture 单独成 Task，避免以手写 JSON 代替 PTS/AAC/edit-list 证明。
- 长稿 DP 优化必须与 full-matrix reference 输出等价，不能换 heuristic。
- Design 阈值先作为 Candidate Profile，通过关键 false-precision cases 后才标 accepted；变更必须形成新 Profile value revision 和 evidence。
- OpenAI 真实 smoke 是 implementation 后的独立 Gate；API/网络环境失败与产品验证失败分开记录。
- synthetic、真实媒体 fixture 与 provider smoke 都不能代替用户真实 Clean A-roll 验收。

## 10. 产品经理需要决定什么

本轮没有新的产品选择。请 ChatGPT 只 Review Implementation Plan 是否完整、Task 边界是否合适、依赖/接口/TDD/Gate 是否符合 approved Design，并另行决定是否授权进入 implementation。

## 11. 建议下一阶段

等待 ChatGPT Implementation Plan Review。只有收到明确 implementation 指令后，才按 Plan Task 1 开始 TDD；不得自行继续开发。

## 给用户的下一步操作

用户不需要阅读 Plan、找文件或选择执行方式。Codex 聊天回复会在最末尾附完整交接，用户只需整段复制给 ChatGPT。
