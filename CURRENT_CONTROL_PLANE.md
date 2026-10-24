# DeepTalk Studio — Current Control Plane

> **2026-10-24 GitHub-verified integration snapshot, not a live status service.** On every recovery first check remote `main`, relevant Issue/PR exact SHAs and local dirty/worktree state. [PROJECT_STATE.md](PROJECT_STATE.md) owns formal release / accepted capability facts; [AGENTS.md](AGENTS.md) owns guardrails and canonical engineer roster. Historical handoffs and plans are not default next actions.

## 当前一句话
**当前唯一开发主线是 [PR #48](https://github.com/HWang0310/deep-talk-studio/pull/48)「爆款二创 1.0」一次性交付候选，Codex 唯一执行工程师；Nexus 待审。** Owner 最终验收以 [issuecomment-6383273699](https://github.com/HWang0310/deep-talk-studio/pull/48#issuecomment-6383273699) 为准，结合 6383140012 与 6383162084，已取代旧 Forge-only topic-first 派工。保留原分支 `agent/issue29-topic-first`，不新增 PR、不合并、不发布。

## 已确认状态与产品边界
- **最新正式发布仍为 [v1.0.0](https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0)**；当前 `main` 已包含 post-release Creator Workbench、DeepSeek 设置、参考视频分析、显式 Search/Fetch、音频交付 UI、浏览器验收、Chat-first 多会话与未审核 Creative Draft。**已合并代码不等于新版本已发布、本机服务已自动升级、真实视频已完成。**
- 已合并的功能 PR：[ #39](https://github.com/HWang0310/deep-talk-studio/pull/39) → [#40](https://github.com/HWang0310/deep-talk-studio/pull/40) → [#41](https://github.com/HWang0310/deep-talk-studio/pull/41) → [#42](https://github.com/HWang0310/deep-talk-studio/pull/42) → [#43](https://github.com/HWang0310/deep-talk-studio/pull/43) → [#45](https://github.com/HWang0310/deep-talk-studio/pull/45)。最终集成提交为 `fcb0b6d4c12208cf86a589211fe8a43f05f809ef`（后续文档提交将推进 `main` HEAD）。合并使用保留祖先的 merge commit；#42/#43/#45 与项目瘦身文档冲突已明确取新版状态与人员规范，同时保留应用代码和测试。
- Owner 已保存 DeepSeek API Key：稳定用户级 `~/.deeptalk/workbench.local.json`，必须跨工作树/重启复用且不泄露。历史聊天稳定保存于 `~/.deeptalk/chat/`；迁移不得覆盖旧文件，测试 `pytest` / `unittest` 双入口必须隔离真实 Key 与聊天。**不得再次要求 Owner 反复输入 Key。**
- 2026-10-23 Owner 批准 Chat-first 方案 A：自由聊天、真实 SSE、多会话、未审核草稿不强制先做事实核查。**正式** Research / Fact Check / Thesis / Reviewed Script / Rights / Production 的人工审批 Gate 不变；显式付费 Search/Fetch、素材下载、上传私人数据需要适当的授权；真实最终音轨由 Owner 录制或合法提供，剪映编辑/发布由 Owner 完成。
- 内嵌 TTS/声音克隆 [#28](https://github.com/HWang0310/deep-talk-studio/issues/28) 与 V2 后续阶段仍 **HOLD**。不要擅自自动发布、复制他人原创表达、伪造事实来源/模型结果/时间对齐。

## 近期执行顺序
1. **一个 Writer：Codex；Nexus 审核。** PR #48 原始 topic-first head `ae8e0f2b0fab6872265c4787fc4577524b565bf2` 上继续开发。候选改动与验证记录见 [一次性交付证据](evaluations/remix_one_shot/README.md)。以远端 PR exact head 和本机服务核验为准。
2. **娱乐创作优先。** 输入热点→本轮相关视频按逐视频核验播放量排序→按需参考工作区→显式授权下载/本地转写/叙事分析→犀利吐槽、搞笑玩梗、故事反转三篇完整未审核稿→聊天继续修改。免费草稿无强制新闻核查流程；严重指控不编成事实，原有正式 Gate 保持独立。
3. 验收同时覆盖全文 ASR 的 TXT/JSON 导出、播放量文件名、历史重命名/软删除/恢复、同聊天 A→B 来源隔离与检索等待/超时。Three.js 选择不启用，保留静态轻量装饰；不新增服务订阅。
4. Owner Key/历史仍在稳定用户目录。自动化与破坏性试用只用临时目录；真实模型限定最多4次新调用，证据须区分真实公共检索、真实 DeepSeek、合成媒体/Whisper 夹具。最新正式发布仍是 v1.0.0；本 PR 未合并、未发布，Issue #29 真实成片与 #28 TTS 不因本轮自动完成。

## Agent 最短阅读
远端当前状态 → [AGENTS.md](AGENTS.md) → 本索引 → 按需 [docs/INDEX.md](docs/INDEX.md) 的 canonical Skill/合同、实现和测试。只有涉及正式产品能力与版本时深入 [PROJECT_STATE.md](PROJECT_STATE.md)。GitHub 最新事实优先，遇到冲突向 Nexus 报告。

**维护规则：** 只更新当前主线/下一步，已完成历史保存在 GitHub PR、CHANGELOG 与 HANDOFF；保持本文件简洁。
