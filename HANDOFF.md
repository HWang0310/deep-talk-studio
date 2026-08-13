# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

本轮：Audio Alignment + Visual Edit Bridge Implementation Plan Hardening，保持 Unreleased。

## 1. 本轮任务是什么

ChatGPT 对 Planning HEAD `aa23b446e04302837c8632fc8851f7b61e39fa2a` 给出 IMPLEMENTATION PLAN — CONDITIONAL PASS。本轮只修正两个 Plan blocker：大文件 transcription 不能在句中任意硬切；Aligned Preview audio 必须保持原 Clean A-roll presentation timing。不得开始 Task 1 或修改产品代码、renderer、Skill。

## 2. 完成了什么

- 新增独立 Task 7 `transcription-chunk-profile/1`，并将 Provider protocol 顺延为 Task 8，保证 Chunk Plan 先于其消费者实现；总 Task 数从 28 调整为 29。
- 大文件仍遵守 25 MB provider limit，request cap 为 24 MiB；nominal boundary 前 12 秒内用 20 ms RMS / 10 ms hop 搜索持续至少 300 ms、≤ -42 dBFS 的自然停顿。
- 候选采用确定性 score/tie-break；能量 threshold 使用整数 mean-square 比较，避免浮点差异移动边界。无安全停顿时在 10 ms 网格上比较完整 300 ms 区间的 nearest-rank p95 能量，选择同窗口最低能量 valley，标记 high boundary risk，并生成前后各 1 秒 risk guard。
- Chunk 保存 index、samples、sample rate、extracted/media seconds、boundary evidence、Profile/chunk digest；不重叠、不删停顿、不修改 A-roll，也不依赖 LLM/Transcript。
- boundary risk 贯穿 Provider Transcript → Timed Transcript → Alignment → Bridge → QA；风险区 duplicate/omission/anchor 异常不得生成 false high-confidence ready。
- Preview audio mux 改为消费 Clean A-roll media presentation evidence；正 audio offset、normalized raw PTS、internal gap 与 audio/video relationship 必须保留。
- AAC copy 或 codec conversion 后都重新 probe audio start/end、gap、packet/frame timing 和 conversion evidence；总时长相同但 audio 被重置到 0 必须 QA fail。

## 3. 创建 / 修改的重要文件

- 核心 Plan：`docs/superpowers/plans/2026-08-13-audio-alignment-edit-bridge.md`
- 状态同步：`AGENTS.md`、`PRD.md`、`ROADMAP.md`、`CHANGELOG.md`、`HANDOFF.md`

没有修改 `src/`、`tests/`、`renderer_templates/`、`scripts/`、`.agents/skills/` 或 `config/`。

## 4. 最终 Plan 架构变化

```text
Extracted PCM + Mapping
→ versioned Chunk Profile
→ deterministic natural-pause Chunk Plan
→ Provider units + boundary risk
→ Timed Transcript risk binding
→ Alignment false-ready protection
→ Bridge readable warning
→ QA risk re-derivation

Clean A-roll presentation evidence
→ visual-only Preview
→ presentation-preserving audio copy/conversion
→ packet/frame re-probe
→ audio start/gap/A-V relationship QA
```

## 5. Chunk fallback 与风险策略

- Profile revision 1 不使用 overlap、ASR stitching 或 previous-chunk prompt，保持最小且可复验。
- 找到安全停顿：边界为停顿 run 的 sample-aligned midpoint，risk=none。
- 找不到安全停顿：在同一 12 秒窗口选 300 ms interval 的最低 p95 energy valley；tie-break 为离 nominal boundary 更近，再按更早 sample；risk=high。
- high-risk guard 为边界前后各 1 秒。Provider/Transcript units 相交时保留 risk ID；若出现 duplicate、omission、competing window 或 anchor truncation，Beat/Cue 不能 aligned/high/ready。
- 没有文字层面的 LLM 拼接，也不隐藏 provider 的重复或漏识别。

## 6. Preview audio presentation contract

机器不变量：`Preview audio presentation time = Clean A-roll audio presentation time`，容差取 Preview frame、source/preview time-base tick 和 codec frame duration 的最大值。

- video presentation 0、audio presentation +0.375 时，Preview 0–0.375 必须仍无真人声音；
- raw PTS 非零/负但 edit list 已 presentation-normalized 时，使用 presentation time，不误用 raw PTS；
- internal gap 必须保持，不能将两侧语音贴合；
- MP4 兼容 codec 优先 copy；不兼容时只转换音频 codec，并保持同一 audible timeline；
- 允许 evidence-derived container timing 或等价 leading-silence representation，但禁止强制 shift 到 0、trim、atempo、loudnorm、silence removal 或用总时长掩盖错位。

## 7. 新增测试与 adversarial ownership

- CB1–CB7：自然停顿、句中 nominal boundary、无停顿 fallback/risk、重建时间单调、非零 Mapping、边界 duplicate/omission false-ready 防护、重复运行 digest 稳定。
- PA1–PA7：+0.375 audio start、raw PTS/presentation 分离、internal gap、AAC copy、codec conversion、presentation evidence tamper、总时长正确但 audio 提前到 0。
- Alignment calibration 新增 CR1–CR3，保证安全边界正常对齐、高风险边界不 false ready、边界后 Beat 可恢复。
- Task 29 分组 eval 和 property tests 负责 CB/PA；Task 26 QA 重新推导 chunk risk 与 Preview audio sync。

## 8. 已经可以运行什么

现有 Topic → Research → Script → Material → Motion 仍可运行。本轮只是 Implementation Plan Hardening，没有新增 runtime 能力。

## 9. 还不能运行什么

- 尚未开始任何 Implementation Task；
- 尚不能导入/转录 Clean A-roll 或生成 Alignment/Edit Bridge/Aligned Preview；
- 没有运行真实 provider、render 或真实用户 E2E；
- 不做 A-roll cleanup、字幕、BGM/SFX、标题封面或发布。

## 10. 测试和自审

- Plan 共 29 Tasks，依赖顺序连续。
- 完成 placeholder、interface、dependency、TDD、chunk-boundary、media-presentation、Preview audio sync、QA、adversarial 和 2.0 scope 自审。
- 完整项目基线仍收集 272 tests：270 pass，1 个显式真实渲染测试按预期 skip，1 个既有 Topic Discovery CLI 测试因固定为 `2026-08-10T08:00:00Z` 的 fixture 在当前时间越过 72 小时窗口而失败；生产时效筛选行为正确，本轮按“不得修改 tests/产品代码”的边界未修该旧 fixture，也未将其伪装为通过。
- diff 仅限 Plan 与状态文档；无产品代码。

## 11. 建议下一阶段

等待 ChatGPT 最终 Implementation Plan Review。只有收到明确授权后才允许从 Task 1 开始 TDD。

## 给用户的下一步操作

用户不需要阅读 Plan 或检查 GitHub。Codex 回复最末尾会提供完整交接，只需整段复制给 ChatGPT。
