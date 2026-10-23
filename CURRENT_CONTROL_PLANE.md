# DeepTalk Studio — Current Control Plane

> **2026-10-24 GitHub-verified integration snapshot, not a live status service.** On every recovery first check remote `main`, relevant Issue/PR exact SHAs and local dirty/worktree state. [PROJECT_STATE.md](PROJECT_STATE.md) owns formal release / accepted capability facts; [AGENTS.md](AGENTS.md) owns guardrails and canonical engineer roster. Historical handoffs and plans are not default next actions.

## 当前一句话
**PR #39 → #40 → #41 → #42 → #43 → #45 六个依赖功能 PR 已全部合并 `main`。下一关是 Forge 对集成后 `main` 做隔离测试、本机 8321 与真实聊天/草稿/Key 的无损验证；然后推进 [Issue #29](https://github.com/HWang0310/deep-talk-studio/issues/29) 首条真实视频，而不是继续改基础聊天界面。**

## 已确认状态与产品边界
- **最新正式发布仍为 [v1.0.0](https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0)**；当前 `main` 已包含 post-release Creator Workbench、DeepSeek 设置、参考视频分析、显式 Search/Fetch、音频交付 UI、浏览器验收、Chat-first 多会话与未审核 Creative Draft。**已合并代码不等于新版本已发布、本机服务已自动升级、真实视频已完成。**
- 已合并的功能 PR：[ #39](https://github.com/HWang0310/deep-talk-studio/pull/39) → [#40](https://github.com/HWang0310/deep-talk-studio/pull/40) → [#41](https://github.com/HWang0310/deep-talk-studio/pull/41) → [#42](https://github.com/HWang0310/deep-talk-studio/pull/42) → [#43](https://github.com/HWang0310/deep-talk-studio/pull/43) → [#45](https://github.com/HWang0310/deep-talk-studio/pull/45)。最终集成提交为 `fcb0b6d4c12208cf86a589211fe8a43f05f809ef`（后续文档提交将推进 `main` HEAD）。合并使用保留祖先的 merge commit；#42/#43/#45 与项目瘦身文档冲突已明确取新版状态与人员规范，同时保留应用代码和测试。
- Owner 已保存 DeepSeek API Key：稳定用户级 `~/.deeptalk/workbench.local.json`，必须跨工作树/重启复用且不泄露。历史聊天稳定保存于 `~/.deeptalk/chat/`；迁移不得覆盖旧文件，测试 `pytest` / `unittest` 双入口必须隔离真实 Key 与聊天。**不得再次要求 Owner 反复输入 Key。**
- 2026-10-23 Owner 批准 Chat-first 方案 A：自由聊天、真实 SSE、多会话、未审核草稿不强制先做事实核查。**正式** Research / Fact Check / Thesis / Reviewed Script / Rights / Production 的人工审批 Gate 不变；显式付费 Search/Fetch、素材下载、上传私人数据需要适当的授权；真实最终音轨由 Owner 录制或合法提供，剪映编辑/发布由 Owner 完成。
- 内嵌 TTS/声音克隆 [#28](https://github.com/HWang0310/deep-talk-studio/issues/28) 与 V2 后续阶段仍 **HOLD**。不要擅自自动发布、复制他人原创表达、伪造事实来源/模型结果/时间对齐。

## 近期执行顺序
1. **只允许一个 Writer：Forge；Nexus 审核。** Forge 首先核对本机现有 8321 的 PID/实际运行代码/工作树与最新 `main`，保留 dirty 文件、用户级 Key、原会话和所有草稿；不要直接重置或覆盖。运行隔离的 pytest 与裸 unittest、桌面/375px 浏览器 smoke（新建 A、B/快速切换/迟到草稿、关闭/展开侧栏、刷新重启、404/stop/retry、草稿版本），核对用户目录快照前后未改。**可使用 mock 验收集成，不必重复调用付费模型。**
2. **Owner 最新产品反馈待落地：输入一个时事选题（如「王扁被打」）后，DeepTalk 应主动识别事件、尝试找到可信公开来源和准备结构/可修改草稿，而不是先向用户抛出泛泛的身份/视角问题。** 这是一项尚未实现的 **topic-to-creation 编排能力**，不能因为聊天 AI 能回答问题就声称已完成。搜不到或同名歧义才精确询问；发现报道同源要区分，未有权威确认的动机/伤情不能编造。可先产出清楚标记“未核实”的创作方向/自由草稿；正式口播发布仍按原 Gate。涉及付费检索和下载应先按产品现有授权约束行动。
3. 回到 [Issue #29](https://github.com/HWang0310/deep-talk-studio/issues/29)：从真实选题到独立来源、可审核原创口播稿、Owner 最终音频、真实对齐/素材建议、剪映人工成片。目标是 **第一条真实视频**，不是更多工程表单或治理文档。
4. 当前不要再创建一串嵌套 PR；新工作若需 PR，应从最新 `main` 单一分支提交；禁止重新打开/重复合并 #39–#45、批量删历史分支、未经授权发布/tag 或绕过人审。

## Agent 最短阅读
远端当前状态 → [AGENTS.md](AGENTS.md) → 本索引 → 按需 [docs/INDEX.md](docs/INDEX.md) 的 canonical Skill/合同、实现和测试。只有涉及正式产品能力与版本时深入 [PROJECT_STATE.md](PROJECT_STATE.md)。GitHub 最新事实优先，遇到冲突向 Nexus 报告。

**维护规则：** 只更新当前主线/下一步，已完成历史保存在 GitHub PR、CHANGELOG 与 HANDOFF；保持本文件简洁。
