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

### 2026-08-22：POST-ALIGNMENT FULL VISUAL PLANNING

- 完成：本期 episode-only 高密度视觉偏好、18 Beat 审计、16 个由 approved Alignment 投影的机会（15 ready、B011 unplaced）、新 Material Review、Production、Bridge 和完整真实 Preview r0002。
- 未修改：reviewed Script、approved Research、Transcript、ASR、approved Alignment；B018 `588.11–620.14s` 仍保持真人尾段。
- Gate：Material/Production PASS；Canonical QA 6/6 PASS，唯一 warning 为 B011 `partial_placement_unready`，没有硬塞候选画面。
- 当前 Preview：`ALIGNED_PREVIEW-r0002.mp4`，1920×1080、30fps、H.264/AAC、620.533333 秒，SHA `d5c17ab1d883e7d890c195c9f111fb6f1d85dd1c0e37f519cb74f8b64d66fffb`。此前失败的 r0001 与历史工件保留不覆盖。
- Git：`agent/audio-alignment-edit-bridge`，commit `d8e7560` 已推送；main、v0.6.1 tag 和 Release 未改变。

## 给用户的下一步操作

观看新的完整预览；满意请回复“预览通过”，不满意直接说哪一处画面需要调整。

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

## 2026-08-21：当前轮最终状态（SAFE-CUE REAL MATERIAL COMPLETION）

> 本节位于文件末尾，覆盖本轮之前的历史交接摘要。它只记录本轮 SAFE-CUE completion 的最终状态；历史章节保留用于审计。

### 1. 任务与边界

- 已完成 VC003/B006 与 VC007/B016 的真实语义素材补齐、Material Gate、Production canonical rebind、Edit Bridge、全长真人 Preview 和 Canonical QA。
- 没有修改 reviewed Script、approved Research、Transcript、ASR、Alignment、Basic Subtitle、reviewed Material 的旧 revision、既有 Motion 或旧 Preview。
- 没有开始 Audio Alignment + Edit Bridge 新功能；没有创建 V1 tag/Release，也没有修改 main。

### 2. 对齐与素材

- Approved Alignment：`ALIGNMENT-96854be79b9048a2b6800e1313efb2a6`，digest `b71ccfcbe1decb71a48c2901daba1f0627596f4c95c9d191dd3c1fb3a351dce0`；全局单调、Beat localization、Cue projection 均 PASS，17/18 Beat aligned，B011 保留 needs_review warning。
- VC003 时间只来自 Alignment：`162.55–174.48s`，Preview 实际 `162.55–169.55s`；VC007：`488.77–512.12s`，Preview 实际 `488.77–495.77s`。没有猜测时点。
- 新 Material `MAT-20260821-safe-cue-completion-01` r2，Material Review/Gate PASS，digest `756f417948c2c7a91bfdf2f7f0b0c5037c9d0684a4134a154cb0c1aeeecf9e5a`；旧 Material r2 未覆盖。
- M003/VC003 为 [AISI 官方 Figure 1 页面](https://www.aisi.gov.uk/blog/how-do-environmental-factors-impact-ai-behaviour) capture，SHA `d75611aaf0372f3c3ab5ca42c16ec3b380eca7a008bc6027a185ae1e167641d6`；M007/VC007 为 [California SB-53 官方法条页面](https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB53) capture，SHA `16e60b0a2a4476e603e863dff5f74953c9552b352ccdb343a167b02f8dcfa66e`。Capture Manifest digest `1e80d03a04f28e9783a4981aaba1cc91db738cdd244e1e5d7f9c1880c33d5c2e`。
- 两张 capture 均如实保留 `editorial_reference_only/reference_only`；没有声称版权许可，rights 不参与 Production Gate；未绕过 paywall、DRM 或访问控制。

### 3. Production / Motion / Bridge

- Production `PROD-20260821T170000-safe-cue-completion-01`，digest `a63217f219130119b4360bf1d392a223542d68d40ad2cddb1a5155226140ca13`；既有 approved Motion 仅做 scene/payload/SHA canonical rebind，未重新渲染，Production QA PASS（digest `fcfa194c74a08b1c830001a1b69d27abfe38b915d81d595f9a4e515ba820dbd9`）。
- Edit Bridge `BRIDGE-20260821-safe-cue-completion-01` r1，digest `74108d721bd27cdea6459cdf9c1b9099c72fba3f26520fa36fbe8e14ca2051ca`；staged 仅 `VP0000` A-roll、`VP0006` VC007、`VP0007` VC003。
- VC001/VC002/VC004/VC005/VC006/VC008 仍 unplaced；既有 Motion placement 保持 `NOT_YET_VALIDATED / WARNING`；B011 需人工听音确认；B018 `588.11–620.14s` trailing ad-lib 仍只保留 A-roll。

### 4. Preview / QA

- 全长真实 Remotion Preview（无 fixture）路径：`/Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/DeepTalk-Aligned-Edit-safe-cue-completion-20260821/outputs/ALIGNED_PREVIEW-r0001.mp4`。
- 规格：1920×1080、30fps、H.264 + AAC、`620.533333s`、955,193,338 bytes，SHA `afa27c6f0f5e09e3e53f65a471e565d07c0d163f1b7806515c1d69c1a1184606`；visual-only master SHA `a0b26dc13cbab2ed8510c5a3b31dd51555d1597c7099a26c7c7e3d3210657d23`。真实全长渲染/封装约 30 分钟完成，无进程遗留，未覆盖历史 Preview。
- Preview Manifest digest `764e715698e5078cab9ddeaa97eb11eae1e1fd60dd91c53482ffeb31f8c16970`；Canonical Edit Bridge QA digest `9af393da0599f5659317010b4665349ce405c2ef04490a7a5f3ddb1d85d1ae2c`，6/6 checks pass、0 blocking，唯一 warning 为预期 `EBI0001 partial_placement_unready`。
- 已检查 VC003 约 165s 和 VC007 约 491s 的真实帧：来源图/法条在上方，Basic Subtitle 在安全区，未混入 Motion；Human Preview Gate 仍等待用户完整观看。

### 5. 测试与当前版本

- 完整测试：`460 passed, 3 skipped`；本轮相关定向回归：`52 passed`。本轮没有新增功能代码或测试源码，验证通过正式 artifact replay、真实渲染、ffprobe、Manifest/SHA binding 和 Canonical QA 完成。
- 当前状态：`REAL USER MATERIAL PLACEMENT = PASS for VC003/VC007`；`REAL USER MOTION PLACEMENT = NOT_YET_VALIDATED / WARNING`；`REAL USER FULL PREVIEW = TECHNICAL PASS / AWAITING HUMAN`；`V1.0 Candidate — Unreleased`。

### 6. Git / Release

- 分支：`agent/audio-alignment-edit-bridge`。本轮开始 HEAD：`f35f19405da44e64acbc6cb1387acaf9cf08ccce`；本轮仅提交 HANDOFF/CHANGELOG 文档，最终提交 SHA 见本轮最后一次 commit。
- canonical main HEAD、正式 `v0.6.1` peeled tag commit 均仍为 `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`；main 未修改，v0.6.1 未改写，无新 tag、无新 Release。

### 7. 下一步

先由用户完整观看新 Preview 并提出画面反馈；只有用户确认后，才由 ChatGPT Review 本轮 Material/Preview 并正式安排 Audio Alignment + Edit Bridge。不得因本轮技术 QA PASS 跳过 Human Preview Gate。

---

## 2026-08-21：本轮最终交接摘要（SAFE-CUE completion）

1. **任务 / 完成**：只为 VC003/B006、VC007/B016 取得真实页面/法条 capture，完成新的 Material r1→reviewed r2、Production canonical rebind、Edit Bridge r1、全长真人 Preview；没有修改 Script、Research、Transcript、Alignment、Subtitle 或既有 Motion。
2. **Gate / QA**：Material Review `PASS`；Production QA `PASS`；Canonical Edit Bridge QA 6/6 `pass`、0 blocking、唯一预期 warning `EBI0001 partial_placement_unready`；Human Preview Gate 尚未完成。
3. **关键产物**：Material `MAT-20260821-safe-cue-completion-01` r2 digest `756f417948c2c7a91bfdf2f7f0b0c5037c9d0684a4134a154cb0c1aeeecf9e5a`；Capture Manifest digest `1e80d03a04f28e9783a4981aaba1cc91db738cdd244e1e5d7f9c1880c33d5c2e`；Production `PROD-20260821T170000-safe-cue-completion-01` digest `a63217f219130119b4360bf1d392a223542d68d40ad2cddb1a5155226140ca13`；Bridge `BRIDGE-20260821-safe-cue-completion-01` digest `74108d721bd27cdea6459cdf9c1b9099c72fba3f26520fa36fbe8e14ca2051ca`。
4. **当前架构 / placements**：新的 Material View → 既有 Motion canonical rebind → 既有 Transcript/Alignment/Basic Subtitle → 新 Bridge → Remotion Preview → Canonical QA。Preview 只 staged `VP0000` A-roll、`VP0006` VC007、`VP0007` VC003；Motion 没有进入 Preview。
5. **真实时间 / 素材**：VC003 `162.55–174.48s`，Preview `162.55–169.55s`；VC007 `488.77–512.12s`，Preview `488.77–495.77s`。VC003 SHA `d75611aaf0372f3c3ab5ca42c16ec3b380eca7a008bc6027a185ae1e167641d6`；VC007 SHA `16e60b0a2a4476e603e863dff5f74953c9552b352ccdb343a167b02f8dcfa66e`。未放置 VC001/VC002/VC004/VC005/VC006/VC008；B011 warning、B018 trailing ad-lib 保留。
6. **Preview / QA 输出**：`/Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/DeepTalk-Aligned-Edit-safe-cue-completion-20260821/outputs/ALIGNED_PREVIEW-r0001.mp4`，1920×1080、30fps、H.264/AAC、620.533333s、955193338 bytes，SHA `afa27c6f0f5e09e3e53f65a471e565d07c0d163f1b7806515c1d69c1a1184606`；Manifest `764e715698e5078cab9ddeaa97eb11eae1e1fd60dd91c53482ffeb31f8c16970`；QA `9af393da0599f5659317010b4665349ce405c2ef04490a7a5f3ddb1d85d1ae2c`。
7. **测试 / 人工检查**：项目回归 `460 passed, 3 skipped`；定向 Material/capture/Production/Alignment/Edit Bridge `52 passed`；已抽查 165s 的 VC003 与 491s 的 VC007 帧，来源文字在画面上方、字幕在安全区且无 Motion 混入。两张 capture rights 均保守 `editorial_reference_only/reference_only`，未声称版权许可。
8. **已知 gap / 决策**：Motion status 仍 `NOT_YET_VALIDATED / WARNING`；Human Preview Gate 等用户观看；本轮没有开始 Audio Alignment + Edit Bridge；不要因 warning 宣称 V1 完成。
9. **Git / Release**：分支 `agent/audio-alignment-edit-bridge`，本轮开始 HEAD `f35f19405da44e64acbc6cb1387acaf9cf08ccce`；本轮只提交文档；canonical main 与 v0.6.1 tag 仍 `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`，无新 tag/Release。
10. **需要产品经理决定**：Review 新 Material completion、两张 capture 的来源与全长 Preview；若通过，再正式安排 Audio Alignment + Edit Bridge。
11. **给用户的下一步**：只需完整观看上述新 Preview，然后直接告诉 Codex 哪一处画面需要修改；不要打开终端、JSON 或输入时间码。

## 2026-08-21：SAFE-CUE REAL MATERIAL COMPLETION + REAL USER VISUAL PREVIEW

### 1. 本轮任务是什么

在不修改 reviewed Script、approved Research、Transcript、Alignment、Basic Subtitle 或既有 Motion
语义的前提下，完成真实用户 Clean A-roll 的两个安全 Cue：VC003/B006 与 VC007/B016。为这两个 Cue
取得真实页面/法条截图，重新通过 Material Gate，建立新的 Production / Edit Bridge revision，生成一份
不覆盖旧工件的 620 秒全长真人预览，并停在用户人工观看 Gate。

### 2. 完成了什么

- 实际打开并保存了 AISI 官方研究说明页 Figure 1（VC003）与加州官方 SB-53 Section 22757.13(c)(1)-(2)
  法条摘录（VC007）；没有使用 fixture、合成图片、猜测时点或访问控制绕过。
- 创建新的不可变 Material Package lineage：`MAT-20260821-safe-cue-completion-01`，r1 → reviewed r2，
  Material Review `MRV-20260821-safe-cue-completion-01`，Material Gate `PASS`，r2 digest
  `756f417948c2c7a91bfdf2f7f0b0c5037c9d0684a4134a154cb0c1aeeecf9e5a`。旧 `MAT-c29080...` r2 未改写。
- 新 capture manifest digest 为
  `1e80d03a04f28e9783a4981aaba1cc91db738cdd244e1e5d7f9c1880c33d5c2e`：VC003/M003 PNG 254,016 bytes，
  SHA `d75611aaf0372f3c3ab5ca42c16ec3b380eca7a008bc6027a185ae1e167641d6`；VC007/M007 PNG 45,367 bytes，
  SHA `16e60b0a2a4476e603e863dff5f74953c9552b352ccdb343a167b02f8dcfa66e`。两者历史 rights 仍保守为
  `editorial_reference_only/reference_only`；这没有被误写成取得版权许可，且 rights 不参与 Production Gate。
- VC003 使用当前 Alignment 的 `162.55–174.48s` 语义窗口，Preview 实际展示 `162.55–169.55s`；
  VC007 使用 `488.77–512.12s`，Preview 实际展示 `488.77–495.77s`。未放置 Cue 仍为
  `VC001, VC002, VC004, VC005, VC006, VC008`；B011 仍 `needs_review`；B018 `588.11–620.14s`
  trailing ad-lib 仍只保留在 A-roll。
- 从新 Material Package 生成 Production Plan `PROD-20260821T170000-safe-cue-completion-01`，digest
  `a63217f219130119b4360bf1d392a223542d68d40ad2cddb1a5155226140ca13`。逐项核对旧 approved Motion 的
  scene/payload 语义、文件大小与 SHA 后，仅做 canonical rebind，没有重新渲染 Motion；新 Motion Manifest
  digest `86034a61dc4b11432e20254753e37aa73e80b07cb59080086faaaebb550491d7`，Production QA digest
  `fcfa194c74a08b1c830001a1b69d27abfe38b915d81d595f9a4e515ba820dbd9`，Gate `PASS`。
- 新 Edit Bridge `BRIDGE-20260821-safe-cue-completion-01` r1，digest
  `74108d721bd27cdea6459cdf9c1b9099c72fba3f26520fa36fbe8e14ca2051ca`；新的真实用户输出根目录为
  `/Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/DeepTalk-Aligned-Edit-safe-cue-completion-20260821/`。
- 使用既有 immutable local whisper.cpp Transcript、Timestamp Mapping、Alignment `ALIGNMENT-96854be79b9048a2b6800e1313efb2a6`
  （digest `b71ccfcbe1decb71a48c2901daba1f0627596f4c95c9d191dd3c1fb3a351dce0`）和既有 Basic Subtitle；没有重新转写。
- 新全长 Preview：
  `.../outputs/ALIGNED_PREVIEW-r0001.mp4`，1920×1080、30fps、H.264 + AAC、`620.533333s`、
  955,193,338 bytes，SHA `afa27c6f0f5e09e3e53f65a471e565d07c0d163f1b7806515c1d69c1a1184606`；visual-only
  master `ALIGNED_PREVIEW_VISUAL-r0001.mp4` SHA `a0b26dc13cbab2ed8510c5a3b31dd51555d1597c7099a26c7c7e3d3210657d23`。
  Preview Manifest digest `764e715698e5078cab9ddeaa97eb11eae1e1fd60dd91c53482ffeb31f8c16970`。

### 3. 创建 / 修改的重要文件

- Git tracked：`HANDOFF.md`、`CHANGELOG.md`。
- Git-ignored canonical artifacts：新 Material r1/r2 与 Review、capture manifest、Production Plan / Motion Manifest /
  Production QA，以及新 Edit Bridge / Preview / Manifest / QA，均位于上面列出的日期化目录。
- 新 Preview 的人工检查帧：`.../visual-checks/VC003-at-165s.png` 与 `.../visual-checks/VC007-at-491s.png`。
- reviewed Script、approved Research、既有 Material r2、既有 Alignment、既有 Motion 输出和旧 Preview 均未覆盖。

### 4. 当前架构

```text
reviewed Script + approved Research
  → immutable Material completion r1/r2 + actual capture manifest
  → Material Production View（仅 M003/M007 capture 为 ready）
  → existing approved Production/Motion canonical rebind（不重新渲染）
  → existing Transcript / Alignment / Basic Subtitle
  → new Edit Bridge r1
  → Remotion full-length Preview（A-roll + VC003/VC007 real image + Basic Subtitle）
  → Canonical Edit Bridge QA
```

Preview 实际 staged placement 只有 `VP0000`（A-roll）、`VP0006`（VC007）和 `VP0007`（VC003）；
既有 Motion 没有进入 Preview。

### 5. 已经可以运行什么

- 可以观看新的全长真人预览并核对两个真实素材的语义位置。
- Material Capture Manifest、Material Production View、Production Plan、Motion Manifest、Production QA、
  Edit Bridge、Preview Manifest 和 Canonical QA 均可按 digest 重放。
- Full project test：`460 passed, 3 skipped`；Material / capture / production / alignment / Edit Bridge
  定向回归：`52 passed`。
- Canonical Edit Bridge QA：6 项 revalidation 全部 `pass`，blocking failure `0`；唯一 issue 是预期的
  `EBI0001 partial_placement_unready` warning，因为另外 6 个 Cue 和既有 Motion 仍未有安全语义时点。

### 6. 还不能运行什么

- 还不能声称真人 Clean A-roll E2E 最终完成：用户尚未人工观看并确认新 Preview，且既有 Motion placement 仍为
  `NOT_YET_VALIDATED / WARNING`。
- 不包含 Audio Alignment + Edit Bridge 新功能、音频对齐、字幕升级、BGM/SFX、标题、封面或发布能力。
- 不能把 `editorial_reference_only` capture 解读为已取得第三方版权许可；如将来需要正式发布，仍需单独做版权/授权判断。

### 7. 已知问题 / warning / gap

- `EBI0001 partial_placement_unready` 是 warning，不是 blocking failure；未就绪素材和 Motion 被 fail-closed 排除。
- B011 的人工听音确认仍未完成；本轮不利用 B011 做素材落位。
- B018 trailing ad-lib 保留在真人 A-roll 尾段，未自动安排任何素材。
- VC003 使用 AISI 页面中实际下载的 Figure 1，页面截图复用权未被宣称为已获许可；VC007 是官方法条截图，
  同样保守记录为 reference-only。两者都保留来源与 SHA，便于后续产品/版权决定。

### 8. 重要技术决策

- 不修改 Script、Research、Transcript、Alignment、字幕或 Motion 语义；时间点只来自当前 approved Alignment。
- 不覆盖旧 Material r2、旧 capture manifest、旧 Bridge 或旧 Preview；用新的 package/session/Bridge/output revision 保存历史。
- 不因新 Material 而强行把旧 Motion 放入 Preview；Motion 只做 canonical rebind 和 SHA/语义等价核验，Real User Motion
  Placement 继续标记为 warning。
- rights 不参与 Production Gate；但 rights 状态仍如实保守，不使用无证据的“可复用”表述。

### 9. 需要产品经理决定什么

1. Review 新 Material Package completion、两个 capture 的来源/语义与新的全长 Preview。
2. 判断 `editorial_reference_only` 的真实页面截图是否足够作为当前试用的辅助素材；这不是 Codex 自动替用户作出的版权授权决定。
3. 如果 Preview 通过，再正式安排 Audio Alignment + Edit Bridge；本轮没有提前开始该功能。

### 10. 建议下一阶段

先完成本轮人工 Preview Gate。只有用户观看完整视频并确认后，才由 ChatGPT 决定是否进入 Audio Alignment + Edit Bridge。

### 11. Git / Release 状态

- 分支：`agent/audio-alignment-edit-bridge`；本轮开始 HEAD：`f35f19405da44e64acbc6cb1387acaf9cf08ccce`。
- 本轮只更新 `HANDOFF.md` 与 `CHANGELOG.md`，代码树没有新增功能代码；本轮最终 commit SHA 以本轮提交记录为准。
- canonical main 与正式 `v0.6.1` tag 仍保持 `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`；没有修改 main、tag，
  没有创建新 Release，V1 仍为 `Candidate — Unreleased`。

## 给用户的下一步操作

你现在只需要完整观看本轮新的 `ALIGNED_PREVIEW-r0001.mp4`，然后告诉 Codex 哪一处画面需要修改；不需要打开终端、
查看 JSON、输入时间码或自己总结。

---

## 2026-08-21：GLOBAL MONOTONIC ALIGNMENT PROJECTION FIX + REAL USER E2E RESUME

> 本节是当前最新状态。本轮实现并验证 ChatGPT 已批准的最小 Alignment 修复；没有改 reviewed Script、approved Research、reviewed Material Package、真人媒体、raw Timed Transcript、ASR、字幕、阈值、main、tag 或 Release。

### 1. 本轮任务与完成内容

- 根因修复：`script-alignment/2` 对完整 Script 与完整 Timed Transcript 只做一次 deterministic
  `align_sequences` pass，再投影 Beat 与 Cue。本地 Beat 不再扫描整条 10 分钟 Transcript。
- 每个 Script lexical unit 保存 exact/numeric/substitution/deletion 与实际 Transcript index/unit/time；每个
  insertion 保存相邻 Script position，并归类为 leading、Beat-local、Beat-boundary 或 trailing。
- Beat 只计算自身 Script span 和确定归属的本地 evidence。既有 accepted/review floors 未改变；少量
  substitution、filler 与非结构性小缺口不再自动使 Beat 失效。真实长缺口、boundary risk 和 ambiguity 继续
  fail closed。
- Cue 直接投影自身 global correspondence。只要 anchor/semantic span 唯一、单调、连续并达到既有 floor，就能
  使用真实 token timing；不再因父 Beat 其他位置的 review item 自动 unplaced。
- 保存新真人 Alignment：`ALIGNMENT-96854be79b9048a2b6800e1313efb2a6` / r0001，digest
  `b71ccfcbe1decb71a48c2901daba1f0627596f4c95c9d191dd3c1fb3a351dce0`。路径在既有 Git 外 session 的
  `alignment/.../ALIGNMENT-96854be79b9048a2b6800e1313efb2a6/`。

### 2. 真实结果与 Gate

- BEFORE：18/18 `needs_review`、213 gaps、8/8 Cue `unplaced`。
- AFTER：17 `aligned`、1 `needs_review`、0 `unmatched`；117 个全局 gap；2 `aligned` Cue（VC003、VC007）、
  6 `unplaced`、0 coarse/needs_review。全局 projection 重放耗时 78.765 秒；没有运行 Whisper。
- B011：仍为 `needs_review`，coverage/similarity `0.906736`，保存真实 13-unit omission 与本地 ad-lib；文本
  本身无法判断是漏讲还是 ASR drop，因此需要听音确认，未伪造修复。
- B018：`aligned/high`；Script 完结后的额外真人尾段保留为 `trailing_ad_lib_transcript_span`，真实时间
  `588.11–620.14s`。它没有被改成 Script 内容，也不污染 B001–B017。
- `GLOBAL MONOTONIC ALIGNMENT = PASS`；`BEAT LOCALIZATION = PASS`；`CUE PROJECTION = PASS`；
  `REAL USER ALIGNMENT = PASS WITH B011 WARNING`。
- 当前 approved Material/Production 的 Motion 只绑定 VC001/VC002/VC008，真实 image items 对 VC003/VC007
  是 `missing_asset`。因此没有任何 ready real image 或 Original Motion placement。`REAL USER MATERIAL
  PLACEMENT = WARNING`；`REAL USER MOTION PLACEMENT = WARNING`；没有伪造或猜测画面。
- 因为没有可安全进入视频的实际素材，未创建新的 Bridge、Preview、Manifest 或 QA，避免生成另一份只有 A-roll
  的伪进展。`REAL USER FULL PREVIEW = BLOCKED`；`CANONICAL QA = NOT RERUN`；`HUMAN PREVIEW GATE = NOT_REACHED`；
  `REAL USER CLEAN A-ROLL E2E = REVISION_REQUIRED`。

### 3. 回归、边界与版本

- 新增匿名 regression：全局单调/deterministic、每 Beat 不吞其他 Beat、局部 insertion、长 omission、trailing
  tail、raw Transcript 文字/时间不变、18/20 substitution Cue、重复/缺词 Cue fail closed、父 Beat 无关 review
  不污染安全 Cue。既有 Alignment、Cue、Edit Bridge 定向 regression 保持通过。
- `script-alignment/1` 仅可历史读取；新 Artifact/validator 使用 `script-alignment/2`，global mapping 是完整
  re-derivation 的一部分，手改 status、time 或 correspondence 均失败。
- ASR wall runtime/RTF 没有持久化为正式真人工件，仍是与本 Alignment 修复无关的 non-blocking observability gap。
- 开发分支：`agent/audio-alignment-edit-bridge`；本轮起点 `0103d4b5881425aa5f6b9013ef8ad9757a7d60cc`。
  产品实现 commit `59cd636070620f909727c60f7f386ae17334459f`（已推送）；交接文档 commit
  `16ad6fdaa651d5f490a0f53d3121a42359dd9e9d`（已推送）。GitHub compare 保持只 ahead、behind 为 0，merge-base 仍是 canonical main
  `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`。`V1.0 Candidate — Unreleased` 保持不变。
  main、peeled `v0.6.1`、tag 和 GitHub Release 均未改变。

### 4. 需要产品经理决定什么

请 Review 全局 mapping / local Beat / independent Cue contract 和真实 After metrics。下一步需要决定：是否允许在不改
Script、Research、现有 Motion 语义的前提下，为已安全对齐的 VC003/VC007 补齐经过正式 Material Gate 的可用素材，
从而恢复真实 Bridge、full Preview 与 canonical QA；或者另行调整 Approved Material/Production Plan。不要开始字幕、
ASR、forced alignment、自动剪口气或 V1.0 Release。

## 给用户的下一步操作

你现在不需要看片、重录、找素材文件、运行命令或自己判断技术问题。请把本次 Codex 回复最底部“请把以下内容复制给 ChatGPT”后的完整文字原样发给 ChatGPT，等待它 Review 本次全局对齐修复，并决定如何处理 VC003/VC007 的正式素材缺口。

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

---

## 2026-08-21：REAL USER ALIGNMENT BLOCKER DIAGNOSIS（只读诊断）

> 本节是当前最新状态。本轮是诊断，不是功能开发：没有重新转写、重渲染、改稿、改 Transcript、改
> Alignment 代码、阈值、Gate 或正式工件，也没有 merge、tag 或 Release。

### 1. 本轮任务与产物

针对第一次真人 Clean A-roll E2E 的 `18/18 needs_review`、`213 gaps`、`8/8 Cue unplaced`，只回答
根因。诊断使用原有真人工件和同一套确定性 normalization / sequence-alignment core；没有用 LLM 语义猜测
时间，也没有生成新的 Alignment / Edit Bridge / Preview revision。

Git 外诊断产物：

- JSON：`/Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/DeepTalk-Aligned-Edit/diagnostics/real-user-alignment-diagnosis-r0001.json`
  ，SHA-256 `6a5bad483bdaee40f2ec5185512aaacbc9c11d7843ea1fbb7ba340c9ec6dd1d7`。
- 人读 Markdown：`/Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/DeepTalk-Aligned-Edit/diagnostics/real-user-alignment-diagnosis-r0001.md`
  ，SHA-256 `114be3bf1f26c10a2b60d5a4f7bcf0a72addc342989cc4b79f8a2a20bd8e0190`。

### 2. Artifact binding verification

所有实际可重算的 binding 均通过：

- Alignment `ALIGNMENT-b3cfeb6801094e03b1b4658bde602760` 精确绑定 Script
  `SCR-301097255e2746ee9550ba8ea38acf01` revision 2；保存的 full-script digest 与当前 r2 重算值一致。
- Material r2 与 Production Plan `PROD-20260813T133848055707` 均绑定当前 reviewed Script r2 的
  content digest `855b0d3c7d39b3e76a7bd18b90293bed93a9026e2b035cf86eadd4c00f6554cd`。
- Alignment 精确绑定真实 Transcript `TRANSCRIPT-e3e949a79e744a3d90aa8a02b9366742` 及其 digest
  `85154b27fed6b9871c4975692b37410d5d79526caa7128cb3d0ccc2d525b92f7`。
- Transcript / Alignment 的 Media ID、Mapping ID/digest 和媒体 SHA 都一致，并指向用户的原始 Clean A-roll
  SHA-256 `39d08733447f78c60b5cc0f737781c8fc3a9d95629d7f92a04902bbe0f8e57ec`。
- 8 个 Cue 的 `(cue_id, beat_id, placement_anchor)` 与 approved Production Plan 完全一致。

没有误用旧 synthetic Transcript、旧 Script revision 或错误的 Material/Production lineage。CASE D 的含义是
现有 Alignment 实现行为有问题，不是 artifact binding 错误。

### 3. Independent ordered diagnostic

在不改变 production 的前提下，使用同一现有 deterministic DP core 对“完整 Script（按 B001→B018 顺序）”和
“完整真实 Transcript”做了一次只读顺序比较，不输出时间码：

- Script normalized lexical units：`2,743`；Transcript：`2,884`。
- Script → Transcript exact/numeric lexical coverage：`94.8232%`；计入 substitution 后 `96.9377%`。
- Transcript → Script exact/numeric coverage：`90.1872%`；计入 substitution 后 `92.1983%`。
- Beat 间顺序违例：`0`。没有证据表明整段口播被大范围重排，也不支持“已不是同一条内容”的 CASE C。
- 原正式 artifact 的 18 个 Beat 中，`18/18` 满足 coverage floor `0.85`，`17/18` 同时满足 accepted
  similarity floor `0.88`；仍然全部 `needs_review`。

### 4. 根因：CASE D 为主因

当前 `_beat_record` 在 Beat 没有“整段逐字精确命中窗口”时，会把该**单个 Beat**与**整条 10 分钟
Transcript**比较。真实口播存在正常小差异，因此 18 个 Beat 都进入该 fallback。

这会造成两个连锁结果：

1. 其他 17 个 Beat 的正常内容，都会成为当前 Beat 的 `transcript_insertion`；
2. 只要出现任意 `transcript_insertion`，实现就加入 `ad_lib_transcript_span` deviation；只有完全无 deviation
   才可能标记 `aligned/high`。

因此，`ad_lib_transcript_span` 在 18/18 Beat 出现，并不是“用户 18 次都大幅加词”的证据，而是逐 Beat
对全片 fallback 的必然结果。B001 更出现 `1,289` 个 candidate windows，覆盖从 `1.27s` 到 `593.83s` 的
几乎整条视频；这不是 1,289 个真实复读位置，而是缺少顺序定位时的算法歧义。

另一个直接证据：正式 artifact 把唯一 `long_gap` 标在 B010；而只读全片顺序诊断显示 B010 最大真实
Script deletion 只有 1 lexical unit，唯一 13-unit deletion 在 B011。这说明独立 Beat→全片比较发生跨段
吸附，不能可靠归因本地 gap。

### 5. 213 gaps 的真实含义

正式 artifact 的 213 条为：147 `ad_lib_transcript_span`、61 `omitted_script_span`、5
`repeated_or_ambiguous_span`。其中 96 条 ad-lib 被记录为 `13+` units，最大甚至 `2,561` units；这些大
ad-lib 主要是“整条 Transcript 中不属于当前独立 Beat 的部分”，不能解释成 96 个真实大段加词。

一次完整顺序诊断得到的实际差异分布：

- Script deletion：84 units / 66 runs，其中 62 个单 unit、2 个双 unit、1 个 3–5 unit、1 个 13+ unit。
- Transcript insertion：225 units / 51 runs，其中 37 个单 unit、10 个双 unit、2 个 3–5 unit、1 个
  6–12 unit、1 个 154-unit tail。
- 除 B011 的 13-unit 缺口和 B018 的 154-unit 额外收尾外，其余大部分是单字、双字、专有名词或正常
  口语变化级别差异。

### 6. 18 Beat audit summary

以下 coverage 为完整顺序诊断，非新的正式 timing；每个 Beat 当前的共同 production failure 都是
`ALIGNER_SENSITIVITY`（全片 fallback 产生 ad-lib）。

| Beat | lexical coverage | 次要差异证据 | 结论 |
| --- | ---: | --- | --- |
| B001 | 95.38% | 1–2 unit 小漏/错词；B001 有 1,289 个假性候选窗 | 正常口语/ASR 小噪声 + sensitivity |
| B002 | 93.86% | `OpenAI→Open`、`Hugging→H`、中文数字→阿拉伯数字 | 专名/数字 ASR 噪声 |
| B003 | 92.86% | 多个单字替代、`Hugging→H` | ASR 小错词 |
| B004 | 96.35% | `Hugging→H`、`Spaces→SP` | 专名 ASR 噪声 |
| B005 | 95.65% | 两个最长仅 2-unit 小缺口 | 小口语差异或 ASR |
| B006 | 97.01% | `地→的`、`结→解`、`果→锁` | 单字 ASR 错误 |
| B007 | 95.73% | 最长单 unit；2 个候选窗 | 小口语/ASR 差异 |
| B008 | 98.18% | `Axios→AC`、`这就是` 3-unit 插入 | 专名 ASR + 小加词 |
| B009 | 92.65% | 单字遗漏/替代；3 个候选窗 | 小差异，非大段重排 |
| B010 | 93.92% | `Open Secure AI Alliance`、`SAFE` 被拆错 | 专名 ASR；不支持正式 long-gap 归因 |
| B011 | 90.67% | 开头“这里有个很容易被忽略的关键”13 units 未见 | 需听音频确认：真人漏讲或 ASR drop |
| B012 | 97.66% | 三个单字错词 | ASR 小错词 |
| B013 | 92.72% | `SAFE` / `Axios` 等专名拆错 | 专名 ASR |
| B014 | 97.97% | `NASA→N`、单字替代 | 专名 ASR |
| B015 | 94.41% | `NASA→N`；“责任洗掉”重复 4 units | 专名 + 重复短语 |
| B016 | 93.84% | `SB` / `SAFE` 拆错；7-unit 重复/变体 | 专名 ASR + 小重复 |
| B017 | 94.32% | 少量单字替代 | ASR 小错词 |
| B018 | 94.19% | 154-unit 未写入 Script 的尾部收束/CTA；另有 5-unit 缺口 | 需听音频确认额外收尾，不影响前 17 Beat 顺序 |

仅从文本证据不能把每个中文单字差异百分之百归为“ASR”或“用户改说”；诊断没有假装知道。清晰的专有名词
错误（如 OpenAI、Hugging Face、Axios、NASA、SAFE、SB）归为 ASR evidence；B011/B018 的较大内容则明确
保留为需要未来听音频确认的局部情况。

### 7. Cue diagnosis（仅诊断，不写 production time）

8 个 Cue 都不是“真人完全没讲”。在完整顺序诊断中：

- VC001、VC002、VC003、VC004、VC005、VC006、VC008 都有一个顺序一致的**部分**候选；分别只受 0–2
  anchor lexical 差异影响。
- VC007“`一般要在十五天内报告`”有唯一 exact literal candidate（`15` 与“十五”受正常数字 alias 处理）。
- 当前 8/8 `unplaced` 的直接原因是 Cue mapper 要求整段 semantic span 全部严格匹配；其 parent Beat 已被
  全片 fallback 置为 `needs_review` 后，Cue 全部得到 `semantic_span_unmatched`，而不是没有说 anchor。

### 8. 正式结论与建议（不实施）

结论为 **MIXED：CASE D 为主因，CASE B 为次因**。

- CASE D：实现的 per-Beat→full-Transcript fallback 使正常真人口播被系统性写成 ad-lib，足以解释
  `18/18 needs_review`、大部分 `213 gaps` 与 `8/8 unplaced`。
- CASE B：B011 有一个 13-unit 缺口，B018 有一个 154-unit Script 外尾段；它们是局部真实风险，不能被
  正常化或静默吞掉。
- 不支持 CASE C：整体 Script→Transcript lexical coverage 94.82%，顺序违例 0；用户没有把整期讲成另一篇。
- 不支持 artifact lineage CASE D：所有 binding 均正确；这里的 CASE D 是实现/contract sensitivity，而非
  工件串线。

当前 fail-closed 行为仍然正确：在当前工件下不能安全生成素材时间码。错误不在于“停止”，而在于停止依据
把非本 Beat 的整片内容错误地计入了本 Beat 的 ad-lib。

建议 ChatGPT 若决定解除 blocker，授权的最小下一步应是：设计并评审一个**全局单调、顺序感知**的
Script→Transcript evidence pass，再从唯一的全局 mapping 投影 Beat/Cue；保持严格的 Cue span、B011/B018
人工 review、raw timestamp、无 Script 覆盖、无阈值放宽和 fail-closed。此建议未实施。

### 9. Git / Release 状态

- 本轮开始 HEAD：`acd229899844c9d8c7d55bcdccb5c5e9260cbb0a`。
- 本轮尚未修改产品代码；仅生成 Git 外 diagnosis artifact，并将最终更新 HANDOFF / CHANGELOG。
- 仍为 `V1.0 Candidate — Unreleased`；main、`v0.6.1` tag、GitHub Release 均不得改变。

## 给用户的下一步操作

你现在不需要重录、看片、对 Transcript、找时间点或改任何文件。请把本次 Codex 回复最底部“请把以下内容复制给 ChatGPT”后的整段文字原样发给 ChatGPT，等待它决定是否进入最小的 alignment architecture 修复设计。

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

---

## 当前轮最终状态：SAFE-CUE REAL MATERIAL COMPLETION

本节位于 HANDOFF 文件末尾，覆盖本轮之前的历史章节；历史内容保留用于审计。

### 任务、边界与 Gate

- 已完成 VC003/B006、VC007/B016 的真实语义素材补齐、Material Gate、Production canonical rebind、Edit Bridge、全长真人 Preview 和 Canonical QA。
- 没有修改 reviewed Script、approved Research、Transcript、ASR、Alignment、Basic Subtitle、旧 Material r2、既有 Motion 或旧 Preview；没有开始 Audio Alignment + Edit Bridge。
- Material `MAT-20260821-safe-cue-completion-01` r2 Review/Gate PASS，digest `756f417948c2c7a91bfdf2f7f0b0c5037c9d0684a4134a154cb0c1aeeecf9e5a`。Capture Manifest digest `1e80d03a04f28e9783a4981aaba1cc91db738cdd244e1e5d7f9c1880c33d5c2e`。
- Approved Alignment `ALIGNMENT-96854be79b9048a2b6800e1313efb2a6`，digest `b71ccfcbe1decb71a48c2901daba1f0627596f4c95c9d191dd3c1fb3a351dce0`；VC003 仅使用 `162.55–174.48s`，VC007 仅使用 `488.77–512.12s`。不猜时点。

### 素材、Production 与 Bridge

- M003/VC003 使用 [AISI 官方页面 Figure 1](https://www.aisi.gov.uk/blog/how-do-environmental-factors-impact-ai-behaviour)，PNG SHA `d75611aaf0372f3c3ab5ca42c16ec3b380eca7a008bc6027a185ae1e167641d6`；M007/VC007 使用 [California SB-53 官方法条页面](https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260SB53)，PNG SHA `16e60b0a2a4476e603e863dff5f74953c9552b352ccdb343a167b02f8dcfa66e`。两者均保留 `editorial_reference_only/reference_only`，未声称版权许可或绕过访问控制。
- Production `PROD-20260821T170000-safe-cue-completion-01` digest `a63217f219130119b4360bf1d392a223542d68d40ad2cddb1a5155226140ca13`；只对既有 approved Motion 做语义/SHA canonical rebind，不重新渲染，Production QA PASS，digest `fcfa194c74a08b1c830001a1b69d27abfe38b915d81d595f9a4e515ba820dbd9`。
- Bridge `BRIDGE-20260821-safe-cue-completion-01` digest `74108d721bd27cdea6459cdf9c1b9099c72fba3f26520fa36fbe8e14ca2051ca`；staged 只有 `VP0000` A-roll、`VP0006` VC007、`VP0007` VC003。VC001/002/004/005/006/008 仍 unplaced；B011 仍需听音确认；B018 `588.11–620.14s` trailing ad-lib 保留 A-roll；Motion placement 仍 `NOT_YET_VALIDATED / WARNING`。

### Preview、QA 与测试

- 全长真实 Remotion Preview：[ALIGNED_PREVIEW-r0001.mp4](</Users/hwang/.cache/deep-talk-studio/transcription/e2e/real-user-clean-aroll-20260821/DeepTalk-Aligned-Edit-safe-cue-completion-20260821/outputs/ALIGNED_PREVIEW-r0001.mp4>)，1920×1080、30fps、H.264 + AAC、`620.533333s`、955,193,338 bytes，SHA `afa27c6f0f5e09e3e53f65a471e565d07c0d163f1b7806515c1d69c1a1184606`；真实渲染/封装约 30 分钟，旧 Preview 未覆盖。
- Preview Manifest digest `764e715698e5078cab9ddeaa97eb11eae1e1fd60dd91c53482ffeb31f8c16970`；Canonical Edit Bridge QA digest `9af393da0599f5659317010b4665349ce405c2ef04490a7a5f3ddb1d85d1ae2c`，6/6 pass、0 blocking，唯一 warning `EBI0001 partial_placement_unready`。
- 项目测试 `460 passed, 3 skipped`；定向回归 `52 passed`。已检查约 165s/491s 真实帧：来源素材在上方、Basic Subtitle 在安全区、无 Motion 混入。Human Preview Gate 仍等待用户完整观看。

### Git / Release / 下一步

- 分支 `agent/audio-alignment-edit-bridge`；本轮开始 HEAD `f35f19405da44e64acbc6cb1387acaf9cf08ccce`；文档收尾提交链为 `3d46f42a68841425b47672d398d3ec1a3c69287b` → `b46e536b30aee0067b361b09b42bc81091dd13e0`。
- GitHub canonical `origin/main` HEAD、正式 `v0.6.1` peeled tag commit 均为 `8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`；`merge-base(origin/main, HEAD)` 相同，当前 compare 为 `ahead 80 / behind 0`。main、tag 未变，无新 Release，V1 仍 `Candidate — Unreleased`。
- 下一步只等待用户完整观看 Preview；确认后由 ChatGPT Review 本轮 Material/Preview 并正式安排 Audio Alignment + Edit Bridge，不得用技术 QA PASS 跳过人工 Gate。
## 2026-08-24：REAL USER VISUAL PRESENTATION MODE FIX + OUTPUT-TRUTH QA

当前正式版本：V0.6.1 / `v0.6.1`
当前产品状态：V1 Candidate — Unreleased；真实用户 Full Visual Preview 已生成，等待人工观看 Gate
仓库：https://github.com/HWang0310/deep-talk-studio
当前开发分支：`agent/audio-alignment-edit-bridge`

### 本轮完成

- 修复了真实 E2E 中“素材和 Motion 只占上方、下方长期保留 A-roll”的呈现错误。已经批准的全屏素材和 Motion 现在作为主画面完整占据 1920×1080；其间字幕仍在最上层；窗口外回到真人 A-roll。
- 没有改变 reviewed Script、approved Research、Fact Check、Transcript、Alignment、approved Material、Visual Plan、A-roll 或默认偏好。B011 仍为 unplaced/needs-review 警告，B018 尾段仍是 A-roll。
- 增加受控 `primary_visual`、`primary_visual_with_pip`、`supporting_overlay` renderer contract；未从任何机器文本重开编辑解释入口。
- 增加 `output-truth-evidence/1`：保存 final MP4 的 pre/in/post 抽帧、SHA 和绑定；正式 Full Visual Preview 少此证据时 canonical QA 直接 fail。
- 真实输出：`ALIGNED_PREVIEW-r0003.mp4`，H.264 1920×1080 30fps，AAC 单一 Clean A-roll 音轨，620.533333 秒，878,626,034 bytes，SHA-256 `6494ac0ebf60e0d888d6fe2dc9dbfa02f7dc5cbd33c3f0156e27c1894b1e15eb`。
- 真实 Output-Truth digest：`631989274c4363ed357c0af56553aa44d867fb6dbed43fc9e28371360e51bae4`；抽样 VP0001–VP0005 全部为 primary visual。人工检查确认 Timeline/Motion、Hugging Face 真实材料均为全画面，窗口结束恢复真人 A-roll。
- Canonical Edit Bridge QA：`warnings`，digest `e6d301dc8f69d8ca929b2532af072a9fa48b15fbaa5ddc806c3bef5310db00b9`；唯一 warning 是既有 B011 `partial_placement_unready`，没有 blocking failure。Remotion project validation、ffprobe 和完整项目测试均通过（483 passed，3 skipped）。

### 当前 Gate

工程、绑定、成片输出和自动 QA 已通过；下一步是人工观看新粗预览。没有 main/tag/Release，仍未开始任何新功能。

### 给用户的下一步操作

请观看新的 `ALIGNED_PREVIEW-r0003.mp4`。满意则回复“预览通过”；如不满意，直接说出画面位置或问题。
## 2026-08-24：Visual Asset Engine MVP Design（设计草案，等待 ChatGPT Review）

### 本轮任务与完成内容

将已完成的高级动画研究转化为 DeepTalk V1 的产品/技术合同；这是设计轮，不实现 Renderer、不生成正式动画、不修改生产逻辑、不创建 Release。已完成 `Visual Director` 四选一决策、MG Motion Grammar、Advanced Motion Spec、Asset Manifest、Edit Map、自然语言 Human Review、Gates、Fallback、V1/Later 分界及第一条真实 episode 验收设计。

### 重要文件

- `docs/superpowers/specs/2026-08-24-visual-asset-engine-mvp-design.md`：完整设计草案。
- `CHANGELOG.md`：只记录本轮实际完成的设计工作。
- 本仓库外研究证据保持在 `/Users/hwang/Movies/自媒体创意库/Codex动画参考/研究报告/`，未进入 Git。

### 当前建议架构

`reviewed Script + approved Research + reviewed Material + Clean A-roll + Alignment` → `Visual Director` →
`KEEP_A_ROLL / REAL_MATERIAL / MG_MOTION / ADVANCED_MOTION` → 自然语言 Visual Plan Review →
Spec/Asset QA → 独立 Asset Pack + Edit Map → 用户 NLE 手工剪辑。

时间只从 Alignment 来；事实和显示文字继续绑定 Research/Material；MG 是高频确定性解释工具；Advanced Motion 仅为少量认知高潮。核心路径不依赖用户额外 API Key，图像生成只可作为未来 optional/experimental adapter。

### 已经可以运行什么 / 仍不能运行什么

现有 Research、Material、Production、Alignment、Edit Bridge 与 Preview 能力维持原状。本轮没有新可运行 Renderer、没有新视频、没有新真实 asset，也没有修改 reviewed Script、approved Research、reviewed Material、Transcript、Alignment 或 Production 工件。新合同尚未实现，必须先经 ChatGPT Review 后另开实现轮。

### 产品决策与待定问题

- 首批真实验收建议只测 3 个不同 MG、1 个 SVG/path、1 个概念隐喻，而不是全片自动制作。
- 建议 V1 先用中性、克制、非角色 IP 的视觉 Profile；不得复制“小黑”IP或参考作者表达。
- 需 ChatGPT 决定首期是否对全部 Visual Plan 一次性确认，以及 Edit Map 首批仅 Markdown+CSV 还是需要特定 NLE 项目导出。

### Git / Release 状态

设计完成时无功能 commit、无 push、无 PR、无 tag、无 Release；`main` 和 `v0.6.1` 未改。随后已按仓库规则将获批设计与实施计划作为独立文档 commit，功能实现将另起 feature commits。

### 给用户的下一步操作

把本轮 Codex 的完整交接文字原样发给 ChatGPT，请它 Review `Visual Asset Engine MVP Design`，确认 MVP 边界、首批动画能力和第一条真实 episode 验收方案，再给出下一轮正式实现任务。

## 2026-08-24：Visual Asset Engine MVP Foundation（实现中，待 Review）

### 本轮实际实现

- 新增 `visual-director-plan/1` 的最小机器合同：必须引用 64 位 Alignment digest，所有窗口只从 Alignment cue range 投影；proposal 自带 start/end/duration 会失败；未升级时默认 `KEEP_A_ROLL`。
- 新增 `motion-spec/1`：首批允许 timeline、causal chain、comparison/mechanism、SVG/path、controlled conceptual metaphor；事实文字无 binding、超容量或 Advanced 未经 Review 一律拒绝。Advanced fallback 固定为 MG → real material → A-roll。
- 新增共享 primitive payload（text/shape/line/arrow/node/card/path/reveal/transition 的最小组合）及无外部 API 的本地 fixture renderer。
- 新增 `visual-asset-manifest/1`、用户目录 `06_真实素材` 至 `09_剪辑表`、`_DeepTalk记录`，以及不暴露 SHA/内部 ID 的 Markdown/CSV Edit Map。
- fixture 成功输出 3 个 MG、1 个 path、1 个 controlled metaphor，共 5 个独立 1920×1080 MP4；ffprobe、SHA、manifest 与 Edit Map 一致性通过。fixture 不是真实 episode 验收。

### 重要文件

- `src/deeptalk_studio/visual_director.py`
- `src/deeptalk_studio/motion_spec.py`
- `src/deeptalk_studio/visual_asset_renderer.py`
- `src/deeptalk_studio/visual_asset_pack.py`
- `src/deeptalk_studio/edit_map.py`
- `evaluations/visual_asset_engine/fixture_episode.py`
- `tests/test_visual_director.py`、`tests/test_motion_spec.py`、`tests/test_visual_asset_renderer.py`、`tests/test_visual_asset_pack.py`、`tests/test_visual_asset_engine_fixture.py`

### 真实限制 / 下一步产品问题

本机 ffmpeg 9.0.1 没有 SVG decoder 和 `drawtext` filter。因此 fixture renderer 的路径和节点 reveal 是真实、确定性的图形动画，但最终 MP4 尚未显示已绑定的中文标题/标签；binding Gate 已在 Spec 层执行，却不能把它当成完整的 Neutral Editorial 文本渲染完成。下一实现轮应复用现有 Remotion renderer（或确认另一已安装的文字渲染路径）来完成中文 display-text 输出，再开始真实 episode。

### 测试与 Git

- 新增定向测试 7/7 通过；完整项目回归 `493 passed, 3 skipped`。
- 本轮未修改 main、`v0.6.1` tag 或 Release；未开始真实《牛来》或任何真实选题/资产。

### 给用户的下一步操作

把本轮 Codex 完整交接发给 ChatGPT，请它 Review MVP 基础实现，重点确认“中文 Display Text 必须迁移到现有 Remotion 文字渲染后才可进入真实 episode”的 blocker，并决定下一轮是否只做该 renderer hardening。
