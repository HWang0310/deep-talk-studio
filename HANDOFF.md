# DeepTalk Studio 交接记录

更新时间：2026-08-10
当前版本：V0.2 / `0.2.0`
当前分支：`main`
GitHub：`https://github.com/HWang0310/deep-talk-studio`（公有仓库）
正式发布：`https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.2.0`

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.1 的正式 Review，实现 **V0.2 Research Quality Gate & Independent Fact Check**。本轮只提高研究证据、来源 provenance、独立核查和质量 Gate，不实现自动选题、写稿、素材、视觉、剪辑或发布。

## 2. 本轮完成了什么

- 将报告契约升级为 Research Report 0.2。
- 把来源与主张的关系升级为正式 Evidence Ledger，区分支持、反驳、归属和背景。
- 实现完整的嵌套 Schema、枚举、类型、未知字段和跨字段校验，错误统一为可理解的 `ReportValidationError`。
- 保留 OpenAI Responses API 的搜索调用、完整来源和 URL citation provenance，并对模型自报但无法匹配的来源降级。
- 将研究和事实核查拆成两个独立调用/步骤；Fact Check 必须记录新的检索和反证检查。
- 给主张增加重要性、风险等级和风险因素，高风险主张自动进入二次核查队列。
- 实现透明质量指标和质量 Gate；不达标只能保存为 `draft`。
- 实现 URL 规范化、追踪参数清理、同 URL、同发布者和疑似转载分组。
- 实现报告 ID、不可覆盖的修订版、更正历史和独立核查工件保存。
- 实现 0.1 → 0.2 迁移，迁移结果不会伪装成已独立核查。
- 更新 `research-topic` Skill 为两阶段流程，并增加 Codex Draft 的机器字段准备入口。
- 用三类真实公开题材跑完整工作流：稳定商业信息、争议公共政策、快速突发热点。
- 新增并通过 68 项自动测试。

## 3. 创建 / 修改了哪些重要文件

- `src/deeptalk_studio/schema.py`、`validation.py`：0.2 契约和完整校验。
- `src/deeptalk_studio/provenance.py`、`sources.py`：工具来源追踪、URL 规范化和独立性分组。
- `src/deeptalk_studio/fact_check.py`、`quality.py`：独立核查、高风险队列和质量 Gate。
- `src/deeptalk_studio/revisions.py`、`storage.py`：不可覆盖的报告历史和更正。
- `src/deeptalk_studio/migration.py`：0.1 兼容读取与迁移。
- `src/deeptalk_studio/providers/openai.py`、`workflow.py`：两次独立联网调用和 provenance 传递。
- `.agents/skills/research-topic/`：V0.2 Codex Skill、报告契约和 UI 元数据。
- `examples/sample-research-report.json`：当前 0.2 虚构报告示例。
- `examples/sample-codex-draft-input.json`：Codex 研究内容输入示例。
- `docs/EVALS.md`、`evaluations/v0.2-summary.json`：真实评测方法与去内容化结果。
- `docs/releases/v0.2.0.md`：GitHub Release 说明。
- `tests/`：完整 Schema、来源、provenance、Fact Check、质量、修订、迁移和 CLI 回归测试。
- `README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`docs/ARCHITECTURE.md`、`CHANGELOG.md`：全部同步到 V0.2。

## 4. 当前架构是什么

当前正式数据流是：

```text
用户主题
→ Research Pass + 首次来源检索
→ Research Draft r1
→ Independent Fact Check + 新的检索/反证
→ FactCheck Artifact
→ Reviewed Research Report r2
→ Quality Gate
→ draft，或 reviewed 并等待用户确认
```

Research Report JSON 继续是下游正式接口；FactCheck Artifact 是独立核查的版本化证据。Markdown 只供人阅读。真实报告按 `主题 / report_id / rNNNN` 保存，已有修订拒绝覆盖。

## 5. 已经可以运行什么

普通用户可在仓库内直接对 Codex 说：

> 请用 DeepTalk Studio 研究“某个话题”，完成独立事实核查并生成 V0.2 Research Report。

Codex 会完成两阶段研究、保存草稿与核查工件，并告诉用户最终是 `reviewed` 还是被 Gate 拦在 `draft`。

开发和验收入口：

```bash
./scripts/deeptalk sample
./scripts/deeptalk validate examples/sample-research-report.json
./scripts/deeptalk prepare-draft examples/sample-codex-draft-input.json
./scripts/deeptalk migrate 旧版报告.json
./scripts/deeptalk review-report 草稿.json fact-check.json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

配置用户自己的 `OPENAI_API_KEY` 后，仍可用 `./scripts/deeptalk research "主题"` 运行 API 自动化的两阶段研究。

## 6. 还不能运行什么

- “今天讲什么”的 Topic Discovery。
- Script Agent 和成品原创口播稿。
- 素材搜索、新闻截图和版权使用建议。
- Remotion、HyperFrames、图表和视频辅助素材。
- 剪辑方案、字幕、标题、封面和 B 站发布。
- 小红书、抖音等平台适配。

## 7. 已知问题

- 来源转载识别是保守的第一版启发式规则；无法确定时保留未知，仍需编辑判断。
- Codex Skill 依赖宿主联网工具；如果宿主不能联网，只能使用用户提供的来源，不能伪装为已完成核查。
- 本轮环境没有用户 OpenAI API 密钥，因此 API 联网调用没有产生真实费用，也没有做线上调用；其请求、provenance 提取和两次独立调用由模拟 API 测试覆盖。Codex Skill 已用三类真实题材完成联网验收。
- 真实快速热点可能正确地停在 `draft`，这表示 Gate 正常工作，不是程序故障。
- 机器 Gate 只能验证证据结构和规则，不能代替编辑、法律意见或现实世界事实认证。
- 本机普通 HTTPS `git push` 仍可能挂起；远程同步继续采用已授权 GitHub API，并在发布前后比对远程文件树。不得强推或重写 `main` 历史。

## 8. 重要技术决策

1. 继续使用 Python 3.9+ 标准库，不为 Schema 校验新增运行时依赖。
2. 自行实现并测试项目实际使用的完整 JSON Schema 关键字；Schema 和业务交叉规则由同一个入口执行。
3. 模型生成研究内容，报告 ID、修订、时间、质量指标和审批状态由代码确定，不能让模型自报。
4. API 模式使用 `web_search_call.action.sources` 和 URL citation；Codex 模式使用实际工具结果 URL，两者明确标记不同 provenance 方法。
5. 无法与真实工具来源匹配的页面降级为 `unmatched/not_inspected`，不能支撑 confirmed fact。
6. Fact Check 是单独 Artifact 和新的工具调用，即使底层使用同一模型也不能与 Research Pass 合并。
7. 质量 Gate 不使用神秘总分；状态只由公开底层指标计算。
8. 高风险未解决时必须保持 `draft`；通过 Gate 后也只到 `reviewed`，等待一次用户确认。
9. 旧报告迁移保持保守：保留内容，但把核查状态设为未完成。
10. 完整真实评测报告继续留在被 Git 忽略的 `reports/`，公开仓库只保存方法和去内容化汇总。
11. OpenAI Structured Outputs 请求会移除官方当前不支持的 `uniqueItems`，但模型返回后仍执行完整本地 Schema，绝不因此放松报告校验。

## 9. 哪些问题需要产品经理决定

请 ChatGPT Review 后只决定下一阶段产品方向：

1. 是否正式进入 V0.3 Topic Discovery；如果进入，第一版候选题评分最看重新鲜度、观点冲突、可核查性还是频道匹配度。
2. Topic Discovery 每次给用户多少候选题，以及用户确认选题时最简单的交互形式。
3. V0.2 的质量阈值是否先保持当前保守设置，等更多真实运营样本后再调整。
4. 真实报告是否继续只放本机，还是未来建立单独私有内容库；V0.2 不改变当前本机策略。

## 10. 建议下一阶段做什么

建议由 ChatGPT 完整 Review V0.2 后，再决定是否进入 **V0.3 Topic Discovery**。如果通过，V0.3 只实现“我不知道今天讲什么 → 给出少量可解释候选题 → 用户确认 → 进入现有 V0.2 Research Workflow”，仍不要提前实现 Script Agent。

## 11. 本轮验收记录

2026-08-10 已完成：

- 68 项自动测试全部通过。
- 当前 V0.2 示例报告校验通过并能生成 Markdown/JSON。
- `prepare-draft`、独立 `review-report`、0.1 迁移、报告修订防覆盖全部通过。
- 三类真实公开题材完整运行；2 份 `reviewed`、1 份高风险动态热点按预期 `draft`。
- 三份真实报告的 claim coverage、高风险核查 coverage 和 provenance match 均为 100%；突发样本因 1 个未解决高风险主张被正确拦截。
- 官方 Skill Creator `quick_validate.py`：`Skill is valid!`，PyYAML 仅安装在临时目录。
- Python 3.9 兼容测试、源码编译、干净虚拟环境安装、密钥扫描、Git diff 和远程文件树比对：通过。
- GitHub Release `v0.2.0` 已创建并核验，自动提供 ZIP/TAR 源码包；没有发布无意义的空软件包。

## 12. 版本发布规则

用户要求每个正式版本都使用 GitHub Release。V0.2.0 发布页：`https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.2.0`。GitHub 自动提供源代码 ZIP/TAR。当前仍不创建 GitHub Packages，因为项目还不是需要独立安装分发的成品软件包。

## 给用户的下一步操作

下一步：只把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成并正式发布的 DeepTalk Studio V0.2：https://github.com/HWang0310/deep-talk-studio ，发布页是 https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.2.0 。请先完整阅读 HANDOFF.md，再 Review Research Report 0.2、Evidence Ledger、来源 provenance、独立 Fact Check、质量 Gate、修订历史、迁移、68 项测试和三类真实评测汇总。请判断 V0.2 是否验收通过，并决定是否进入 V0.3 Topic Discovery。最后请直接给我一段可以原样发给 Codex 的下一轮任务，不要让我自己总结。

如果 ChatGPT 暂时打不开仓库，只需把本文件 `HANDOFF.md` 全文复制给它，不需要自己解释。
