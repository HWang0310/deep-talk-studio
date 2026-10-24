# DeepTalk Studio — Current Control Plane

> **2026-10-24 GitHub-verified integration snapshot, not a live status service.** On every recovery first check remote `main`, relevant Issue/PR exact SHAs and local dirty/worktree state. [PROJECT_STATE.md](PROJECT_STATE.md) owns formal release / accepted capability facts; [AGENTS.md](AGENTS.md) owns guardrails and canonical engineer roster. Historical handoffs and plans are not default next actions.

## 当前一句话
**当前唯一开发主线是原 [PR #48](https://github.com/HWang0310/deep-talk-studio/pull/48) 的“五视频口播提取工具”，Codex 单一执行，Nexus 待复审。** 最新 Owner 需求以 [issuecomment-6384621479](https://github.com/HWang0310/deep-talk-studio/pull/48#issuecomment-6384621479) 为准，取代旧自动热门搜索/四步创作/三稿默认流程：用户自带1～5链接→显式本批授权→本地下载/FFmpeg/Whisper→逐视频完整TXT+JSON与全文合并导出；可选明确调用模型融合一篇稿。原分支继续，不新开PR、不合并/发布。

## 已确认状态与产品边界
- **最新正式发布仍为 [v1.0.0](https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0)**；当前 `main` 已包含 post-release Creator Workbench、DeepSeek 设置、参考视频分析、显式 Search/Fetch、音频交付 UI、浏览器验收、Chat-first 多会话与未审核 Creative Draft。**已合并代码不等于新版本已发布、本机服务已自动升级、真实视频已完成。**
- 已合并的功能 PR：[ #39](https://github.com/HWang0310/deep-talk-studio/pull/39) → [#40](https://github.com/HWang0310/deep-talk-studio/pull/40) → [#41](https://github.com/HWang0310/deep-talk-studio/pull/41) → [#42](https://github.com/HWang0310/deep-talk-studio/pull/42) → [#43](https://github.com/HWang0310/deep-talk-studio/pull/43) → [#45](https://github.com/HWang0310/deep-talk-studio/pull/45)。最终集成提交为 `fcb0b6d4c12208cf86a589211fe8a43f05f809ef`（后续文档提交将推进 `main` HEAD）。合并使用保留祖先的 merge commit；#42/#43/#45 与项目瘦身文档冲突已明确取新版状态与人员规范，同时保留应用代码和测试。
- Owner 已保存 DeepSeek API Key：稳定用户级 `~/.deeptalk/workbench.local.json`，必须跨工作树/重启复用且不泄露。历史聊天稳定保存于 `~/.deeptalk/chat/`；迁移不得覆盖旧文件，测试 `pytest` / `unittest` 双入口必须隔离真实 Key 与聊天。**不得再次要求 Owner 反复输入 Key。**
- 2026-10-23 Owner 批准 Chat-first 方案 A：自由聊天、真实 SSE、多会话、未审核草稿不强制先做事实核查。**正式** Research / Fact Check / Thesis / Reviewed Script / Rights / Production 的人工审批 Gate 不变；显式付费 Search/Fetch、素材下载、上传私人数据需要适当的授权；真实最终音轨由 Owner 录制或合法提供，剪映编辑/发布由 Owner 完成。
- 内嵌 TTS/声音克隆 [#28](https://github.com/HWang0310/deep-talk-studio/issues/28) 与 V2 后续阶段仍 **HOLD**。不要擅自自动发布、复制他人原创表达、伪造事实来源/模型结果/时间对齐。

## 近期执行顺序
1. 五个粘贴槽支持多行、跟踪参数与BV去重；不自动搜热门，不自动收费。每个视频独立进度、失败重试，已完成记录幂等保留。
2. 原文完整保存并导出，含末尾段落；合并稿按来源顺序标注标题/URL/BVID，失败如实标记。可选单篇指定字数融合，原文永不因模型窗口裁剪。
3. 旧聊天、历史管理、正式工作流保留在高级入口；用户级Key和聊天主存储不迁移、不覆盖。所有正式Gate不变。
4. 浏览器五视频验收使用明确离线工具夹具，不冒称真实平台五视频ASR。真实平台下载需要本批范围授权。最新正式发布仍为v1.0.0。

## Agent 最短阅读
远端当前状态 → [AGENTS.md](AGENTS.md) → 本索引 → 按需 [docs/INDEX.md](docs/INDEX.md) 的 canonical Skill/合同、实现和测试。只有涉及正式产品能力与版本时深入 [PROJECT_STATE.md](PROJECT_STATE.md)。GitHub 最新事实优先，遇到冲突向 Nexus 报告。

**维护规则：** 只更新当前主线/下一步，已完成历史保存在 GitHub PR、CHANGELOG 与 HANDOFF；保持本文件简洁。
