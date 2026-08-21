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
本轮核心实现 commit：`412f699`（`feat: integrate local whisper production transcription`）
本轮文档收尾 commit：`34aad60`（`docs: finalize local transcription handoff`）

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

最终完整回归：`447 passed, 3 skipped, 58 subtests passed in 8.11s`；`compileall`、`git diff --check` 和 tracked-file credential-shaped secret scan 均通过。3 个 skip 是既有环境/显式真实渲染条件，不是本轮新增失败。不得把本轮的 QA warning 写成无 warning 的 PASS。

GitHub 已推送：`origin/agent/audio-alignment-edit-bridge` 当时 HEAD 为 `34aad60884804ba768f04766c0a7bfb55ec127ba`；与远端 `main` 的 compare 为 `ahead 66 / behind 0`，merge-base 为 canonical main `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`，不再是无共同祖先。远端 main 仍为 `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`；annotated `v0.6.1` tag object 为 `64358100d17de3f74d0d9c3db12a0c177a80a190`、peeled commit 仍为 canonical main；没有新 Release。

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

---

## 2026-08-21：REAL USER CLEAN A-ROLL E2E（Alignment Gate Blocked）

> 本节是当前最新状态，优先于本文件前面的历史交接记录。本轮只执行真实用户端到端试用，未开发新功能、未改稿、未改研究、未改素材包。

### 1. 本轮任务

使用用户提供的无烧录字幕真人 Clean A-roll，按正式 V1 路径执行：不可变媒体 → 音频抽取 → 官方本地
whisper.cpp v1.9.2 full multilingual `large-v3` + `--dtw large.v3` → Timed Transcript →
Script Alignment → Beat/Cue timing → approved Material / Original Motion → Edit Bridge →
完整 Remotion Preview → canonical QA。不得使用 fixture、synthetic timing、云端 ASR、第二 ASR、
forced aligner、Script 覆盖 Transcript 或任何自动剪口气/删填充词/改用户口播。

### 2. 完成了什么

- 已验证用户原始文件真实存在、可读取，且原文件未移动或覆盖：
  `/Users/hwang/Movies/口播/AI事故8月21日.mp4`。
- 为避免触碰原文件，只在项目外缓存建立同 inode hard link，作为本次不可变输入：
  `/Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/AI事故8月21日.mp4`。
- 已完成完整本地 large-v3 转写、Timed Transcript、Alignment、Bridge、字幕和完整时长 Remotion
  Preview；命令返回成功，后台没有遗留转写、渲染或测试进程。
- 没有重新生成或修改 reviewed Script、approved Research、reviewed Material Package，也没有修改
  Clean A-roll 本身。

### 3. 真实媒体与音频

- 原始容器：MP4/MOV；视频：H.264/AVC，1920×1072，逐行，30/1 fps；音频：AAC-LC，44.1 kHz，
  stereo；原始 presentation duration `620.530068` 秒，文件大小 `943,998,605` bytes。
- 原始媒体 SHA-256：`39d08733447f78c60b5cc0f737781c8fc3a9d95629d7f92a04902bbe0f8e57ec`。
- 正式抽取音频：24 kHz mono PCM，`14,892,722` samples，duration `620.5300833333333333333333333`
  秒；audio SHA-256：`83d8942cf36290bcba54483d98fd7c41e54bf3965113eb99c413698090bbf3cc`。
- 没有改变输入时长、结构、停顿、填充词或重录段。

### 4. Local ASR / Transcript

- Provider：`whisper.cpp`；runtime `v1.9.2+306c88f4d1286aec1bf96e544632897886af5501`；
  model：full multilingual `large-v3`；flags 包含 `--language zh --dtw large.v3 --output-json-full`；
  无 API Key、无云端、无 medium/turbo/quantized fallback。
- Timed Transcript：
  `.../DeepTalk-Aligned-Edit/artifacts/MEDIA-0d2b4644fb6d445189b9141250fe47d0/artifacts/timed-transcript-TRANSCRIPT-e3e949a79e744a3d90aa8a02b9366742.json`
 ；ID `TRANSCRIPT-e3e949a79e744a3d90aa8a02b9366742`；token granularity；真实 token/unit 数
  `2646`；transcript digest `85154b27fed6b9871c4975692b37410d5d79526caa7128cb3d0ccc2d525b92f7`；
  provider metadata digest `b34b197175e0e6ed0376abf7b8999bb2476cbe8d541c0dafb32b54a3902ed901`。
- raw token overlap count：`0`。没有发生裁剪、排序、平均、插值、segment fallback 或 canonicalization。
- 本次 session 没有将 whisper 单阶段 wall runtime / RTF 持久化到 Transcript Artifact；因此不能诚实地
  报出精确的 ASR runtime/RTF。完整 CLI 流程实际已等待 ASR、Bridge、长时渲染和 QA 全部结束，约为一
  小时内；这是当前 observability gap，不能用文件 mtime 倒推伪造精确值。
- 真实中文转写观察（保留原始 Transcript，没有人工纠正）：开头出现“设一家公正在给AI…”（目标语义
  应接近“一家公司正在给 AI…”）、“顺系统漏洞”（目标语义应接近“顺着系统漏洞”）、“这场…2026年7月Open…”
  （`OpenAI` 在该处被截成 `Open`）。`Hugging Face` 在多处被识别；后段出现 `OpenAI`、`SAFE`、`NASA`、
  `SB53` 相关内容，但仍有“OpenSeries”“SAVE”等可疑读法。上述是实际语音与模型输出的观察，不是用
  Script 改写后的文本。

### 5. Script Alignment / Beat / Cue

- Alignment：
  `.../DeepTalk-Aligned-Edit/alignment/SCR-301097255e2746ee9550ba8ea38acf01/MEDIA-0d2b4644fb6d445189b9141250fe47d0/ALIGNMENT-b3cfeb6801094e03b1b4658bde602760/script-alignment-r0001.json`
 ；ID `ALIGNMENT-b3cfeb6801094e03b1b4658bde602760`；绑定 Script `SCR-301097255e2746ee9550ba8ea38acf01`
  revision 2、Transcript revision 1。
- 18/18 Beats 均为 `needs_review`；confidence 为 13 medium、5 low；共有 `213` 个 alignment gaps。
  每个 Beat 都出现 `omitted_script_span` / `ad_lib_transcript_span`，多个 Beat 还出现
  `ambiguous_match`，B010 另有 `long_gap`。这是实际口播与 reviewed Script 存在连续偏差和候选窗口
  不唯一，不是可以安全忽略的少量错字。
- 8/8 Cues 均为 `unplaced`、confidence `none`，没有可靠的 `actual_start_seconds` /
  `actual_end_seconds`。例如 `VC001` 的“演变成了对 Hugging Face 基础设施的真实入侵”无法安全绑定到
  真实语音时间。
- 因此本轮没有用 Script 偷换 Transcript，也没有猜测素材出现时间；相关 Alignment / Material / Motion
  产品 Gate 必须停在等待 Review。

### 6. Material / Motion / Edit Bridge

- 复用已批准 Material `MAT-c29080b0554d4c49959b58f5fcc3174d` revision 2、Material Review
  `MRV-30c7d6fc40c043e6b071b45ded6bedc9`、Production Plan `PROD-20260813T133848055707`；没有重研究、
  重搜或修改素材。
- Edit Bridge：`BRIDGE-f1f75ecc66234b3e8ca843a635a47814` revision 1；共 13 个候选 placement：
  10 个 `real_image`（7 needs_review、3 rejected）和 3 个 `original_motion`（全部 needs_review）；
  ready placement `0`。所有非 A-roll placement 因缺少可靠 Cue timing 保持未落位，未伪造进入视频。
- 本次预览实际使用的 placement 只有 `VP0000`（Clean A-roll）；没有真实 screenshot/image/document
  或 Original Motion 进入这份 Preview。这说明完整视频虽已生成，但没有达到本轮要求的“真人 + 真实素材 +
  Original Motion”产品验收，不能宣称 REAL USER CLEAN A-ROLL E2E 通过。
- 5 个 `reference_only` 来源没有被偷偷放入视频；没有真实视频 placement，也没有猜选 clip range。

### 7. Preview / Subtitle

- 完整 Preview：
  `/Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/DeepTalk-Aligned-Edit/outputs/ALIGNED_PREVIEW.mp4`
 ；SHA-256 `36d29165238bd1a2dcb05060be067aee05eedfe44f0898ce0b3858e589d71bf9`；971,138,885 bytes；
  H.264/AAC，1920×1080，30 fps，duration `620.533333` 秒，和原始 Clean A-roll 完整时长一致到视频
  帧边界。
- Preview Manifest：`aligned-preview-manifest.json`，bridge digest
  `6e0b36b1ebc9b49d4d9f427d2acc26c2ad3ae2f43d9c3d272664e7668e8aa422`，manifest digest
  `099d6e33d53a1bd055d3c700537546e5e1194ab53b13e3ee042436e084c0ae6c`，`subtitles_enabled=true`。
- 当前 Preview **带烧录 Basic Subtitle**，字幕仍来自真实 Timed Transcript；没有生成真正的无字幕
  visual master。`ALIGNED_PREVIEW_VISUAL.mp4` 只是静音视觉中间片，同样使用当前字幕渲染配置，不能当作
  无字幕成片。

### 8. Canonical QA / Gate

- QA：`.../outputs/edit-bridge-qa.json`；6 项 canonical revalidation 全部 `pass`：root artifacts、
  chunk/transcript mapping、normalization/alignment risk、placement timing、preview manifest/audio、
  ready-only preview。
- QA package gate 为 `warnings`，blocking failure `0`；唯一 issue 是 `EBI0001 partial_placement_unready`
  （warning）。这表示技术 QA 没有发现伪造或损坏输出，但不等于产品素材/对齐 Gate 通过。
- 本轮产品 Gate：`REAL USER TRANSCRIPTION` **PASS（token timing 可产出，overlap=0）**；
  `REAL USER ALIGNMENT` **BLOCKED / NEEDS_REVIEW**；`REAL USER MATERIAL PLACEMENT` **BLOCKED / WAITING**；
  `REAL USER MOTION PLACEMENT` **BLOCKED / WAITING**；`REAL USER FULL PREVIEW` **TECHNICAL OUTPUT ONLY，未通过产品验收**；
  `REAL USER CLEAN A-ROLL E2E` **BLOCKED / NOT PASSED**。
- 本轮没有进入人工视觉 Preview Gate，因为没有可靠 Beat/Cue timing，视频只保留 A-roll 和字幕；不要把这
  份 Preview 当作已经通过的成片，也不要要求用户按 timecode 做审美判断。

### 9. 测试、Git 与版本

- 当前代码回归：`454 passed, 3 skipped in 13.29s`；本轮未改产品代码，`git diff --check` 与工作区检查通过。
- 分支：`agent/audio-alignment-edit-bridge`。本轮真实运行开始时 HEAD 与最终文档提交前 HEAD 均为
  `0a9830a3a04cdfa5e11a5a34fa92d99d29f45586`（`docs: record large-v3 long-form verification`）。
  本轮只新增本交接/CHANGELOG 文档记录，不新增产品功能。
- canonical main HEAD 未改变：`8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`；正式 `v0.6.1` peeled
  commit 未改变，annotated tag object 仍为 `64358100d17de3f74d0d9c3db12a0c177a80a190`；没有新 tag、
  GitHub Release 或 main merge。
- 当前状态仍为 `V1.0 Candidate — Unreleased`。不要开始字幕新功能、ASR 修正、第二模型、forced aligner、
  音频清理或其他新功能；先由 ChatGPT Review 本轮 Alignment blocker，并决定下一步是否需要用户重录/
  重新确认口播、受控对齐规格或其他产品决策。

### 10. 给产品经理的 Review 请求

请 ChatGPT Review：真实 Transcript 与 reviewed Script 的偏差是否达到需要产品决策的程度；在保持
fail-closed 和“不用 Script 覆盖真实语音”的前提下，下一轮应如何处理 18 个 `needs_review` Beat、213 个
gaps 和 8 个未落位 Cue；是否接受当前 Preview 仅 A-roll + Basic Subtitle 的技术产物；以及在没有可靠
alignment 前，是否允许任何 Material/Motion placement Gate 继续。请先给出明确的下一轮 Codex 指令，本轮
不要直接进入新的功能开发。

## 给用户的下一步操作

你现在不需要看片，也不需要做任何技术操作。请把本次回复最底部“请把以下内容复制给 ChatGPT”后的整段文字原样发给 ChatGPT，等待它决定下一步。不要打开终端、找 JSON、改字幕或重新上传视频。

## 2026-08-14：Quality-first large-v3 长版生产验证

### 1. 本轮任务

按 ChatGPT Review 的正式质量优先决定，将 V1 本地转写生产默认升级为 full multilingual
`large-v3`，锁定正确 DTW preset，保留 medium 历史，调查真实 token overlap，并完成同一份
272 秒评测音频与 274 秒 non-private synthetic Clean A-roll 的完整 production E2E。

### 2. 已完成内容

- 默认 Provider 已改为官方 full `ggml-large-v3.bin`，只能与 `--dtw large.v3` 配对；禁止
  medium、turbo、量化模型和云端静默 fallback。
- Bootstrap 重新从官方 Hugging Face 下载并本地复算：3,095,033,483 bytes、SHA-256
  `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`；运行时为
  whisper.cpp v1.9.2/source `306c88f4d1286aec1bf96e544632897886af5501`，Apple Silicon Metal。
- 增加 macOS 系统 HTTPS proxy 探测，解决桌面进程没有继承 shell proxy 时无法下载官方模型的
  真实环境问题；不改变模型来源或身份。
- Token overlap 继续 fail closed，并新增完整 raw overlap audit contract；实际 large-v3 long-form
  smoke 得到 `overlap_count=0`，没有触发 canonicalization，也没有篡改时间戳。
- 272 秒 no-key smoke 已通过 `ProviderTranscript → Timed Transcript → Script Alignment`。
- 274.267 秒 non-private synthetic Clean A-roll 已走完整正式入口，生成 Material/Motion/Subtitle/
  Edit Bridge/全长 Remotion Preview/canonical QA；没有重研究、改稿或重做素材包。

### 3. 创建 / 修改的重要文件

- `src/deeptalk_studio/transcription/local_whisper_cpp.py`：large-v3 默认、`large.v3` DTW、provenance、
  macOS system proxy transport、结构化 overlap error。
- `src/deeptalk_studio/transcription/local_asr_selection.py`：按实际 DTW 记录 parser provenance，并输出
  原始 token overlap audit。
- `evaluations/local_asr_selection/run_large_v3_production_gate.py`：可直接执行的 no-key smoke、
  overlap evidence、full session child/liveness monitor。
- `tests/test_local_whisper_bootstrap.py`、`tests/test_local_whisper_cpp_provider.py`、
  `tests/test_large_v3_production_gate.py`：large-v3 default/bytes/digest/DTW/no-medium fallback/
  raw overlap/liveness/direct CLI regressions。
- `README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`CHANGELOG.md`、
  `.agents/skills/align-video/SKILL.md`：更新 quality-first policy、真实长版结果与用户边界。

### 4. 当前架构

```text
Clean A-roll
  → Media / lossless 24 kHz transcription audio / Timestamp Mapping
  → TranscriptionChunkPlan
  → verified local whisper.cpp v1.9.2 + full large-v3 + --dtw large.v3
  → ProviderTranscript (raw runtime token offsets and provenance)
  → Timed Transcript → Alignment → reviewed Material → Motion → Basic Subtitle
  → Edit Bridge → full Remotion Preview → canonical QA
```

medium 的 selection cache/artifacts 保持为历史审计；正式 runtime/model/provenance 和所有真实运行
输出都在 Git 外 `~/.cache/deep-talk-studio/transcription/`。

### 5. 已经可以运行什么

- 正式 no-key large-v3 生产路径会自动下载、核验、缓存并使用 Apple Silicon Metal，不要求用户找模型、
  设置 PATH 或 API Key。
- 272.367 秒中文评测音频：runtime 87.210505 秒、RTF 0.320194、1,167 token、overlap 0；
  `large-v3-production-smoke.json` 已记录完整原文、timing/provenance、轻量 medium 对照。
- 全长 formal session 用 274.267 秒 synthetic Clean A-roll 已生成 Preview：1920×1080、30 fps、
  H.264 + AAC、274.3 秒、6,079,376 bytes、SHA-256
  `2377c5459c5bd31894ece27c105ec7305f03269f215732c41efea619df773c81`。
- canonical QA 六项 revalidation 均 pass；唯一 `EBI0001 partial_placement_unready` 是 warning，
  没有 blocking failure；subtitle binding 与 Preview manifest 已核对。

### 6. 还不能运行什么

- 尚未运行用户本人的真实 Clean A-roll，也尚未由用户人工观看自己的内容 Preview；不能称 V1.0 发布。
- 本轮没有实现 Audio cleanup、forced aligner、词典/LLM correction、second ASR、BGM/SFX、标题、封面、
  发布或其他功能。

### 7. 已知问题 / warning / gap

- `partial_placement_unready` 仍有 1 个 warning：只有已可用 placement 进入 Preview，未就绪素材没有被伪造
  或硬塞进视频。它不阻断 canonical QA，但需要 ChatGPT 判断 V1 对真实用户试用时的展示策略。
- large-v3 的 same-audio proper-noun exact presence：OpenAI、DeepSeek、AI Agent、GPU 为 true；`昇腾` 为
  false。报告保留原始转写，没有人工修正；这不是 token-timing 或 E2E blocker。
- 新评测 runner 修正了 completed session 摘要中 bridge digest 的字段名；现有 session 的 manifest 和
  saved bridge 已独立验证其 digest 为
  `1ac996561f25248477f937c25b80ed73af5f613761376015613708c9d1d12181`，无需为摘要字段重渲染。

### 8. 重要技术决策

- 用户质量优先选择覆盖了 Selection Gate 后的 medium 默认；full large-v3 是唯一 V1 production default，
  必须使用 `large.v3` DTW heads。
- 不以任意毫秒阈值消除 overlap。raw overlap 保留完整证据并 fail closed；本次实际 large-v3 无 overlap，
  因此没有引入未经 Review 的 canonicalization contract。
- 长时 Remotion render 由独立子进程执行、每 15 秒记录 PID/liveness/output bytes；665.763 秒完成，
  没有因安静或缓慢而提前终止。
- 本轮保持 `V1.0 Candidate — Unreleased`，不创建 tag、Release，不修改 main、v0.6.1 或 reviewed upstream
  artifacts。

### 9. 需要产品经理决定什么

1. Review full large-v3 quality-first default、272 秒 token/proper-noun evidence、274 秒 Preview 与
   canonical QA。
2. 确认 `partial_placement_unready` warning 在真实用户 Gate 的产品展示/交接策略是否可接受。
3. 若通过，单独安排用户真实 Clean A-roll E2E 与人工 Preview Gate；在用户试用完成前不得发布 V1.0。

### 10. 建议下一阶段

停止新功能，先让 ChatGPT Review 本轮 long-form evidence。若其批准，再请用户仅拖入已经剪好口气的
真人口播视频，运行同一正式入口并观看自己的 Preview；仍不扩展 Audio Alignment 功能范围。

### 11. Git / Release 状态

- 工作分支：`agent/audio-alignment-edit-bridge`；本轮开始时生产集成记录 HEAD 为
  `b6dcf3c7a3a48ba818ff416d3ee83e1c3e011980`。
- large-v3 design/plan commits：`b79fd9e16ff2e2fafb763b8268af1c0c19397446`、`8f86f98`；
  实现和证据 runner commit：`b9c51c2cb7c53b6c75cd8035a570e3bb367e9e63`。
- GitHub compare：branch 对 canonical main `ahead 70 / behind 0`，merge-base 仍为
  `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`。
- main HEAD 与 peeled `v0.6.1` tag commit 都是
  `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`；现有 latest Release 仍是 v0.6.1。
  本轮没有修改 main/tag/Release。

## 给用户的下一步操作

你现在只需要把 Codex 回复最底部“请把以下内容复制给 ChatGPT”后面的整段文字，原样发给 ChatGPT。你不需要打开终端、安装模型、设置 API Key 或自己总结。
