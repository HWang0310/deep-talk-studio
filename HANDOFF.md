# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `v0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

当前开发分支：`agent/audio-alignment-edit-bridge`

本轮：REAL USER CLEAN A-ROLL E2E Preflight（Unreleased）。

## 1. 本轮任务是什么

ChatGPT 已通过 Hook-aware Script 与 Basic Subtitle V1 Implementation Review，并正式批准进入真人 E2E Gate。本轮只做只读 Preflight：核对 branch/workspace、视频工具、真实 Remotion、真实 OpenAI 转写环境、当前本期根工件与本期真实素材文件；不开发功能、不要求用户先上传视频、不创建版本。

## 2. 完成了什么

- Hook-aware Script 不新增重复 schema。现有 `audience_promise + ordered Beats + closing` 足以承载结构；Writer/Profile/Review 明确要求 opening hook、value promise、必要的 re-hook / information turn 和 conclusion payoff。
- 新 Review consistency mapping 为 `0.4.2`；`narrative_structure` 缺失 Hook-aware 结构时生成 blocking `hook_structure`。旧 `0.4.1` reviewed 工件继续兼容读取。
- 新增版本化 `subtitle-profile/1`、`subtitle-artifact/1`、不可覆盖 JSON/SRT 和显示 normalization。
- word/token transcript 只组合真实单位边界；segment-only 一段一 cue 且明确 coarse，不做词内插值或 karaoke。
- 字幕已进入唯一正式 production entrypoint、Edit Bridge root binding、Remotion payload、Preview Manifest、自然语言 revision 重渲染和 repository-owned canonical QA。
- Remotion 在 A-roll、图片、视频和 Original Motion 全时段显示同一 narration subtitle；统一预留底部安全区，视觉 overlay 不能占用字幕区。
- Preview 仍只有 Clean A-roll 主音轨；自然语言调整画面后生成新 Bridge/Preview/Manifest/QA revision，字幕绑定、音频起点和内部静音保持不变。
- 当前 branch/HEAD 正确且 workspace clean：`agent/audio-alignment-edit-bridge` / `5ff947c99859ef9179b27a7ca9129448eeb7a10e`。
- `ffmpeg 8.1.1`、`ffprobe 8.1.1` 可用；正式 exact-entrypoint Remotion 真实渲染回归在 26.654 秒完成并通过。
- 本期 approved Research r3、reviewed Script r2、reviewed Material Package r2、Production Plan、Motion Manifest、Production QA 均存在、精确相互绑定；Production QA 为 `pass`，Motion 输出文件存在且可 probe。
- 真实转写 Preflight 为 **BLOCKED**：当前 Codex 进程没有 `OPENAI_API_KEY`，也没有 OpenAI Python SDK；因此不允许用 deterministic provider 代替真实用户转写。
- 本期 Material Package 的外部网页/官方文件仍是 `reference_only` / 无本地 capture，未发现本期可供正式 Rough Cut 使用的真实 screenshot/image/document 或带明确范围的真实视频。本期现有原创 Motion 输出完整可用，但真实素材子项是 `missing_asset`。

## 3. 创建 / 修改的重要文件

- Subtitle Core：`config/subtitle-profile.json`、`subtitle_profile.py`、`subtitle_builder.py`、`subtitle_storage.py`。
- Renderer：`renderer_templates/aligned_preview_remotion/src/BasicSubtitles.tsx`、`AlignedPreview.tsx`、`index.css`。
- Integration / QA：`edit_bridge_session.py`、`edit_bridge_qa.py`、`edit_bridge_schema.py`、`edit_bridge_planner.py`、`aligned_preview/remotion.py`。
- Hook：`config/script-profile.json`、`script_prompt.py`、`script_review.py`、`schema.py`、`write-script/SKILL.md`、`docs/SCRIPT_CONTRACT.md`。
- 设计与计划：`docs/superpowers/specs/2026-08-13-v1-scope-reconciliation-basic-subtitle-design.md`、对应 implementation plan。
- 本轮没有修改 production code 或本期历史工件；只更新状态记录。
- 测试：subtitle profile/builder/storage、renderer、manifest、canonical QA、exact-entrypoint E2E 与自然语言 rerender regressions。

## 4. 当前架构

```text
Hook-aware reviewed Script + approved Research + reviewed Material + QA-ready Motion
                                  +
                         immutable Clean A-roll
                                  ↓
Media → Mapping → Chunk → real Timed Transcript
                                  ├→ Subtitle Artifact / SRT
                                  └→ deterministic Script Alignment
                                             ↓
Material/Motion Placement → Edit Bridge → subtitled visual Remotion render
                                             ↓
                      original Clean A-roll audio mux
                                             ↓
 Subtitle + roots + placement + preview + audio canonical QA
                                             ↓
                           ALIGNED_PREVIEW.mp4
```

## 5. 已经可以运行什么

- 正式入口可从 Timed Transcript 自动生成、保存并烧录 Basic Subtitle V1。
- 字幕跨 A-roll、真实图片、真实视频和 Original Motion 连续显示。
- 用户说“这张图短一点/晚一点/一直留真人”后，新完整视频 revision 仍带相同当前字幕。
- Subtitle/Transcript/Profile/Media/Bridge/Manifest/renderer enablement 可由 QA 重推导，篡改失败关闭。

## 6. 还不能运行什么

- **REAL USER E2E = BLOCKED**，因此尚不能接收/处理用户正式 Clean A-roll，也不得称 V1.0 通过。
- 阻断一：当前 Codex 运行环境没有 `OPENAI_API_KEY` 和 OpenAI Python SDK。官方转写接口仍兼容本项目的 `whisper-1 + verbose_json + word timestamps` 实现，但真实调用必须在授权环境中运行。
- 阻断二：本期缺少可进入 Rough Cut 的真实 screenshot/image/document capture；没有假装把 reference-only 链接或原始网页/PDF 当作 ready asset。没有明确 clip range 的真实视频也不会自动猜选段。
- 不做自动剪口气、重录删除、filler word cleanup、BGM/SFX、高级/karaoke 字幕、标题封面、发布、平台上传或 NLE 专属工程导出。

## 7. 测试、评测与真实渲染

- 完整 unittest：436 collected，433 pass，3 environment/explicit-render skip，0 fail。
- Subtitle/Hook/renderer/integration 定向：26 项通过；Script Hook 相关 35 项通过。
- Remotion ESLint 与 TypeScript typecheck：pass。
- exact-entrypoint 真实 synthetic Remotion E2E：初版与自然语言 revision 均成功，H.264、1920×1080、30fps、2 秒、单一 Clean A-roll AAC 音轨。
- 初版 Preview：908,187 bytes，SHA-256 `283b2bace94f3853745f4740fcdfc33b6bb5595b2d3a96def2748f005be19919`。
- revision Preview：930,296 bytes，SHA-256 `cf13a810249dc897556592cfec7ba47f9ed5b692ee48d50c1b71693a07460b2a`。
- Subtitle Artifact digest：`6a4465ce947e64c829816ff63d07648773492d0ba2da15adc8f30731eac31963`。
- 两版 canonical QA：`warnings`，原因是既有 synthetic 未选范围视频继续保持 `clip_selection_needed`；无 blocking failure。
- 人工抽帧确认：字幕确实烧录、两行内、高对比、底部安全区生效；初版和 revision 都有字幕。
- 本轮 Preflight：当前 production roots 的 Production QA 是 `pass`；一张 `HERO001.png` 与 8 个 Motion MP4/MAPREVIEW 文件存在，抽样 `MA001.mp4` 可由 ffprobe 读取（10.048 秒）。
- OpenAI adapter 单元测试 8 项通过，真实 smoke 1 项因授权/真实媒体环境缺失跳过；没有伪造 provider success。

## 8. 已知 warning / gap

- real transcription 的唯一 blocker 是环境授权/SDK，不是 adapter 设计或官方接口不兼容。
- 本期真实素材缺口不是 Rights Gate 问题：现有 reference-only 网页/官方文件没有被错误升格为 ready；需要真实 capture/image/document 文件，真实视频还需要明确 clip range。
- 当前默认中文换行使用确定性字符容量，不做 AI 动态避障；真实长视频可能暴露断句与审美调整需求。
- `npm audit` 的 2 个上游 low severity warning 仍存在；没有擅自升级锁定 Remotion。
- 真实用户 E2E 才能发现实际录音中的 ASR 错字、长停顿、语速、字幕断句和素材时机问题。

## 9. 重要技术决策

- Hook 是 Script 内容结构，不是后期特效；不修改既有 Script Draft schema。
- Subtitle 是 Transcript 的确定性派生物，不从 Script timecode 或 LLM 猜测时间。
- Basic Subtitle V1 只有一套版本化样式、最多两行、无 karaoke/花哨动画。
- 视觉安全区全局统一，不让每个 Motion 自行决定字幕位置。
- Subtitle Artifact 与 SRT 可审查，但用户默认拿到的是烧录字幕的完整 MP4。
- synthetic pass 不等于 real-user V1 pass。

## 10. 需要产品经理决定什么

请 ChatGPT 决定如何为当前 Codex 运行环境提供真实 OpenAI transcription 授权（不把密钥写入仓库），以及是否先补齐本期真实 screenshot/image/document capture。两项 blocker 均解除后，Codex 再要求用户录制并拖入 Clean A-roll。

## 11. 建议下一阶段

停止新增功能。保持本分支 Unreleased。先解除真实转写环境和真实素材 capture 两项 Preflight blocker；随后用户只需拖入已经自行剪好口气的正式真人口播 mp4/mov，由同一正式入口完成 real transcription、Alignment、Material/Motion、Basic Subtitle、完整 Rough Cut 与 QA，再由用户观看。

## 给用户的下一步操作

现在不要录制或上传视频。把 Codex 回复底部的完整交接原样发给 ChatGPT，请它只决定如何解除“真实转写授权/SDK”和“本期真实素材 capture”两个 blocker；解除前不进入真人视频 Gate。
