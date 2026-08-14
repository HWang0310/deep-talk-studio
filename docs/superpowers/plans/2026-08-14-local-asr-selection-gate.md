# DeepTalk Studio V1 本地 ASR 选择 Gate

## 目标

在把任何本地转写引擎设为 V1 默认前，用同一段非私人中文单人音频，对官方
`whisper.cpp` multilingual medium 与 Microsoft `VibeASR.cpp` /
`VibeVoice-ASR-BitNet` 做可复现的候选验证。重点先验证能否提供可靠的媒体时间戳，
再比较中文准确性、专有名词、速度、资源和维护复杂度。模型与音频只保存在项目外部
缓存，不提交到 Git。

## 执行步骤

- [x] 固定官方仓库版本、模型身份、下载来源和本机硬件/加速条件。
- [x] 在项目外缓存构建两套官方运行时，并记录源码 commit、模型文件大小与 SHA-256。
- [x] 创建一段 2–5 分钟、非私人、单人中文评测音频及其公开的参考文本；两套候选使用
      完全相同的输入。
- [x] 分别运行候选，保存原始输出摘要、时间戳粒度、运行时间/RTF、中文与专有名词
      差异，并确认是否有真实 token 时间戳；不做插值或模型猜测。
- [x] 对每个候选做最小适配链：本地输出 → `ProviderTranscript` → Timed Transcript
      → 现有 Script Alignment；不能提供所需信息的候选在此处标记失败并停止深入接入。
- [x] 依据证据选择 V1 默认本地 Provider，或明确 Gate 阻塞；保持 Provider-neutral
      边界，不接入任何 API key，不做云端默认路径。
- [x] 运行完整测试和 Production 定向 regression，更新 README、ROADMAP、CHANGELOG、
      HANDOFF，提交并推送开发分支；不创建 v1.0.0/rc 或其他正式 Release。

## Gate 规则

1. 没有可靠媒体时间戳即失败；只有 segment 时间戳必须标为 `coarse`，并真实跑过
   Alignment 验证；只有供应商直接提供 token 时间戳才可标为 `token`。
2. 不允许用字符位置、平均分配或 LLM 猜测制造时间戳。
3. V1 不依赖 `OPENAI_API_KEY` 或任何第三方 API key；现有 OpenAI Provider 仅保留为
   后续可选能力。
4. 评测失败、模型下载失败或环境不稳定必须如实记录，不能用 fixture 或伪造成功结果。

## 交付物

评测报告、候选原始输出摘要、适配与 Alignment 证据、Gate 判定、缓存清单和人工
审核说明会进入版本控制；大模型文件、音频和临时构建目录保持在项目外部。
