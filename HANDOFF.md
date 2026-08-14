## 2026-08-14：V1 本地 ASR Selection Gate

当前正式版本：V0.6.1 / `v0.6.1`
当前产品状态：V1 Candidate — Unreleased；本地 ASR 选择 Gate 已完成，默认接入等待 ChatGPT Review
仓库：https://github.com/HWang0310/deep-talk-studio
当前开发分支：`agent/audio-alignment-edit-bridge`
本轮初始 HEAD：`4bb3c93f00a350a9b414e7893782db4f08924052`
本轮产品实现 commit：`00105b6`（`feat: complete local ASR selection gate`）

### 1. 本轮任务是什么

本轮先执行正式 Local ASR Selection Gate，再决定 V1 默认本地转写候选。没有执行此前
“直接采用 whisper.cpp”旧指令；没有修改 reviewed Script、approved Research、reviewed
Material Package、Motion/Production 工件或正式版本。候选必须用同一份 2–5 分钟非私人中文
评测音频真实运行，并经过时间戳 hard gate 和最小 Alignment 适配。

### 2. 完成了什么

- 固定并构建官方 `ggml-org/whisper.cpp v1.9.2`，源码 commit
  `306c88f4d1286aec1bf96e544632897886af5501`；multilingual `medium` 模型文件
  1,533,763,059 bytes，SHA-256 `6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208`。
- 固定并构建官方 `microsoft/VibeASR.cpp` commit
  `5cbce71c65911a7e10639ac13b6ab6929e4c8f9e`，配合官方
  `VibeVoice-ASR-BitNet@66e7802`；LM 992,877,600 bytes、SHA-256
  `fbe273d8dc2f2433bb25f849e19d77ea65aaa2188d12c20cee987ab6f321e002`；VAE
  703,080,064 bytes、SHA-256
  `4941c82608c253ec066b5cc74d3dd11a5c8fef96cccbc5b87359ef0fe4338df6`。
- 两候选使用同一份外部非私人评测音频：24 kHz、单声道、PCM 16-bit、272.367458 秒，
  SHA-256 `c1b08fe694eb59d598af2fb06b29f165ee341afc82048e999ddb362dceeba601`。音频由
  macOS `say` 从公开评测文本生成，没有用户视频、私人录音或云端上传；因此不冒充真人
  口音验收。
- Whisper 使用 Metal，实际 wall runtime 44.37 秒、wall RTF 0.1630；`--dtw medium`
  JSON 直接给出 token offsets。1,136 个单位通过 `ProviderTranscript(token)` →
  `Timed Transcript` → `Script Alignment`，首个 Beat 为 `aligned/token`，起止
  `0.05–3.41s`。Timed Transcript digest 为
  `6e7bb2cccbd0c720ac5c8f962629b23617530f7abb499235c2edeb5a00a50d41`，Alignment
  digest 为 `bf2f594cc5a99b17b2c6dd3be93b49cf9812fe6f01e09495a87d165053d2cafe`。
- VibeASR 同音频真实运行：JSON prompt 331.97 秒、RTF 1.2109；默认 text prompt
  284.17 秒、RTF 1.0402。两个模式都输出重复文本并耗尽 max tokens，没有 machine-owned
  media timestamp；`Start/End` 只是模型 prompt/output 形状，不能作为时间证据。因此
  ProviderTranscript Gate 直接 fail closed，没有生成 Timed Transcript 或 Alignment。
- 选择结论：推荐 `whisper.cpp multilingual medium` 作为 V1 默认本地 Provider 候选，
  但正式 production integration/自动 bootstrap 仍是 `PENDING_CHATGPT_REVIEW`。
- 新增 evaluation-only `local_asr_selection` parser、复现脚本、报告和 regression；不把
  大模型、音频或原始长日志提交 Git。外部真实摘要位于
  `/Users/hwang/.cache/deep-talk-studio/asr-selection/eval/local-asr-selection-report.json`，
  SHA-256 `df1abf766cb66236f893f2d3ee9bf8240d4233e0de90e59c1661e6639b959759`。

### 3. 创建 / 修改的重要文件

- `src/deeptalk_studio/transcription/local_asr_selection.py`：只接受官方 Whisper 直接
  token offsets；固定拒绝 VibeASR prompt-generated times；不改变生产 Provider 默认值。
- `evaluations/local_asr_selection/run_selection_gate.py`：将真实候选输出接入现有
  `ProviderTranscript → Timed Transcript → Script Alignment` 的可复现实验链。
- `evaluations/local_asr_selection/report.md`、`selection-result.json`：模型、音频、SHA、
  runtime/RTF、时间戳证据、中文名词差异和 Gate 结论。
- `tests/test_local_asr_selection.py`：3 个 parser/Gate regression。
- `docs/superpowers/plans/2026-08-14-local-asr-selection-gate.md`、`README.md`、
  `ROADMAP.md`、`AGENTS.md`、`CHANGELOG.md`：更新 V1 Candidate 与长期协作边界。
- reviewed Script、approved Research、reviewed Material、旧 Production 工件和正式 Release
  未改动。

### 4. 当前架构

```text
Clean A-roll → Media/Mapping/Chunk → provider-neutral ProviderTranscript
                                        ├─ local ASR selection Gate
                                        │    ├─ whisper.cpp token offsets → Timed Transcript
                                        │    │                              → Script Alignment
                                        │    └─ VibeASR no machine timestamps → fail closed
                                        └─ future approved V1 default local Provider
                                                   ↓
                    Material/Motion Placement → Edit Bridge → subtitled Preview
```

Provider-neutral boundary、真实 timestamp granularity、segment/coarse 安全降级和不插值规则
均保持不变。当前选择代码是 evaluation-only，未把模型下载和 UI provider 选择塞入正式生产。

### 5. 已经可以运行什么

- 在项目外缓存中重跑同音频的两套官方候选，记录源码/model revision、大小、SHA、加速、
  runtime、RTF、文字摘要和 timestamp provenance。
- 用 `run_selection_gate.py` 将 Whisper 的真实 token offsets 送入现有 Timed Transcript
  和 Script Alignment；VibeASR 无证据时在 ProviderTranscript 阶段停止。
- 保持原有 Audio Alignment + Visual Edit Bridge + Basic Subtitle V1 synthetic integration
  和 Material/Motion 产物可用。

### 6. 还不能运行什么

- Whisper 默认 Provider 尚未接入正式 V1 production bootstrap；必须先经 ChatGPT Review。
- 这轮评测音频是非私人合成语音，不等于用户真人 Clean A-roll 的最终中文准确率、停顿、
  音色、字幕断句或素材时机验收。
- 真实用户 Clean A-roll E2E 仍不能宣称 V1.0 通过；必须保留现有 Media → real transcription
  → Alignment → Material/Motion → Subtitle → Preview → QA Gate。
- 不做自动剪口气、TTS、BGM/SFX、高级/karaoke 字幕、标题封面、发布或平台上传。

### 7. Gate、测试和产物

- Local ASR timestamp Gate：Whisper **PASS**；VibeASR **FAIL**。
- Whisper adapter chain：ProviderTranscript **PASS**、Timed Transcript **PASS**、
  Script Alignment **PASS/aligned/token**。
- VibeASR adapter chain：ProviderTranscript **STOPPED**、Timed Transcript **NOT_BUILT**、
  Script Alignment **NOT_BUILT**。
- 完整 unittest：441 run，438 pass，3 skipped，0 failure。
- 新增 local ASR regression：3 pass；`compileall` pass；既有 Production/Remotion 定向
  regression 未改动，完整 suite 一并通过（真实 aligned E2E 仍按环境 skip）。
- 真实 Material Preflight：继续保持 READY；本轮没有重新获取、重写或替换 reviewed Material。
- REAL TRANSCRIPTION PREFLIGHT：本地选择 Gate 完成，但尚未处理用户正式 A-roll；OpenAI
  cloud adapter 仍是无 API Key 的后续可选路径。
- REAL USER E2E：**BLOCKED/PENDING**，原因是 ChatGPT 尚未 Review 默认集成，且尚未进入
  用户本期 Clean A-roll 真实试用。

### 8. 已知 warning / gap

- macOS `say` 合成音频不覆盖真人声学分布；下一次真实 Clean A-roll Gate 才能确认用户
  录音下的专有名词和停顿表现。
- VibeASR 官方仓库在本机 `BITNET_ARM_TL1=ON` 编译失败，关闭 TL1 后 I2_S CPU 路径构建
  成功；这降低了它的 bootstrap 稳定性评分，但不改变其 timestamp Gate 失败。
- Whisper 在同一合成音频仍有 `OpenAI→OpenEye`、`DeepSeek→DeepSeq`、`AI Agent→AI Agit`、
  `昇腾→生酮`、`GPU→GTU` 等明显名词错误；脚本和研究不能据此自动改写，后续需由真实
  用户试用和产品 Gate 决定。
- 本机 shell 未自动继承代理；本轮下载通过用户现有本地代理完成，密钥未输出。

### 9. 重要技术决策

- V1 timestamp priority 高于速度、体积和 README benchmark；没有可靠媒体时间戳即 fail。
- 只接受 runtime 直接给出的 token/word offsets；不接受 segment 内插、字符位置、平均
  分配或 LLM 生成时间。
- V1 不依赖 `OPENAI_API_KEY`、Anthropic、Google 等 API Key；OpenAI Provider 保留为未来
  V2/V3 可选能力。
- 模型只在 `/Users/hwang/.cache/deep-talk-studio/asr-selection/` 外部缓存，不提交仓库；
  正式接入后只允许 winner 自动 bootstrap，loser 不成为默认 UI 路径。
- 本轮不是新版本；main、`v0.6.1` tag、GitHub Release 保持不变，没有创建 v0.7/v0.8/v0.9、
  v1.0.0 或 rc tag。

### 10. 需要产品经理决定什么

请 ChatGPT Review `evaluations/local_asr_selection/report.md` 与
`selection-result.json`，确认：

1. 合成非私人音频是否足以通过“工程选择 Gate”，以及真实用户 A-roll 仍需保留哪些最终
   Gate；
2. 是否批准 `whisper.cpp multilingual medium` 成为 V1 默认本地 Provider，并给出正式
   bootstrap/cache/CLI 规格；
3. 是否允许下一阶段进入正式 V1 default integration，然后再安排真实用户 Clean A-roll
   transcription preflight。

### 11. 建议下一阶段

先不要开始音频对齐新功能，也不要创建 Release。先由 ChatGPT Review 本轮 ASR 选择证据；
通过后再实现一个明确版本化、provider-neutral、无 API Key 依赖的 V1 local transcription
bootstrap，并重新跑生产定向 regression。之后才进入用户真实 Clean A-roll E2E Gate。

### 给用户的下一步操作

请把下面“请原样发给 ChatGPT”整段直接复制给 ChatGPT；暂时不要录制、上传或选择技术参数。

# DeepTalk Studio 开发交接

当前正式版本：V0.6.1 / `v0.6.1`

仓库：https://github.com/HWang0310/deep-talk-studio

当前开发分支：`agent/audio-alignment-edit-bridge`

本轮：REAL USER CLEAN A-ROLL E2E Preflight unblock（Unreleased）。

## 1. 本轮任务是什么

本轮只解除两个 Preflight blocker：将 OpenAI Python SDK 安装到项目专用运行环境，并让当前 reviewed Material Package 可安全登记真实官方网页截图；不改 reviewed Script、approved Research 或 Material 历史，不要求用户先上传视频，不创建版本。

## 2. 完成了什么

- Hook-aware Script 不新增重复 schema。现有 `audience_promise + ordered Beats + closing` 足以承载结构；Writer/Profile/Review 明确要求 opening hook、value promise、必要的 re-hook / information turn 和 conclusion payoff。
- 新 Review consistency mapping 为 `0.4.2`；`narrative_structure` 缺失 Hook-aware 结构时生成 blocking `hook_structure`。旧 `0.4.1` reviewed 工件继续兼容读取。
- 新增版本化 `subtitle-profile/1`、`subtitle-artifact/1`、不可覆盖 JSON/SRT 和显示 normalization。
- word/token transcript 只组合真实单位边界；segment-only 一段一 cue 且明确 coarse，不做词内插值或 karaoke。
- 字幕已进入唯一正式 production entrypoint、Edit Bridge root binding、Remotion payload、Preview Manifest、自然语言 revision 重渲染和 repository-owned canonical QA。
- Remotion 在 A-roll、图片、视频和 Original Motion 全时段显示同一 narration subtitle；统一预留底部安全区，视觉 overlay 不能占用字幕区。
- Preview 仍只有 Clean A-roll 主音轨；自然语言调整画面后生成新 Bridge/Preview/Manifest/QA revision，字幕绑定、音频起点和内部静音保持不变。
- 当前开发分支已推送：`agent/audio-alignment-edit-bridge`；本轮核心实现 commit 为 `56882811de31ad1d373be61790889424491eef1d`，交接记录随后仅作状态更新。
- `ffmpeg 8.1.1`、`ffprobe 8.1.1` 可用；正式 exact-entrypoint Remotion 真实渲染回归在 26.654 秒完成并通过。
- 本期 approved Research r3、reviewed Script r2、reviewed Material Package r2、Production Plan、Motion Manifest、Production QA 均存在、精确相互绑定；Production QA 为 `pass`，Motion 输出文件存在且可 probe。
- 新增不可变 `material-capture-manifest/1`：精确绑定 reviewed Material Package、inspected Material、来源、页面/区域、Cue、捕获时间、本地静态文件、MIME、大小和 SHA-256；任何 package、binding 或文件篡改均 fail closed。
- Material Production View 可重放已经验证的 Capture，不改写 Material r1/r2 历史，rights/reuse 保持历史元数据而非生产文件 Gate。
- 已实际打开并读取 M001 的 OpenAI 官方事件说明页，并登记真实截图：PNG、127,433 bytes、SHA-256 `d3305a0d3b9c58c950aa75421c05effb27013d581916a9e0156026106788b3e1`，绑定 VC001；capture manifest digest 为 `3ff4c1df0aea1bbb5152615f126cd5f2a2bfd23b51c30396f7dc5765d65e1de8`。M001 production projection 已为 `ready`。
- 已在项目专用 `.venv` 安装并验证 OpenAI Python SDK `2.54.0`；transport 可实例化至仅缺授权阶段。`OPENAI_API_KEY` 仍未设置，未调用 API、上传音频或伪造 smoke。

## 3. 创建 / 修改的重要文件

- Subtitle Core：`config/subtitle-profile.json`、`subtitle_profile.py`、`subtitle_builder.py`、`subtitle_storage.py`。
- Renderer：`renderer_templates/aligned_preview_remotion/src/BasicSubtitles.tsx`、`AlignedPreview.tsx`、`index.css`。
- Integration / QA：`edit_bridge_session.py`、`edit_bridge_qa.py`、`edit_bridge_schema.py`、`edit_bridge_planner.py`、`aligned_preview/remotion.py`。
- Hook：`config/script-profile.json`、`script_prompt.py`、`script_review.py`、`schema.py`、`write-script/SKILL.md`、`docs/SCRIPT_CONTRACT.md`。
- 设计与计划：`docs/superpowers/specs/2026-08-13-v1-scope-reconciliation-basic-subtitle-design.md`、对应 implementation plan。
- 新增 capture-manifest / Material Bridge 最小实现和回归；本期历史 Research、Script、Material Package 未修改。
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

- **REAL USER E2E 仍为 BLOCKED**，因此尚不能接收/处理用户正式 Clean A-roll，也不得称 V1.0 通过。
- 唯一剩余阻断：当前 Codex 运行环境没有 `OPENAI_API_KEY`。SDK 已可用，官方 `whisper-1 + verbose_json + word timestamps` 实现已可调用，但真实调用必须在授权环境中运行。
- M001 已满足本轮最小真实 screenshot/image/document 要求；真实视频仍是 optional，且无明确 clip range 时绝不自动猜选段。
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
- capture manifest + Material Bridge + real material placement 定向 10 项通过；真实 M001 projection 已重新推导并通过完整性验证。

## 8. 已知 warning / gap

- real transcription 的唯一 blocker 是安全环境授权，不是 SDK、adapter 设计或官方接口不兼容。
- 普通 Playwright 会被目标网页 403 拒绝，但 Chrome 用户浏览器实际打开官方页并完成读取、截图；没有把 403 页面或下载替代品登记成素材。
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

请 ChatGPT Review 本轮 immutable capture manifest / production projection 的边界，并确认可进入唯一剩余的 OpenAI API Key 授权动作。授权后先运行最小真实 OpenAI smoke；通过后才请用户录制并拖入 Clean A-roll。

## 11. 建议下一阶段

停止新增功能。保持本分支 Unreleased。现在只解除真实转写授权；随后先运行最小真实 OpenAI smoke，再由用户拖入已经自行剪好口气的正式真人口播 mp4/mov，由同一正式入口完成 real transcription、Alignment、Material/Motion、Basic Subtitle、完整 Rough Cut 与 QA，再由用户观看。

## 给用户的下一步操作

现在不要录制或上传视频。请创建/准备一个 OpenAI API Key，并把它添加到当前 Codex 运行环境的 `OPENAI_API_KEY` 安全环境变量或 Secret 中。不要把 Key 发到聊天正文里，也不要写进项目文件。设置后只需告诉 Codex“已设置”。
## 2026-08-14：V1 Local Transcription Production Integration

当前正式版本：V0.6.1 / `v0.6.1`
当前产品状态：V1.0 Candidate — Unreleased；Local ASR Selection Gate 已 PASS，本轮本地生产集成已实现，真实用户 Clean A-roll Gate 仍待执行
仓库：https://github.com/HWang0310/deep-talk-studio
当前开发分支：`agent/audio-alignment-edit-bridge`
本轮初始 HEAD：`afb4a5ea5d104c2f65b8744504080b9fb37ff756`
本轮最终实现 commit：待本轮提交后补入（不会创建 Release）

### 1. 本轮任务是什么

根据 ChatGPT 已通过的 Local ASR Selection Gate，把 `whisper.cpp multilingual medium`
正式接入 V1 本地转写生产路径。普通用户只需提供人工清理后的 Clean A-roll；系统自动准备
本地 runtime/model、运行真实 token transcription，并沿用现有 Timed Transcript、Alignment、
Material、Motion、Basic Subtitle、Edit Bridge、Remotion 和 canonical QA。不得检查或要求 API
Key，不得修改 reviewed Script、approved Research、reviewed Material，也不开发新的 ASR 选型或
Audio Alignment 功能。

### 2. 完成了什么

- 新增 `LocalWhisperCppTranscriptionProvider`，实现 `TranscriptionProvider` / `ProviderTranscript`
  provider-neutral contract；默认解析器不查看 `OPENAI_API_KEY`，OpenAI adapter 仅保留未来可选能力。
- 新增 `WhisperCppBootstrap`：锁定官方 whisper.cpp v1.9.2、source commit
  `306c88f4d1286aec1bf96e544632897886af5501`，Apple Silicon 生产构建启用 Metal；自动准备
  `whisper-cli` 和 multilingual medium 模型，下载/构建后核对 runtime version、model SHA-256、
  文件大小，并写入 provenance。
- 新增版本化 `config/transcription-local-whisper-profile.json`，仍使用现有
  `TranscriptionChunkPlan` 与 local→global mapping，只把本地 long-form request cap 提高到
  96 MiB/100 MiB hard limit，避免长音频尾 chunk 的不真实短请求；不是绕过分块。
- Provider 只接受 whisper.cpp full JSON 的真实 token offsets；缺失 timing、越界或同 chunk
  内重叠即 fail closed，不做插值、平均分配、LLM 推断、TTS、silence removal 或云端 fallback。
- ProviderTranscript provenance 绑定 provider、runtime/source/build、model/SHA/bytes、language、
  inference parameters、audio digest、chunk-plan digest、raw response digest、每 chunk evidence、
  timestamp granularity/provenance 与 runtime/RTF。
- CLI / `align-video` Skill 已改为普通用户语言：不要求安装 runtime/model，不要求 API Key；首次
 运行只提示正在准备本地语音识别模型。

### 3. 创建 / 修改的重要文件

- `src/deeptalk_studio/transcription/local_whisper_cpp.py`：bootstrap、runtime/model 校验、真实
  token transcription、provenance、默认 Provider resolver。
- `src/deeptalk_studio/transcription/local_asr_selection.py`：复用并扩展 selection parser，支持
  production chunk order/request provenance；保留 `evaluations/local_asr_selection/` 历史不覆盖。
- `src/deeptalk_studio/transcription_chunking.py`、`config/transcription-local-whisper-profile.json`：
  本地 long-form profile 和同一 chunk planner。
- `src/deeptalk_studio/edit_bridge_session.py`、`src/deeptalk_studio/cli.py`、
  `src/deeptalk_studio/transcription/__init__.py`：正式入口接线和默认 provider。
- `.agents/skills/align-video/SKILL.md`：普通用户本地转写说明。
- `tests/test_local_whisper_bootstrap.py`、`tests/test_local_whisper_cpp_provider.py`、
  `tests/test_local_asr_selection.py`、`tests/test_edit_bridge_cli.py`、相关 Skill/chunk/session 回归。
- `README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`CHANGELOG.md`：更新 V1 本地转写默认、缓存、
  no-key 原则、真实证据与 gap。

### 4. 当前架构

```text
Clean A-roll
  → Media / lossless 24 kHz transcription audio / Timestamp Mapping
  → existing TranscriptionChunkPlan (local long-form profile)
  → LocalWhisperCppTranscriptionProvider
       → verified whisper.cpp runtime token offsets
       → ProviderTranscript(token, provenance)
  → Timed Transcript → Alignment → Material → Motion → Basic Subtitle
  → Edit Bridge → Remotion Aligned Preview → repository-owned canonical QA
```

正式 production cache 为 `/Users/hwang/.cache/deep-talk-studio/transcription/`（用户级、Git 外）；
selection evaluation cache `/Users/hwang/.cache/deep-talk-studio/asr-selection/` 仍仅作历史评测。
已验证生产 runtime：`runtimes/whisper.cpp-1.9.2-arm64/bin/whisper-cli`，model：
`models/whisper.cpp-1.9.2-medium/ggml-medium.bin`，provenance：
`provenance/whisper.cpp-1.9.2-medium.json`。模型 1,533,763,059 bytes，SHA-256
`6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208`；runtime build identity 为
`1.9.2+runtime-sha256:01b232021d77510472911514c822a20187c2725fb3f71a8e31aaa00d991f0d59`；
acceleration 为 Apple Silicon Metal。

### 5. 已经可以运行什么

- 无 `OPENAI_API_KEY`、无其他模型 API Key 时，真实非私人中文音频可通过正式
  `LocalWhisperCppTranscriptionProvider` 生成 token-level ProviderTranscript，并进入 Timed Transcript。
- 无 API Key 的短版正式 `run_real_edit_bridge_session` 已跑通全链路：真实 whisper.cpp、Timed Transcript、
  Alignment、approved Material、Motion、Basic Subtitle、Edit Bridge、Remotion Preview 和 canonical QA。
- 正式生产链路保留 Clean A-roll 原始音频 presentation；不替换成 TTS，不自动清理口气。

### 6. 还不能运行什么 / 当前边界

- 尚未完成用户本期真实 Clean A-roll 的最终语音质量和人工观看 Gate；短版 synthetic E2E 不能替代真人试用。
- 完整约 272 秒合成验证的 raw whisper.cpp 输出出现 5 处微小 token overlap，Provider 按安全合同停止，未裁剪或修正真实时间；这不是已通过的真人 Gate。
- 约 272 秒完整 Remotion render 在当前环境长时间无输出而停止，短版 20 秒 render 已成功；需要 ChatGPT 决定是否把长时 render 当作环境/后续性能 gap。
- 短版 canonical QA 是 `warnings` 而非纯 `pass`，唯一 warning 是预期的 `EBI0001 partial_placement_unready`，因为 20 秒音频未覆盖全部 reviewed Script placement。
- 不实现 VibeASR 复测、forced aligner、第二 ASR、transcript correction、BGM/SFX、标题、封面、发布或新版本。

### 7. 真实产物、测试与 Gate

无 API Key local smoke：外部证据 `~/.cache/deep-talk-studio/transcription/evidence/local-whisper-production-smoke.json`；
1,136 token units，runtime 42.780224 秒，RTF `0.157068`，audio SHA-256
`c1b08fe694eb59d598af2fb06b29f165ee341afc82048e999ddb362dceeba601`，transcript digest
`153374e56a30e2f29a6ac923008dbc510db8b202539734f0445a97c82926e5dd`，token granularity，model SHA
与上文一致，证据记录无 API Key。

短版正式 E2E 外部 session：`~/.cache/deep-talk-studio/transcription/e2e/formal-short-session/`；
源视频为非私人 20 秒 synthetic clean A-roll。Preview：
`DeepTalk-Aligned-Edit/outputs/ALIGNED_PREVIEW.mp4`，SHA-256
`35f43bced73eeb06f1db0bb86501b087da474f74ed026f78ce106c21aebe6363`，442,161 bytes，1920×1080、
30fps、H.264、AAC、20 秒，字幕已烧录。Timed Transcript 93 units；transcript digest
`7f5eb465e28fd3691a8a62fbdab3fd1d4d5649fe63bcd2189418872146f087d5`；subtitle digest
`0b333b09124ab5ac2d1ceaaf9e7e25a4a4e910004431e42a9e62d0dfeb652125`；alignment digest
`dff0b168560e8fbe464f9a86a2ce92708d68683b7e2a8c65e87abf94aab96b7e`；bridge digest
`edbea885752bc59d326bd37d96593d6356c8db436baf20e1ccc4234dcc76e033`。QA package gate 为
`warnings`，0 blocking fail，1 个预期 partial-placement warning；`used_placements=["VP0000"]`，
其余 12 个 placement 未伪造进入视频。现有 5 个 reference-only source 仍没有被放入视频。

当前 Gate 结论：

- Local ASR Selection Gate：PASS（ChatGPT 已批准）。
- Bootstrap/runtime/model digest Gate：PASS（Apple Silicon Metal provenance 已保存）。
- No-API-key local smoke：PASS。
- Short production E2E：PASS WITH EXPECTED WARNING。
- Basic Subtitle / Alignment / Edit Bridge / Motion short render：PASS。
- Real Material Preflight：PASS（复用已 Review 的 Material Package，没有重新获取）。
- Canonical QA：WARNINGS，0 fail；不能写成无 warning 的 PASS。
- `REAL TRANSCRIPTION PREFLIGHT`：CONDITIONAL / PARTIAL（本地路径可运行，完整用户 A-roll 未验收）。
- `NO-API-KEY V1 PRODUCTION PATH`：PASS（smoke + short synthetic E2E 范围内）。
- `REAL USER CLEAN A-ROLL GATE`：BLOCKED/PENDING 用户真实 Clean A-roll 与人工 Review。

本轮应重新运行并记录完整回归的最终数字；短版和定向测试已先通过。不得在没有最终测试输出时声称“全部 Gate PASS”。

### 8. 已知问题 / warning / gap

- whisper.cpp 在长版合成音频的 5 个局部位置给出了重叠 token offsets；安全实现拒绝继续，不能偷偷裁剪、排序或平均化真实时间。是否需要未来调整官方 runtime/config，交由 ChatGPT 决定。
- 本地 profile 将 extraction sample rate 固定为 24 kHz，并把长音频 request cap 版本化提高到 96 MiB；这是为保持真实 token offset 在长 chunk 内可验证，不是为了掩盖模型质量。
- 20 秒短版只覆盖一个 placement，因此 QA 的 partial-placement warning 是预期缺口；需要真人完整 A-roll 后再判断是否仍可接受。
- 当前 full-length Remotion render 的环境耗时未解决；没有伪造 full-length preview 或把短版证据说成完整用户 Gate。

### 9. 重要技术决策

- V1 默认只用 `whisper.cpp multilingual medium`；不重新 benchmark VibeASR，不实现 forced aligner 或第二模型。
- 所有用户默认路径 no API Key；禁止先查 API Key，禁止静默回退 OpenAI/云端。
- 真实 runtime token timestamp 是唯一可用时间证据；缺失、越界、重叠即 fail closed。
- 复用现有 chunk/mapping/Timed Transcript/Alignment/Subtitle/Edit Bridge/QA，不重写 downstream；短版 provenance 证明链路共享同一 production payload。
- 生产 runtime/model/cache/provenance 不进入 Git；selection evidence 继续保留。
- 当前仍是 `V1.0 Candidate — Unreleased`，不创建 tag、Release 或 main 修改。

### 10. 需要产品经理决定什么

请 ChatGPT Review 本轮生产集成和短版真实产物，并决定：

1. 是否接受当前 direct token overlap 的 fail-closed 策略，还是下一轮给出受控的官方 runtime/config 处理规格；在决定前不得放宽安全边界。
2. 是否接受短版 QA 的预期 `partial_placement_unready` warning，以及约 272 秒完整 Remotion render 的环境耗时 gap。
3. 是否批准下一步让用户提供真实 Clean A-roll，进行正式的真人 transcription / subtitle / placement / preview 人工 Gate；未通过前不要宣称 V1.0。
4. 在上述 Review 后，请给出下一轮明确的 Codex 任务；本轮没有开始新的 Audio Alignment 或其他扩展功能。

### 11. 建议下一阶段

先由 ChatGPT Review 本交接、`formal-short-session` Preview/QA 和长版 gap；若接受当前实现，下一轮只安排真实用户 Clean A-roll 试用与人工 Review，不改稿、不改 Research、不扩大 ASR 选型。

## 给用户的下一步操作

你现在只需要把 Codex 回复最底部“请把以下内容复制给 ChatGPT”后面的整段文字，原样发给 ChatGPT。你不需要打开终端、安装模型、设置 API Key 或自己总结。
