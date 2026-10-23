# DeepTalk Studio — Current Control Plane

> **2026-10-23 GitHub verified snapshot（不是自动同步的实时状态）。** 进入项目必须先刷新相关远端 Issue/PR 与 branch HEAD；远端新事实优先。正式验收/发布事实归 [PROJECT_STATE.md](PROJECT_STATE.md)，engineer roster 归 [AGENTS.md](AGENTS.md)。历史交接留在 `HANDOFF.md`，不默认读取。

## 当前一句话
**先完成 Chat-first 对话/原创草稿 MVP 的 PR #45 修正与 Owner 真实体验，再推进首条真实视频 Issue #29。** 不是做新的大重构，也不是启动 V2/TTS。

## 已确认的发布与能力边界
- 最新**正式发布**：[`v1.0.0`](https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0)。`main` 已集成参考发现 [PR #25](https://github.com/HWang0310/deep-talk-studio/pull/25)、本地 Web UI [PR #27](https://github.com/HWang0310/deep-talk-studio/pull/27)、首片 WAV/MP3 音频时间基准窄兼容 [PR #31](https://github.com/HWang0310/deep-talk-studio/pull/31) 与 Workbench 基础 [PR #33](https://github.com/HWang0310/deep-talk-studio/pull/33)；这些 post-release 代码**不等于新的正式发布**。
- [#29](https://github.com/HWang0310/deep-talk-studio/issues/29) 最高**产品结果**：选题 → 必要独立来源/原创稿人工审核（正式路径）→ Owner 外部 VoxCPM2 或自录最终真实口播 → DeepTalk 真实音频时间对齐、素材/剪辑建议 → Owner 剪映人工完成并发布。最终口播可以是经许可的独立 WAV/MP3；CLI 窄适配**已集成、未发布**，不宣称整个 Web UI 已打通音频交付。
- Owner 2026-10-23 选择 **方案 A**：[Issue #44](https://github.com/HWang0310/deep-talk-studio/issues/44) — 默认自由聊天、真实流式回复、可修改和导出 Creative Draft；普通草稿不强制事实核查；正式 Research/Fact Check/Thesis/Reviewed Script/rights/production Gate **不变**。
- [#28](https://github.com/HWang0310/deep-talk-studio/issues/28) 内嵌 TTS/声音克隆及 V2 Phase D/E/F：**DEFERRED/HOLD**。不下载模型，不接触私人声音，不自动剪辑或发布视频。

## 唯一活跃开发/验收主线
- **[PR #45](https://github.com/HWang0310/deep-talk-studio/pull/45)** (`agent/issue44-minimal-ux`，基于 PR #43)：Forge 提交了 Chat-first 流式聊天和未审核草稿的实现；截至本快照 HEAD 为 `f08942a0a9d5b3a71a0e7bfebda0b874f3ce8d76`，**OPEN / NEXUS CHANGES_REQUIRED / 未合并未发布**。本地夹具验证 ≠ Owner 真实 DeepSeek 测试。
- Nexus 本轮代码审查 [Review #5626927896](https://github.com/HWang0310/deep-talk-studio/pull/45#pullrequestreview-5626927896) 的 **4 个未决点**：旧集表单混入聊天首页、并发/陈旧快照可能覆盖聊天或草稿、停止重发重复用户消息和错误计费承诺、草稿模型来源标记未持久化。
- **Writer = Forge（TeleAgent-first）；Reviewer / PM = Nexus**。修复只在原 PR #45 分支推进，逐项补测试/真实浏览器证据。跨模块重大架构问题再升级 Atlas。不得让第二个 Writer 同时改 `webui_static/index.html`。
- **下一关**：Forge 推送修复 → Nexus exact-head delta review → Owner 仅用自己的 API Key 在本机真实体验；未验收前不合并、不打 tag、不正式发布。

## 分支与 PR 依赖（集成时核对 GitHub）
`main` ← [#39](https://github.com/HWang0310/deep-talk-studio/pull/39)（设置）← [#40](https://github.com/HWang0310/deep-talk-studio/pull/40)（参考分析）← [#41](https://github.com/HWang0310/deep-talk-studio/pull/41)（独立检索）← [#42](https://github.com/HWang0310/deep-talk-studio/pull/42)（音频 UI）← [#43](https://github.com/HWang0310/deep-talk-studio/pull/43)（浏览器验收）← [#45](https://github.com/HWang0310/deep-talk-studio/pull/45)（对话 MVP）。

这 **6 个 OPEN PR 是堆叠依赖，不是 6 条独立开发主线**。合并/改 base/关闭/删除分支必须先复核 exact SHA、diff 与合同，不因瘦身而批量清理。已经合入的 [#25](https://github.com/HWang0310/deep-talk-studio/pull/25)、[#27](https://github.com/HWang0310/deep-talk-studio/pull/27)、[#31](https://github.com/HWang0310/deep-talk-studio/pull/31)、[#33](https://github.com/HWang0310/deep-talk-studio/pull/33) 是历史/已实现能力，不是当前待派工任务。

## 恢复与派工最短步骤
1. **先检查远端 PR #45 HEAD、最新评论和所有相关 PR 的真实状态。** 快照若过期，按远端新事实调整；不要重播旧 ChatGPT 会话。
2. 阅读 `AGENTS.md` 的 roster、任务相关 Hard Boundary，以及本索引；根据 `docs/INDEX.md` **按需**读取具体合同/代码/测试。`PROJECT_STATE.md` 仅在要确认产品已验收能力/发布事实时深读。
3. 阅读 `engineering-journal` 的现行 `AGENT-OPERATING-MODEL.md` 与 `BACKEND-CAPABILITY-CERTIFICATION.md` 以确认路由：工程师身份和 backend 分离，已退役 backend 不派工；不复制另一项目 roster。
4. 当前只处理 PR #45 的 correction delta；不得自行启动 #28、V2、删除历史、付费 API 调用或合并。保留本地未提交文件、私有素材与凭据。

**维护规则：** 本文件只记录活跃工作及其短期 next action。PR 合并、任务切换、Owner 优先级改变时由 Nexus 更新对应段落；长期事实在 `PROJECT_STATE.md`，完整历史在 `HANDOFF.md`/Git，不把本文件堆成流水账。
