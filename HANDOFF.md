# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

本轮：Audio Alignment + Visual Edit Bridge Design Contract Hardening，保持 Unreleased。

## 1. 本轮任务是什么

ChatGPT 对 Design HEAD `f9cb70315ea02dbe83353d7c4eee97800dcddccf` 给出 Conditional Pass。本轮继续在 `agent/audio-alignment-edit-bridge` 修复四个 Design blocker：媒体 presentation 时间映射、frame-rate-neutral canonical timecode、placement status 与 timing conflict 正交关系、长静态画面 Preview exposure safeguard。

本轮只修改 Design Spec 与必要状态文档，不写 implementation plan、不开发、不新增 Skill、不 transcription、不 render、不创建 PR/tag/Release。

## 2. 完成了什么

- 将 container/stream PTS、Clean A-roll media presentation timeline 和 extracted-audio timeline 明确拆分。
- 新增 `audio-timestamp-mapping/1`：使用 `media_time = extracted_time × scale + offset`，scale 首版固定 1，offset 由真实 PTS/edit/skip/discard/extraction evidence 确定，可非零。
- 明确 AAC encoder priming/padding、edit list、非零/负 PTS、audio presentation 晚启动、VFR 与正常 duration 微差策略；不再要求 PCM 与 container duration 精确到一个 sample。
- canonical machine time 改为 decimal seconds，人类时间码为 `HH:MM:SS.mmm`；30fps frame/timecode 只存在于 Preview 派生字段。
- 将 placement uncertainty 与 timing conflict 拆成两个维度：位置可靠的 Motion/B-roll duration mismatch 或 overlap 保持 `placement_status=ready`，以 timing warning 进入 Rough Cut；真正的 anchor/same-start selection ambiguity 才 needs_review。
- 长 still semantic window 保留为 canonical 事实窗口；Preview exposure 使用 `rough-cut-duration-profile/1`，首版继承 Material Profile 0.5 已版本化的 7 秒默认 Cue duration，超长时 cap Preview exposure 并记录 warning/adjustment。
- 补充 AA–AI adversarial cases 与 property checks，覆盖 timestamp mapping、fps/VFR、status/conflict、same-start ambiguity 和长 still。

## 3. 创建 / 修改的重要文件

- 核心 Design：`docs/superpowers/specs/2026-08-13-audio-alignment-edit-bridge-design.md`
- 状态同步：`AGENTS.md`、`CHANGELOG.md`、`HANDOFF.md`、`PRD.md`、`ROADMAP.md`

没有修改 `src/`、`tests/`、`renderer_templates/`、`scripts/`、`.agents/skills/` 或 `docs/superpowers/plans/`。

## 4. 当前设计架构

```text
container/stream PTS + edit/codec evidence
→ Clean A-roll media presentation timeline
→ immutable extracted audio
→ versioned Timestamp Mapping
→ provider Timed Transcript boundaries
→ mapped media-presentation timestamps
→ deterministic Script/Beat/Cue alignment
→ reliable placement status + independent timing status
→ canonical semantic seconds / HH:MM:SS.mmm
→ Preview-only 30fps frames + exposure/conflict adjustments
→ Edit Bridge + Aligned Preview + QA
```

## 5. 时间映射契约

- container/stream PTS 可以非零或负；canonical media presentation 起点始终是实际播放的 0 秒。
- extracted audio 从自身 sample 0 开始，可能与 media presentation 0 有确定性 offset。
- Mapping scale 首版必须为 1；offset 只能来自首个 derivative sample 的 source presentation PTS 与 media presentation origin。
- Mapping 保存首末 PTS/sample、edit/skip/discard、time base、evidence digest 和动态 tolerance，validator 重新推导。
- Transcript 的 extracted boundary 与映射后的 media boundary 都保存，最终 Alignment 只使用后者。

## 6. Canonical 与 Preview 时间

- canonical machine truth：decimal seconds。
- canonical readable timecode：`HH:MM:SS.mmm`，与 source fps/VFR 无关。
- Preview profile：1920×1080、30fps；只生成 `preview_in_frame/out_frame` 与带 Preview 前缀的 frame timecode。
- frame snap adjustment 不反写 canonical seconds/timecode。

## 7. Placement / Conflict / Duration 语义

- placement status 只表示 narration placement、对象选择和素材 binding 是否可靠。
- timing status 独立为 clear/warning/blocking。
- 已可靠 Motion/B-roll 的自然时长不匹配或可靠 Visual overlap：placement 仍 ready，timing warning，Package Gate warnings，可执行 preview-only crop/early-return/takeover。
- canonical 同时开始且没有 track priority：selection blocker，相关 placement needs_review，不按内部 ID 自动选。
- still semantic duration 超过 7 秒：semantic OUT 不变，placement 仍 ready，Preview exposure cap、duration warning 和 adjustment 全部记录。

## 8. QA / Gate 更新

QA 新增重推导：

- presentation origin/duration 与 raw stream timebase/PTS/edit evidence；
- Mapping scale/offset/start/end/sample count/dynamic tolerance/digest；
- extracted 与 media Transcript boundary；
- decimal seconds 与 `HH:MM:SS.mmm`；
- Preview-only frame mapping；
- placement/timing/duration status 的正交一致性；
- long-still cap、selection blocker 与所有 preview adjustment。

Mapping 无法重算、scale 非 1、mapped timestamp 越界是 fail。可靠 timing warning、long-still cap 或局部 selection blocker使 package 为 warnings；其他 placement 继续保留。

## 9. 已经可以运行什么

现有 Topic → Research → Script → Material → Motion 仍可运行。本轮只产出可供 ChatGPT Review 的 hardened Design。

本轮没有新增可运行能力。

## 10. 还不能运行什么

- 尚不能导入、映射或转录 Clean A-roll；
- 尚不能运行 deterministic alignment；
- 尚不能生成 Edit Bridge 或 Aligned Preview；
- 尚无实现计划、代码、测试或 Skill；
- 不做 A-roll cleanup、字幕、BGM/SFX、NLE 工程、标题封面或发布。

## 11. 自审与开放风险

Spec Self-Review 已通过 placeholder、internal consistency、timebase、schema、Gate/status、Preview/canonical 区分和 adversarial coverage 七项检查。开放风险仍包括真实媒体 edit-list/codec 组合、provider timestamp 能力和 7 秒 still cap 的真实 E2E 校准；任何 calibration 变化必须形成新版本 Profile，不能改写旧 Artifact。

## 12. 建议下一阶段

等待 ChatGPT 最终 Design Review。只有 ChatGPT 明确将 Conditional Pass 升级为通过并另行发出任务后，才允许创建 implementation plan；当前不得实现。

## 给用户的下一步操作

用户不需要检查文件或 GitHub。Codex 聊天回复会附上完整 Design Hardening 交接，用户只需整段复制给 ChatGPT。
