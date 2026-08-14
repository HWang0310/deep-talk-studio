# DeepTalk Studio V1 本地 ASR Selection Gate

日期：2026-08-14  
状态：Gate 完成；推荐结果等待 ChatGPT Review，尚未接入 V1 默认生产入口  
分支：`agent/audio-alignment-edit-bridge`

## 评测边界

本轮没有执行旧的“直接采用 whisper.cpp”方案，也没有修改 reviewed Script、approved
Research、reviewed Material Package 或任何正式 Production 工件。评测只比较两个官方
候选的本地运行时；模型、音频和原始日志均保存在项目外部缓存，不进入 Git。

同一份音频用于两个候选：

- 外部缓存文件：`eval_cn_single_speaker_24k_mono.wav`
- 24 kHz、单声道、PCM 16-bit、272.367458 秒、13,073,716 bytes
- SHA-256：`c1b08fe694eb59d598af2fb06b29f165ee341afc82048e999ddb362dceeba601`
- 参考文本 SHA-256：`f887be03855e67328195353d5526c88165b366e2054996b16378857b309dea4f`
- 音频由 macOS `say -v Tingting -r 220` 从非私人评测文本生成；没有用户视频、私人录音、
  API Key 或云端上传。它适合验证名词、数字和时间轴工程，但不是用户真人音色，因此
  真人口音/停顿泛化仍是 production gap。

## 候选 A：官方 whisper.cpp multilingual medium

- 源码：[`ggml-org/whisper.cpp`](https://github.com/ggml-org/whisper.cpp)，release `v1.9.2`
- 源码 commit：`306c88f4d1286aec1bf96e544632897886af5501`
- 模型来源：[`ggerganov/whisper.cpp` medium](https://huggingface.co/ggerganov/whisper.cpp)
- 模型文件：`ggml-medium.bin`，1,533,763,059 bytes
- 模型 SHA-256：`6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208`
- 本机：Apple Silicon M4、24 GiB；源码构建启用 Metal，运行日志确认 `using MTL0`、
  `found device: Apple M4`。
- 命令使用 `--language zh --dtw medium --output-json-full`；JSON 的整数 `offsets`
  来自 runtime token timestamp，未做字符插值、平均分配或 LLM 猜测。
- 实际 wall runtime：44.37 秒；272.367458 秒音频的 wall RTF：0.1630。whisper 内部
  timing 的 GPU total 为 37.40016 秒，作为附加证据保留在外部 stderr 日志。
- 输出：1,136 个可用于 ProviderTranscript 的真实 token units；最小适配链通过：
  `ProviderTranscript(token)` → `Timed Transcript`（digest
  `6e7bb2cccbd0c720ac5c8f962629b23617530f7abb499235c2edeb5a00a50d41`）→
  `Script Alignment`，首个 Beat 为 `aligned/token`，真实起止 `0.05–3.41s`。
- 同音频合成文本对照的字符差异率约 5.31%（仅作 TTS 参考，不冒充真人 WER）。明显
  错误包括：`OpenAI→OpenEye`、一次 `DeepSeek→DeepSeq`、一次 `AI Agent→AI Agit`、
  `昇腾→生酮`、一处 `GPU→GTU`。`Anthropic`、`DeepSeek`、`华为`、`英伟达`、`GPT`、
  `AI Agent`、`Metal`、`RTF` 至少有一次原样出现。

## 候选 B：Microsoft VibeASR.cpp + VibeVoice-ASR-BitNet

- 源码：[`microsoft/VibeASR.cpp`](https://github.com/microsoft/VibeASR.cpp)
- 源码 commit：`5cbce71c65911a7e10639ac13b6ab6929e4c8f9e`
- 模型 revision：[`microsoft/VibeVoice-ASR-BitNet@66e7802`](https://huggingface.co/microsoft/VibeVoice-ASR-BitNet/tree/66e7802)
- LM：`vibeasr-lm-i2_s-embed-q6_k.gguf`，992,877,600 bytes，SHA-256
  `fbe273d8dc2f2433bb25f849e19d77ea65aaa2188d12c20cee987ab6f321e002`
- VAE：`vibeasr-vae-encoder-i8_s.gguf`，703,080,064 bytes，SHA-256
  `4941c82608c253ec066b5cc74d3dd11a5c8fef96cccbc5b87359ef0fe4338df6`
- 合计模型约 1.70 GB（十进制；官方标称约 1.58 GiB）。本机以 Clang CPU 构建，Metal
  关闭；官方 `BITNET_ARM_TL1=ON` 配置在本机编译失败，改为关闭 TL1 后使用官方 I2_S
  路径构建成功。这一 bootstrap 差异记录为维护 warning。
- 同一音频真实运行两次：JSON prompt wall runtime 331.97 秒、RTF 1.2109；默认 text
  prompt wall runtime 284.17 秒、RTF 1.0402。
- 两种模式都耗尽 `max_tokens` 并输出重复文本；没有 runtime-owned 的音频 token/word
  offsets。官方 CLI 的 `Start/End` 只是 prompt 要求模型生成的字段，不是可由音频帧
  或声学编码重推导的时间证据。因而适配链在 `ProviderTranscript` 处停止，不生成
  Timed Transcript 或 Script Alignment。
- Timestamp Gate：**FAIL**。不能把模型生成的 Start/End、字符位置或平均分配冒充媒体
  时间戳；速度/模型大小不能弥补这个失败。

## Gate 结论

推荐 `whisper.cpp multilingual medium` 作为 V1 默认本地 Provider 候选：它是唯一通过
可靠 token timestamp hard gate、并在同一音频完成现有 `ProviderTranscript → Timed
Transcript → Script Alignment` 的候选。VibeASR 在本机还同时暴露中文输出退化、重复解码和
RTF 约 1.04–1.21 的问题。

这不是新的正式产品版本，也不是 V1.0 发布。V1 默认生产集成仍标记为
`PENDING_CHATGPT_REVIEW`；若 Review 通过，只有 winner 模型允许自动 bootstrap，模型仍
放在项目外部/用户级缓存，loser 不会被提交仓库。

## 代码与验证

- 新增 evaluation-only parser：`src/deeptalk_studio/transcription/local_asr_selection.py`；
  它只接受 whisper.cpp 直接 token offsets，并固定拒绝 VibeASR prompt-generated times。
- 新增复现脚本：`evaluations/local_asr_selection/run_selection_gate.py`；真实结果摘要保留
  在外部 `local-asr-selection-report.json`，不提交大模型、音频或原始长日志。
- 新增 3 个 parser/Gate regression；全套项目测试、Production 定向 regression 和
  Remotion 既有检查将在本轮提交前重新运行。
- `OPENAI_API_KEY`、Anthropic、Google 等 API Key 均不是本轮依赖；现有 OpenAI Provider
  仅保留为未来可选 V2/V3 能力。
