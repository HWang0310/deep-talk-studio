# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `v0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

当前开发分支：`agent/audio-alignment-edit-bridge`

本轮：Audio Alignment + Visual Edit Bridge Integration Hardening（Unreleased）。

## 1. 本轮任务是什么

按 ChatGPT 已通过的 Hardened Implementation Plan，先修复 Topic Discovery 过期 fixture 基线，再连续完成 Task 1–29，把用户已剪好口气的真人口播视频与 reviewed Script、reviewed Material 和现有 Motion 对齐，输出可导入剪辑软件的 Edit Bridge 和可观看的 Aligned Preview。

本轮只完成 Implementation 与合成证据，不能代替用户真实 Clean A-roll E2E。

## 2. 完成了什么

- 修复 ChatGPT Implementation Review 的 8 项条件：正式入口不再接收 stage lambdas；CLI/Skill 自动发现正式上游；Material 视频字段跨模块保真；Cue OUT 使用完整语义范围；Alignment 绑定 Clean A-roll 总时长；OpenAI segment-only 明确粗粒度；正式 QA validator 由仓库工厂掌握；自然语言修改真正生成新的 Bridge/Preview/Manifest/QA。
- 新增 `edit_bridge_session.py` 作为唯一具体生产所有者，正式顺序为 import → extract → Mapping → Chunk → provider → Transcript → Alignment → Material Projection → Placement/timing → Bridge → Remotion → audio mux → Manifest → canonical QA。
- canonical QA 会实际重探测视频、重建所有确定性链路、复验 Production、素材路径/SHA、Preview Manifest 和音频 presentation；不能用调用方 lambda 伪装正式通过。
- 使用同一正式入口完成真实 MP4 + 真 Remotion 合成 E2E；自然语言修改也已用真实 MP4/mux 验证不可覆盖 r2 流程。
- Task 0 单独修复 Discovery 测试时钟，不改 72 小时 freshness 生产规则。
- 完成 Clean A-roll 不可变导入、`ffprobe` 流/PTS/presentation 证据、lossless transcription WAV 派生、Timestamp Mapping 与不可覆盖存储。
- 完成 24 MiB request cap / 25 MiB hard limit 的确定性 PCM 自然停顿分块；无安全停顿时保留 high boundary risk，不重叠、不删停顿、不用 LLM 拼接。
- 完成 provider-neutral Timed Transcript 与 OpenAI SDK adapter。当前受控调用使用 `whisper-1` + `verbose_json`；真实 word timestamps 优先，只有真实 segment timestamps 时明确降为 coarse，两者均无则失败；provider 不能写 alignment status 或 Gate。
- 完成可逆 NFKC/中英文/数字规范化、确定性全局 DP 对齐、重复/缺失/即兴/倒序和 ambiguity evidence。长稿使用行检查点与块内重算，结果与完整参考矩阵逐操作、逐 digest 一致。
- 完成 Profile calibration、Script Beat → Material Cue → Production Scene 稳定身份链、Alignment 不可覆盖 revision。
- 完成 Material Production Projection：rights/reuse 不再作制作 Gate，但文件、SHA、格式、grounding、binding 和原 Production QA 仍严格复验。
- 完成真实图片/截图/视频/Motion 统一 Placement，自动推导 canonical IN/OUT/duration、source clip 双时间轴、overlap/same-start conflict、timing status 和 7 秒 long-still Preview safeguard。
- 完成 Edit Bridge JSON、普通中文 Markdown、NLE-neutral CSV、Marker package 和不可覆盖 revision。
- 完成 1920×1080、30fps Remotion Aligned Preview。Clean A-roll 始终是 layer 0，只有 ready Placement 进入画面；视觉中间片强制无音轨。
- 最终 Preview 只混入原 Clean A-roll 主音轨。AAC/MP3 优先 copy，PCM 等不兼容 codec 转 AAC；正 audio offset、internal gap、audio start/end 均由 `ffprobe`/decode 重验，不 trim、reset、atempo、loudnorm、删静音或 `-shortest`。
- QA 实际执行 root、transcript、alignment、placement、preview 五组 validator，缺组、validator 异常、未 ready 素材入画、音轨 presentation drift 均 fail-closed；不接受调用者自报 boolean pass。
- 完成 `align-video` Skill、CLI 普通用户 Gate 和自然语言画面时长修订边界。

## 3. 创建 / 修改的重要文件

- 媒体与时间：`narration_media.py`、`narration_schema.py`、`audio_timestamp_mapping.py`、`transcription_chunking.py`、`narration_storage.py`
- 转录：`transcription/base.py`、`transcription/deterministic.py`、`transcription/openai.py`、`transcript_builder.py`
- 对齐：`text_normalization.py`、`sequence_alignment.py`、`alignment_builder.py`、`alignment_validation.py`、`alignment_storage.py`
- 素材与时间线：`material_bridge.py`、`edit_bridge_planner.py`、`edit_bridge_schema.py`、`edit_bridge_validation.py`、`edit_bridge_storage.py`
- Preview/QA/Workflow：`aligned_preview/`、`renderer_templates/aligned_preview_remotion/`、`edit_bridge_qa.py`、`edit_bridge_workflow.py`
- 用户入口：`.agents/skills/align-video/`、`cli.py`、`docs/EDIT_BRIDGE_CONTRACT.md`
- 评测：`evaluations/audio-alignment-edit-bridge/`与相关 `tests/test_alignment_*`、chunk boundary、preview audio sync、OpenAI smoke tests。
- 状态文档：`README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`CHANGELOG.md`、`HANDOFF.md`、`docs/ARCHITECTURE.md`。

## 4. 当前架构

```text
reviewed Script / approved Research / reviewed Material / QA-ready Motion
                              +
                  immutable Clean A-roll
                              ↓
Media Probe → Extracted WAV → Timestamp Mapping
                              ↓
Natural-pause Chunk Plan → Timed Transcript
                              ↓
Reversible Normalization → Deterministic Alignment
                              ↓
Beat/Cue/Scene → Unified Visual Placement → Edit Bridge
                              ↓
visual-only Remotion Preview → original A-roll audio mux
                              ↓
five-group rederivation QA → ALIGNED_PREVIEW.mp4
```

## 5. 已经可以运行什么

- 离线 deterministic provider 可完整运行 Media → Mapping → Chunk → Transcript → Alignment → Placement → Bridge → Preview → QA。
- 真实 `ffmpeg/ffprobe` fixture 已验证正 audio offset、internal gap、AAC copy 和 PCM→AAC conversion。
- 真实 Remotion 已渲染 1920×1080/30fps 合成 Preview，再混入单一 Clean A-roll 音轨并通过 probe。
- 用户拖入 mp4/mov 后，`align-video` Skill 可按固定流程处理，不需要用户选 provider、renderer、路径或时间点。

## 6. 还不能运行什么

- 尚未收到本期用户真实 Clean A-roll，因此 real-user E2E 仍 pending，不得宣称 V1.0。
- 当前环境没有可用的 `OPENAI_API_KEY` 与指定的本地 synthetic smoke WAV，因此真实 OpenAI transcription smoke 未运行；这是 environment unavailable，不是 product fail。
- 不做自动剪口气、字幕、BGM/SFX、标题、封面、发布或 NLE 专属工程导出。

## 7. 测试、评测与真实渲染

- Integration Hardening 最终全量 unittest：424 collected，421 pass，3 environment/explicit-render gated skip，0 fail。
- 唯一生产入口真实 Remotion E2E：可用图片、已选范围视频、未选范围视频、QA-ready Motion 与带内部静音 Clean A-roll 同时进入 canonical 上游；H.264，1920×1080，30fps，单一 Clean A-roll 音轨；输出 595,390 bytes，SHA-256 `029e5211071126bc0183eb2dc354b24ebff5089d9d80a8ff724ff7e7ba38b58f`；canonical QA `warnings`，无 blocking issue。未选范围视频保持 `clip_selection_needed` 且未进入 Preview。
- 自然语言 Revision 快速真实媒体链：Bridge r2、`ALIGNED_PREVIEW-r0002.mp4`、Manifest r2、QA r2 均不可覆盖保存并通过（warnings）。
- 3 个 skip：真实 OpenAI transcription smoke（key/media environment unavailable）、旧 Remotion + HyperFrames 双引擎 integration 默认关闭、exact-entrypoint Remotion 回归默认显式开启；后者本轮已人工显式运行并成功。
- A–AI：35/35 pass。CB1–CB7：7/7 pass。PA1–PA7：7/7 pass。更新后的 repeat digest：`fc90d0f29334e6f454f5196e61af24d55a689308ce732770285dc7b7e4d5a41a`。
- Aligned Preview renderer：ESLint pass，TypeScript typecheck pass，Skill quick validation pass。
- 最终 synthetic real render：H.264，1920×1080，30fps，1 条 AAC 音轨；audio start `0.353s`，audio end `1.185s`，internal gap 保留；Preview SHA-256 `7f38457c191af470dbf674798dfd5f751191d7d9a34ae3025dbbf4122592e618`，559,166 bytes。
- scope scan 没有新增 A-roll cleanup、字幕、BGM、发布或自动选 B-roll 实现。

## 8. 已知 warning / gap

- 真实 provider smoke 仍未运行，原因是当前环境未授权；已有真实 SDK transport 与授权后才执行的完整 smoke test，不会提交 key、媒体或 raw response。
- `npm audit` 曾报告 2 个上游 low severity dependency warning；本轮保留已审批的锁定 Remotion 4.0.507，没有为清除 low warning 擅自升级 renderer。
- 真实用户视频可能暴露新的转录差异、剪辑节奏或画面审美问题；这些必须通过 real-user Gate 如实记录，不用 synthetic pass 掩盖。

## 9. 重要技术决策

- Clean A-roll 是 canonical timeline，V1.0 不自动剪口气。
- container/stream time、media presentation time 和 extracted-audio time 始终分离，Mapping 可从证据重推导。
- LLM 不生成 canonical timestamp；segment-only 只能 coarse，不插值伪造 word precision。
- canonical time 是 decimal seconds；30fps 只是 Preview 派生层。
- placement status 与 timing status 正交；可靠画面的时长冲突是 warning，不清除 placement。
- 视觉中间片与音轨 mux 分离，确保 B-roll/Motion 原声永不混入主音轨。
- 合成/对抗 pass 不是真实用户 E2E pass。

## 10. 需要产品经理决定什么

当前不需要用户或 ChatGPT 选择技术参数。下一个决策 Gate 是：真实 Clean A-roll 产生的 `ALIGNED_PREVIEW.mp4` 由用户观看后，ChatGPT Review 对齐、素材插入、Motion 时机、warning/gap 和 QA 是否可以进入正式版本。

## 11. 建议下一阶段

Implementation Review 所有 hardening 条件已经完成。请 ChatGPT Review 当前开发分支、唯一生产入口、canonical QA、真实 Remotion E2E 和自然语言 revision，然后确认是否允许进入真实用户 Clean A-roll 上传 Gate。

## 给用户的下一步操作

暂时不需要上传视频。先把本轮完整交接原样发给 ChatGPT Review；Review 通过后再按它的决定进入真实用户 Clean A-roll Gate。
