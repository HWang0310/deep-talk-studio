# DeepTalk Studio 交接记录

更新时间：2026-08-10
当前版本：V0.3.1 / `0.3.1`
当前正式分支：`main`
GitHub：https://github.com/HWang0310/deep-talk-studio （公有仓库）
正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.3.1

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.3.0 的 Conditional Pass，完成 **V0.3.1 Discovery Gate Hardening**。本轮只修正 Topic Discovery 的来源检查、候选工件防篡改、Preflight、时间、分类展示、Raw 候选池和评测准确性；没有开始 V0.4 Script Agent，也没有实现素材、视觉、剪辑或发布。

## 2. 本轮完成了什么

- 新增后台 Codex inspection manifest。只有实际打开且记录在 manifest 内的 URL 才会标为 `manual_open`；Raw Candidate JSON 和运行模式都不能自认证页面已打开。
- 新增纯确定性 Candidate derivation。Candidate Set 在读取时重新计算资格、理由、推荐、总分、展示顺序、首选和 watch/reject 统计；任何不一致都会被拒绝。
- Source Seed Preflight 只计算 `matched` 或 manifest-backed `manual_open` 的 official、primary、media、academic、expert 来源；规范化重复 URL、同 publisher、同 host 只算一个方向。
- 增加时间一致性：开始时间不能晚于最新进展；事件时间最多允许比 discovery 时间晚 5 分钟，明显未来时间不能获得新鲜度。
- 原始候选池低于 7 项时明确拒绝生成 Candidate Set；这不会强迫 Eligibility Gate 放行 5 个题。
- 分类展示改为先每类最多两项、再按确定性排名补足空位；同一事件始终只能展示一次。
- 删除无效的 `discover --count` 参数；用户体验继续保持“最多 5 个候选”。
- 重新执行 Broad、Tech / Business、Social / Public 真实公开资料评测，并以 `pass` / `fail` / `not_applicable` 记录结果。

## 3. 创建 / 修改了哪些重要文件

- `src/deeptalk_studio/discovery_derivation.py`：唯一的纯机器字段推导、Preflight、时间、来源方向、排序和补位逻辑。
- `src/deeptalk_studio/discovery.py`、`discovery_validation.py`、`schema.py`：inspection manifest、`seed_provenance`、工件重推导校验和 legacy 读取兼容。
- `src/deeptalk_studio/cli.py`：移除无效 `--count`；为 Skill 自动化提供后台 `--inspection-manifest` companion input。
- `.agents/skills/discover-topics/`：要求实际打开 Seed、后台生成 manifest、保证至少 7 个 Raw Candidate，不让普通用户管理技术文件。
- `tests/test_discovery.py`、`tests/test_cli.py`：新增 provenance、篡改、方向去重、时间、类别补位、最小池和 CLI 回归测试。
- `evaluations/v0.3.1-summary.json`、`docs/TOPIC_DISCOVERY_EVALS.md`：去内容化真实评测及状态语义。
- `README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`CHANGELOG.md`、架构和契约文档：同步 V0.3.1。

## 4. 当前架构是什么

```text
模式 A：用户直接主题
→ V0.2 Research Draft → Independent Fact Check → Quality Gate

模式 B：用户“今天讲什么？”
→ 搜索并实际打开公开来源
→ 后台 inspection manifest + Raw Candidate（至少 7 项）
→ 确定性 Preflight / 评分 / 去重 / 展示
→ Topic Candidate Set 0.3
→ 用户只回复编号
→ Research Handoff Brief 0.3
→ 同一条 V0.2 Research → Fact Check → Quality Gate
```

Topic Discovery 仍只回答“值不值得研究”，不确认现实事实。Source Seeds 仍只是下一步研究入口；完整 Evidence Ledger、独立事实核查和用户确认 Gate 没有变化。

## 5. 已经可以运行什么

- 用户仍可直接说“今天讲什么？”“帮我找几个科技选题”“换一批”或“只看商业”。
- Codex 会在后台记录它实际打开的 Seed；没有实际打开的链接不能通过资料 Gate。
- 最多展示 5 个不同事件；过滤后只剩一个分类时，也可以由高分不同事件补足。
- 用户只回复 `1` 或 `研究 1`，无需重复标题，即可进入已有 V0.2 Research Workflow。
- API、离线 CLI、不可覆盖 discovery 历史、Research Handoff、模式 A Research、V0.2 Fact Check 和 Quality Gate 均继续可用。

## 6. 还不能运行什么

- Script Agent 或成品原创口播稿。
- 素材搜索、截图/版权建议、Remotion、HyperFrames、图表和视频生成。
- 剪辑方案、字幕、标题、封面、平台发布或运营数据学习。
- 云端选题库、自动无人审核发布，或任何模仿某位创作者的内容能力。

## 7. 已知限制和 blocker

- Preflight 只判断“是否有足够可靠的研究入口”，不能代替后续完整事实核查；快速事件仍可能变化。
- inspection manifest 诚实地保存本次实际打开记录，但不是新闻事实证明，也不能阻止拥有完整本地文件写入权限的人同时伪造整个 Artifact 和 manifest；正常工作流会在保存和读取时做一致性校验。
- 同 publisher / host 的保守归并会宁可少推荐一些相关资料，也不会轻易把它们当作独立方向；语义完全不同但本质同一事件仍依赖搜索步骤给出正确的事件键。
- API 模式仍需 `OPENAI_API_KEY`。本轮没有使用用户 API Key，不产生 API 费用；没有 Key 时由 Codex Skill 使用宿主联网能力。
- 真实 discovery artifacts 与检查记录仅在 gitignored `discoveries/evaluations/v0.3.1/`，没有云端历史库。
- 没有工程 blocker；唯一等待的是 ChatGPT 对 V0.3.1 的产品/架构 Review。V0.4 不能在该 Review 前开始。

## 8. 重要技术决策

1. inspection manifest 是独立 companion input，不能被 Raw Candidate 混入或由 `codex_skill` 模式自动推断。
2. 通过单独 `discovery_derivation.py` 让准备和验证共用同一套纯规则，避免校验器只检查部分字段或循环依赖。
3. 新 Candidate Set 保存规范化 provenance context；旧 `0.3` 文件仍可按照其 legacy 状态读取，但不会被升级成“新检查过”。
4. `--count` 选择删除而非增加可变工件复杂度，固定最多 5 个更符合普通用户入口。
5. Raw pool 最小值保证广泛搜索的最低覆盖面，Eligibility Gate 仍可让最终列表少于 5 个。
6. 真实评测把资料不足标为 `not_applicable`，不靠虚构候选填补 Top 5 测试。

## 9. 需要产品经理决定的问题

请 ChatGPT Review：

1. Codex inspection manifest 与 Source Seed provenance 边界是否足够清晰、保守。
2. Candidate Artifact 机器字段重推导和 legacy 读取兼容策略是否符合 V0.3 约束。
3. Source direction 的 URL / publisher / host 归并、5 分钟时间容差和“先多样再补位”规则是否合适。
4. V0.3.1 是否正式验收通过；若通过，请给出 V0.4 Original Script Agent 的明确开发任务。

## 10. 建议下一阶段做什么

只有 V0.3.1 被 ChatGPT 正式验收后，才进入 **V0.4 Original Script Agent**：它只能读取通过 V0.2 Quality Gate 且用户明确确认的 Research Report，生成原创分析框架和口播稿，并保留事实回链、禁讲项、时长/结构与相似表达风险检查。不要提前实现素材、视觉、剪辑或发布。

## 11. 本轮验收记录

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：113 项全部通过（原 101 项继续通过）。
- `python3 -m compileall -q src tests`：通过。
- 新增覆盖：无 manifest 的 Codex Seed、带或不带 tool reference 的 manifest-backed `manual_open`、伪造资格/推荐/展示/首选/统计、伪造 `manual_open`、legacy Candidate Set、重复 URL、同 publisher/host、social Seed、两个真实合格方向、倒置/未来时间、Broad 多样性、单分类补位、Raw 最小池、无效 `--count` 和编号交接。
- Broad 真实评测：7 个 Raw、5 个不同事件；首选机器分 98，高于第 5 名的 86；`研究 1` Handoff 已实际生成。
- Tech / Business 真实评测：7 个 Raw、5 个展示题；验证了类别过滤后的补位。
- Social / Public 真实评测：只有 1 个 Raw；系统正确拒绝生成不完整 Candidate Set，Top 5/首选/Handoff 如实标为不适用。
- 完整真实 Candidate Set、manifest 与网页笔记位于 gitignored `discoveries/evaluations/v0.3.1/`；公开 `evaluations/v0.3.1-summary.json` 不含真实热点内容。
- 发布前已再次运行完整测试、CLI 编号交接、干净安装、JSON、Skill、密钥和 Git 核验；Release 创建后会立即复核标签、目标提交和公开源码包。

## 12. 版本发布规则

每个正式版本继续使用 GitHub Release。V0.3.1 提供 `v0.3.1` 标签及 GitHub 自动生成的 ZIP/TAR 源码包；项目仍不发布空 GitHub Package。发布过程不得 force push 或重写 `main` 历史。

## 给用户的下一步操作

下一步：只把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.3.1 Discovery Gate Hardening。GitHub 仓库是 https://github.com/HWang0310/deep-talk-studio ，Release 是 https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.3.1 。请 Review Source Seed Codex provenance、Candidate machine-owned field canonical validation、Preflight source direction、时间规则、category fallback、测试和真实评测。如果通过，请正式验收 V0.3，并给我 V0.4 Original Script Agent 的开发任务。不要让我自己总结。

如果 ChatGPT 暂时打不开仓库，只需把本文件 `HANDOFF.md` 全文复制给它，不需要自己解释。
