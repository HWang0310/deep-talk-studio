# DeepTalk Studio 交接记录

更新时间：2026-08-10
当前版本：V0.4.0 / `0.4.0`
当前正式分支：`main`
GitHub：https://github.com/HWang0310/deep-talk-studio （公有仓库）
正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.4.0

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.3.1 的正式验收和 V0.4 产品 / 架构任务，实现 **Original Script Agent**：把经过独立 Fact Check、通过 Quality Gate 并由用户明确批准的 Research Report，转换为可核查、原创、适合真人露脸的深度口播稿。本轮要求同时完成 Approval Revision、Script Artifact、Grounding、独立 Script Review、Editor / Teleprompter 输出、版本修订、三类真实评测、文档和 `v0.4.0` Release。

本轮没有开始 V0.5，也没有实现素材、视觉、剪辑或发布。

## 2. 本轮完成了什么

- 用户确认不再只是内存状态：`approve-report` 会建立新的不可覆盖 Research Revision，保存原始确认并设为 `ready_for_script`。
- 新增 Script Profile 0.4，默认适配 B 站中文真人口播、约 12 分钟，并支持“8 分钟”“做长一点”“紧凑一些”等自然语言调整。
- 新增 Script Draft Artifact 0.4。每个 Beat 区分事实、归因、分析、转场和问题，并保留 Claim / Evidence 回链。
- 新增硬 Grounding Gate：未批准 Research、未核查高风险事实、错误归因、直接使用禁讲结论、无依据分析、无效引用和伪造机器字段都会被拒绝。
- 新增 must-keep coverage、有效口播字符数和估算时长，由程序计算，Writer 无法自报。
- Writer 与 Reviewer 分离，二者都不能 Web Search。API 载荷不提供搜索工具，任何返回的搜索 provenance 都会被工作流拒绝。
- 新增 Script Review Artifact 0.4。Reviewer 必须完成 15 个检查维度；缺一项就无效。阻断问题、严重度、数量和 Gate 全部由程序推导。
- Review 会创建新 Script revision：通过为 `reviewed`，有阻断问题仍为 `draft`；旧稿不覆盖。
- 同时输出 Editor Markdown 和纯口播 Teleprompter Markdown；支持修订、比较和自然语言反馈。
- 新增仓库级 `write-script` Skill，让普通用户只需确认时长、粘贴反馈或说“比较两个版本”。

## 3. 创建 / 修改了哪些重要文件

- `.agents/skills/write-script/`：普通用户的确认、写稿、独立审稿、修改和比较流程。
- `config/script-profile.json`：V0.4 频道、口播、时长、风格和原创性约束。
- `src/deeptalk_studio/script_validation.py`：Approval Gate、Grounding、类型边界、禁讲项、覆盖和机器字段校验。
- `src/deeptalk_studio/script_review.py`：独立 15 项 Review、阻断规则和 Gate。
- `src/deeptalk_studio/script_renderer.py`、`script_storage.py`：双 Markdown 输出和不可覆盖保存。
- `src/deeptalk_studio/script_revisions.py`：稿件修订和版本比较。
- `src/deeptalk_studio/script_prompt.py`、`script_workflow.py`：Writer / Reviewer 提示与两阶段工作流。
- `src/deeptalk_studio/schema.py`、`models.py`、`providers/`、`cli.py`、`revisions.py`、`workflow.py`：正式契约、Provider 和统一入口。
- `docs/SCRIPT_CONTRACT.md`、`docs/SCRIPT_EVALS.md`：V0.4 契约与真实评测。
- `evaluations/v0.4.0-summary.json`：不含真实题材内容的公开评测汇总。
- `docs/releases/v0.4.0.md`：正式版本说明。
- README、PRD、ROADMAP、AGENTS、CHANGELOG、架构和本 HANDOFF：全部同步 V0.4。

## 4. 当前架构是什么

```text
模式 A：用户直接主题 ─┐
                     ├→ Research → Independent Fact Check → Quality Gate
模式 B：Topic Discovery → 用户选编号 ┘

Gate fail → draft，禁止写稿
Gate pass → reviewed，等待用户确认
用户确认 → 新 Approval Revision / ready_for_script
          → Original Script Writer（不联网）
          → Script Draft r1
          → Independent Script Reviewer（不联网，15 项必检）
          → blocking：Script r2 / draft
          → pass：Script r2 / reviewed
          → Editor Markdown + Teleprompter Markdown
          → 用户反馈生成 r3、r4……，历史不覆盖
```

Research Report 继续使用 0.2 契约，Topic Candidate Set 继续使用 0.3 契约。V0.4 只新增 Script Profile、Script Draft 和 Script Review 0.4，没有破坏上游工件。

## 5. 已经可以运行什么

- 用户可继续直接给主题，或说“今天讲什么？”后只回复编号。
- Research Workflow 继续执行多来源研究、独立 Fact Check 和透明质量 Gate。
- 通过 Gate 后，用户只需说“确认进入写稿，做成 8 分钟”，系统会保存确认并完整写稿、审稿。
- Script Editor 版可检查每段类型、Claim、Evidence、分析依据、风险、研究局限和必须保留覆盖。
- Teleprompter 版只保留真人可读正文，不显示机器 ID、URL 或 citation syntax。
- 用户可说“第二段更紧凑”“做长一点”或“比较这两个版本”，系统会建立不可覆盖的新 revision。
- Codex Skill 模式不需要 API Key；可选 API 模式支持同一正式契约。

## 6. 还不能运行什么

- 自动搜索或下载新闻截图、公开文件、图片和视频素材。
- 自动生成图表、时间线动画、Remotion / HyperFrames 画面。
- 镜头级剪辑方案、字幕、封面、标题、B 站上传或其他平台分发。
- 根据发布数据自动学习，或无人审核自动发布。
- 这些均属于尚未开始的 V0.5 / V0.6，不应把 `reviewed` Script 误解成发布批准。

## 7. 已知问题和 blocker

- 口播时长来自有效中文字符数估算，真人停顿、语速和临场发挥仍需要最终朗读确认。
- `avoid_claims` 的直接文字使用由程序硬阻止；换一种说法但语义仍越界的情况依赖独立 Reviewer 识别。
- 工程 Grounding 证明稿件忠于批准的 Research Artifact，不能证明现实世界永远没有变化；快速事件要先更新 Research revision，再重新批准。
- 真实评测的两份既有 Research Report 只有 2 项和 3 项可用主张，因此实际稿件采用 5 / 6 分钟目标，没有为凑默认 12 分钟重复信息或补写研究外事实。
- Codex Skill 模式下，Writer / Reviewer 的“独立”是严格分步和不同职责，不是两个长期独立运行的服务器进程。
- 没有工程 blocker。是否进入 V0.5 只等待 ChatGPT 的产品 / 架构验收决定。

## 8. 重要技术决策

1. Approval 必须是新 Research Revision，而不是把原报告原地改为批准；任何新研究内容都会重置旧确认。
2. Writer 只生成内容字段。身份、revision、Beat ID、状态、字符数、时长和覆盖都归代码所有，并在读取时重新推导。
3. Fact / Attribution / Analysis 使用结构化 Beat 明确区分；自然归因与语义越界再由 Reviewer 复核。
4. Writer / Reviewer 不联网，避免研究阶段结束后悄悄混入新事实；需要新信息时必须回到 Research Workflow。
5. Review 要求全部 15 个检查维度，不能用少数“看起来没问题”的检查自报通过。
6. Review 结果也通过新 revision 表达，不修改 r1；Review Artifact 单独保存，保持审稿过程可追踪。
7. Editor 与 Teleprompter 都从 JSON 派生；机器不反向解析 Markdown。
8. 真实完整 Script 默认 gitignore，公开仓库只放去内容化指标，避免未经最终编辑的真实稿件被公开。

## 9. 哪些问题需要产品经理决定

请 ChatGPT Review：

1. Approval Revision 是否充分表达用户批准和新研究修订后的自动失效。
2. Script Draft 的 Beat grounding、Fact / Attribution / Analysis 边界和 `avoid_claims` / must-keep 策略是否达到 V0.4 要求。
3. Script Review 的 15 项必检、blocking 类型和 `reviewed` 含义是否合适。
4. Editor / Teleprompter 分工、不可覆盖 revision 和 Writer / Reviewer 无 Web Search 边界是否清晰。
5. 两份真实稿件的 4.4 / 4.5 人工 Editorial 结果和“证据有限时缩短时长”决策是否可接受。
6. V0.4 是否正式验收，并决定是否进入 V0.5 Material Search 与 Visual Assistance。

## 10. 建议下一阶段做什么

如果 ChatGPT 正式验收 V0.4，下一阶段建议只做 **V0.5 Material Search 与 Visual Assistance 的产品设计和最小实现**：从 reviewed Script 和 Research Evidence 中推荐可合法使用的公开文件、截图、图片、短视频片段与原创图表位置，记录来源、版权风险和画面用途。不要直接跳到自动剪辑或平台发布。

在 ChatGPT 明确给出 V0.5 任务前，不开始开发。

## 11. 本轮验收记录

- 自动测试：151 项全部通过，原 113 项全部继续通过。
- Python 编译：`src` 与 `tests` 全部通过。
- Writer / Reviewer 无 Web Search：Provider payload 与工作流 provenance 两层测试通过。
- Stable Tech / Business：Approval r3；must-keep 2 / 2；1273 字符；约 4.9 分钟；15 / 15 Review；0 blocking；最终 `reviewed`；人工 Editorial 4.4 / 5。
- Contested Public Issue：Approval r3；must-keep 3 / 3；1520 字符；约 5.8 分钟；15 / 15 Review；0 blocking；最终 `reviewed`；人工 Editorial 4.5 / 5。
- Blocked Input：`reviewed` 但无用户 Approval 的报告被拒绝；退出码 2；没有创建文件。
- 两份 Teleprompter 已实际阅读全文，并核验不含 URL、机器 ID 或编辑标签。
- 三个仓库 Skill、JSON 文件、CLI 端到端、密钥扫描、Git diff 和公开 Release 会在发布前后再次核验。

## 12. 版本发布规则

本轮正式版本为 `v0.4.0`。继续使用公有仓库 `HWang0310/deep-talk-studio`，不创建新仓库、不 force push、不重写 `main` 历史。GitHub Release 自动提供 ZIP / TAR 源码包；项目仍不发布没有实际安装价值的空 GitHub Package。

## 给用户的下一步操作

下一步：把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.4 Original Script Agent。GitHub 仓库是 https://github.com/HWang0310/deep-talk-studio ，v0.4.0 Release 是 https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.4.0 。请完整 Review Approval Revision、Script Draft Artifact、Grounding Rules、Fact/Attribution/Analysis 边界、Script Review Gate、Editor/Teleprompter 输出、版本修订、测试和三类真实评测。如果通过，请正式验收 V0.4，并决定是否进入 V0.5 Material Search 与 Visual Assistance。不要让我自己总结。

如果 ChatGPT 暂时打不开仓库，只需把本文件 `HANDOFF.md` 全文复制给它，不需要自己解释。
