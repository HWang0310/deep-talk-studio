# DeepTalk Studio 交接记录

更新时间：2026-08-10
当前版本：V0.2.1 / `0.2.1`
当前正式分支：`main`
GitHub：`https://github.com/HWang0310/deep-talk-studio`（公有仓库）
正式发布：`https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.2.1`

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.2.0 的 Conditional Pass Review，发布 **V0.2.1 Quality Gate Hardening**。本轮只修 Research Quality Gate 的独立来源计数、API machine-owned fields、Fact Check 新来源归组和相邻质量指标；不实现 Topic Discovery、Script Agent、素材、视觉、剪辑或发布。

## 2. 本轮完成了什么

- 修复 P0：confirmed fact 的独立确认只接受 `supports + matched + independent + 不同 independence_group`。
- `unknown`、`related`、`duplicate`、`syndicated` 均不能贡献独立确认；程序不会为通过 Gate 把 unknown 自动改成 independent。
- 新增 API Research 内容草稿 Schema；模型不再生成 report ID、revision、时间、状态、Fact Check、provenance、quality 或审批字段。
- API payload 如果夹带 quality summary 或 approval state，会在正式 r1 生成前被拒绝。
- Fact Check 新来源与 r1 来源合并后统一做 URL 规范化、追踪参数清理、重复、同发布者、转载和独立性归组。
- 保存的 FactCheck Artifact 和 reviewed report 使用同一个确定性来源分组；模型填写的 URL 规范化值和 group 会被覆盖。
- 完成窄范围质量指标审计：context-only、未匹配 attribution、duplicate / syndicated 记录不再意外刷高相关指标。
- 修复来源重复规范化不稳定：同一 URL 多次处理始终保持 duplicate，不会变成 syndicated。
- 新增 17 项回归测试，总数由 68 增至 85，全部通过。
- 重新运行三类真实评测：2 份 `reviewed`，1 份快速高风险热点保持 `draft`。

## 3. 创建 / 修改了哪些重要文件

- `src/deeptalk_studio/quality.py`：独立来源和相邻质量指标 hardening。
- `src/deeptalk_studio/schema.py`：新增内部 `API_RESEARCH_DRAFT_JSON_SCHEMA`。
- `src/deeptalk_studio/workflow.py`：API 内容确定性补全、Fact Check canonicalization。
- `src/deeptalk_studio/fact_check.py`：新旧来源统一归组和 canonical Artifact。
- `src/deeptalk_studio/sources.py`：稳定、幂等的 duplicate 优先规则。
- `tests/`：independence、API ownership、metric audit、Fact Check grouping 回归测试。
- `evaluations/v0.2.1-summary.json`：去内容化复测结果；完整报告仍在 gitignored `reports/`。
- `.agents/skills/research-topic/`：更新独立来源与 Fact Check 新来源规则。
- `docs/superpowers/specs/2026-08-10-v0.2.1-quality-gate-hardening-design.md`：本轮设计。
- `docs/superpowers/plans/2026-08-10-v0.2.1-quality-gate-hardening.md`：本轮实施计划。
- `docs/releases/v0.2.1.md`：GitHub Release 说明。
- `README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/EVALS.md`、`CHANGELOG.md`：同步 V0.2.1。

## 4. 当前架构是什么

```text
用户主题
→ Research 内容生成 + 首次来源检索
→ 程序补齐身份 / revision / provenance / 状态 / quality
→ Research Report 0.2 r1
→ Independent Fact Check + 新检索
→ 新来源与 r1 来源统一确定性归组
→ canonical FactCheck Artifact 0.2
→ Research Report 0.2 r2
→ hardened Quality Gate
→ draft，或 reviewed 并等待用户确认
```

正式下游接口仍是 Research Report 0.2 和 FactCheck Artifact 0.2。V0.2.1 只改变内部输入边界和正确性规则，没有制造不必要的 Report 0.3。

## 5. 已经可以运行什么

- 在 Codex 中直接输入主题，完成 Research Draft、独立 Fact Check、来源归组、质量 Gate 和 r1/r2 保存。
- 使用可选 OpenAI API 自动入口时，模型只负责研究判断，机器字段由 workflow 生成。
- 校验报告、准备 Codex Draft、应用独立 FactCheck Artifact、迁移 V0.1 报告、保留不可覆盖 revision。
- 明确区分“做过核查”和“高风险问题已解决”；后者未满足时保持 `draft`。

常用验收入口：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
./scripts/deeptalk sample
./scripts/deeptalk validate examples/sample-research-report.json
./scripts/deeptalk prepare-draft examples/sample-codex-draft-input.json
./scripts/deeptalk review-report 草稿.json fact-check.json
```

## 6. 还不能运行什么

- “我不知道今天讲什么”的 Topic Discovery。
- Script Agent 和成品原创口播稿。
- 素材搜索、新闻截图和版权使用建议。
- Remotion、HyperFrames、图表和视频辅助素材。
- 剪辑方案、字幕、标题、封面和平台发布。

## 7. 已知问题

- 来源独立性仍包含保守启发式和研究者判断；程序能阻止 unknown 被误算，但不能证明现实世界中两个组织完全没有信息依赖。
- Codex Skill 依赖宿主联网工具；无法联网时不能伪装为完成检索或独立核查。
- 本轮环境没有用户 OpenAI API 密钥，因此线上 API 未产生费用；API Schema、tool provenance 和两次调用由受控 Provider 测试覆盖。
- 真实报告默认只保存在本机 `reports/`，没有云端内容库。
- 本机普通 HTTPS `git push` 历史上可能挂起；本轮继续以不重写历史的 GitHub API 安全同步并核对文件树。
- 机器 Gate 只能验证证据结构和规则，不能代替编辑、法律意见或现实世界事实认证。

## 8. 重要技术决策

1. 保持 Report / FactCheck Artifact Schema 0.2 和原质量阈值，不用内部输入优化制造 0.3。
2. 独立确认的四个必要条件写成确定性代码；group ID 只用于去重，不能单独证明独立。
3. `unknown` 保持未知，质量 Gate 宁可拦截，也不自动升级。
4. API Research 与 Codex Draft 使用不同的内容 Schema，因为两者 provenance 来源不同。
5. 模型生成研究判断；身份、revision、状态、provenance、quality、审批和 review flags 由代码拥有。
6. Fact Check Artifact 在保存前 canonicalize，确保手动 CLI 与 API workflow 使用同一规则。
7. Claim coverage 不把纯背景链接当作有效来源；来源类型和 provenance 指标只评估实际参与非背景证据且非重复转载的来源。
8. 高风险 Fact Check coverage 只表示是否真正复查；是否解决由 unresolved high-risk 和 Fact Check status 单独表达，避免指标含义混淆。
9. 完整真实报告继续 gitignore，公有仓库只保存去内容化评测汇总。

## 9. 哪些问题需要产品经理决定

请 ChatGPT 本轮只决定：

1. V0.2.1 是否修复了 Conditional Pass 的全部 correctness 问题，并正式验收 V0.2。
2. 如果验收通过，是否正式进入 V0.3 Topic Discovery。
3. V0.3 每次给用户多少候选题，以及评分中最优先考虑新鲜度、观点冲突、可核查性还是频道匹配度。

## 10. 建议下一阶段做什么

先由 ChatGPT Review V0.2.1。只有 Review 通过后，再进入 **V0.3 Topic Discovery**：实现“我不知道今天讲什么 → 少量可解释候选题 → 用户确认 → 进入现有 Research Workflow”。不要提前实现 Script Agent。

## 11. 本轮验收记录

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：85 项全部通过。
- 原 68 项测试全部保留并继续通过，新增 17 项 regression tests。
- sample、validate、prepare-draft、review-report、migration、revision overwrite protection：通过。
- 三类真实题材复测：稳定商业 `reviewed`、争议公共政策 `reviewed`、快速公共安全热点 `draft`。
- 完整评测报告位于 gitignored `reports/evaluations/v0.2.1-final/`；公开仓库只有 `evaluations/v0.2.1-summary.json`。
- Skill validation、Python 3.9 兼容、干净环境安装、源码编译、JSON 校验、密钥扫描、Git diff 与远程文件树核对：通过。
- GitHub Release `v0.2.1` 已创建并核验，自动提供 ZIP/TAR 源码包；没有发布无意义的空软件包。

## 12. 版本发布规则

每个正式版本继续使用 GitHub Release。V0.2.1 发布页：`https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.2.1`。GitHub 自动提供源代码 ZIP/TAR。当前仍不创建 GitHub Packages，因为项目还不是需要独立安装分发的成品软件包。

## 给用户的下一步操作

下一步：只把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.2.1：GitHub 仓库是 https://github.com/HWang0310/deep-talk-studio ，Release 是 https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.2.1 。请先完整阅读 HANDOFF.md，再 Review Quality Gate independent-source 修复、API machine-owned field 清理、FactCheck source grouping、新增测试和三类真实评测。如果通过，请正式验收 V0.2，并给我 V0.3 Topic Discovery 的开发任务。最后请直接给我一段可以原样发给 Codex 的下一轮任务，不要让我自己总结。

如果 ChatGPT 暂时打不开仓库，只需把本文件 `HANDOFF.md` 全文复制给它，不需要自己解释。
