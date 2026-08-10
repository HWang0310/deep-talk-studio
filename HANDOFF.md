# DeepTalk Studio 交接记录

更新时间：2026-08-10
当前版本：V0.3.0 / `0.3.0`
当前正式分支：`main`
GitHub：https://github.com/HWang0310/deep-talk-studio （公有仓库）
正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.3.0

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.2.1 的正式验收，实施 **V0.3 Topic Discovery**：让用户可以问“今天讲什么”，获得少量可解释候选题，只回复编号后直接进入已有 V0.2 Research Workflow。本轮不实现 Script Agent、素材、视觉、剪辑或发布。

## 2. 本轮完成了什么

- 建立版本化默认 Channel Profile，定位为 B 站真人深度口播；用户无需手工配置。
- 新增独立 `Topic Candidate Set 0.3` 和 `Research Handoff Brief 0.3`，没有修改 Research Report 0.2。
- 新增 72 小时发现窗口，并支持最近 14 天开始、但在 72 小时内出现关键进展的持续事件。
- 新增轻量 Source Seed Preflight、Eligibility Gate 和风险降级：匿名传言、无公开资料、纯情绪、未证实严重指控和模仿型题材不能进 Top 5；重大快速事件或高风险弱证据题材会成为 `watch`。
- 新增固定透明评分：可核查性 30%、深度冲突 25%、新鲜度 20%、频道匹配 15%、公开关注信号 10%；五项理由由搜索步骤提供，但总分、标签、首选和排序全部由程序计算。
- 新增事件聚类去重、单分类最多两项、最多 5 张短卡片和一个首选；Creator signal 是可选辅助信号，不是事实证据。
- 新增按日期保存的 discovery 历史和 latest 指针，历史不可静默覆盖；用户只回 `1` 或 `研究 1` 就能得到正式 Research Handoff。
- 新增 `discover-topics` Skill 和 API/CLI 自动化入口；`research-topic` 已能接收 Handoff，不再重复要求标题。
- 新增 16 项 V0.3 测试，原有 85 项测试保持通过；发布前完整验证共 101 项测试全部通过。

## 3. 创建 / 修改了哪些重要文件

- `config/channel-profile.json`：默认频道定位与版本。
- `src/deeptalk_studio/discovery.py`：时间、Preflight、评分、去重、类别多样性与 Research Handoff。
- `src/deeptalk_studio/discovery_validation.py`：Raw / Candidate Set / Handoff 契约和机器字段校验。
- `src/deeptalk_studio/discovery_renderer.py`、`discovery_storage.py`：短卡片渲染、不可覆盖历史和 latest 指针。
- `src/deeptalk_studio/schema.py`、`models.py`：Candidate Artifact 0.3 Schema 与值对象。
- `src/deeptalk_studio/workflow.py`、`providers/openai.py`、`prompt.py`、`cli.py`：Discovery API、保存、CLI 和后续 Research 接口。
- `.agents/skills/discover-topics/`：新的自然语言选题 Skill；`.agents/skills/research-topic/`：编号交接支持。
- `docs/TOPIC_DISCOVERY_CONTRACT.md`、`docs/TOPIC_DISCOVERY_EVALS.md`、`evaluations/v0.3.0-summary.json`：契约、评测方法和去内容化汇总。
- `README.md`、`PRD.md`、`ROADMAP.md`、`AGENTS.md`、`docs/ARCHITECTURE.md`、`CHANGELOG.md`、`docs/releases/v0.3.0.md`：同步 V0.3。

## 4. 当前架构是什么

```text
模式 A：用户直接主题
→ V0.2 Research Draft
→ Independent Fact Check
→ Quality Gate

模式 B：用户“今天讲什么？”
→ Topic Discovery + 轻量 Preflight
→ Topic Candidate Set 0.3（JSON 是机器接口，Markdown 是阅读版）
→ 用户只回复编号
→ Research Handoff Brief 0.3
→ 同一条 V0.2 Research Draft → Fact Check → Quality Gate
```

Topic Discovery 只决定“是否值得研究”，不确认事实。Source Seeds 只是可追踪的公开研究入口；完整证据账本、独立事实核查和质量 Gate 仍完全由 V0.2 执行。

## 5. 已经可以运行什么

- 在 Codex 中直接说“今天讲什么？”“帮我找几个科技选题”“换一批”或“只看商业”。
- 得到最多 5 个候选、一个首选、why now、核心冲突、风险、时效和机器计算总分。
- 只回复 `1` 或 `研究 1`，无需再复制标题，开始该题的深度 Research Workflow。
- API 自动化：`./scripts/deeptalk discover "今天有什么值得讲？"`、`select-topic "1"`、`research-selected "1"`。
- 离线 Codex 内容入口：`prepare-discovery` 保存 Candidate Set；没有 API Key 时 CLI 会明确提示使用 Codex Skill，不会假装联网完成。

## 6. 还不能运行什么

- Script Agent 或成品原创口播稿。
- 素材搜索、截图/版权建议、Remotion、HyperFrames、图表和视频生成。
- 剪辑方案、字幕、标题、封面、平台发布和运营数据学习。
- 云端选题库、自动无人审核发布，或根据单一创作者内容决定选题。

## 7. 已知问题

- Preflight 只能判断资料入口和结构，不能替代后续完整事实核查；快速事件仍会变化。
- 事件聚类是第一版稳定事件键 + 确定性排序，面对语义完全不同但本质相同的标题仍需要搜索步骤正确赋予事件键；后续可用真实评测持续校准，但不能变成黑箱推荐算法。
- API 模式需要 `OPENAI_API_KEY`；本轮没有使用用户密钥，不产生 API 费用。没有 Key 时 Codex Skill 使用宿主联网能力。
- Creator signal 若平台公开页面无法稳定访问会直接缺失，不影响 Discovery；系统不绕过登录、风控或限制。
- 真实 discovery artifacts 保持本机 Git ignore，目前没有云端历史库。
- GitHub `v0.3.0` 正式发布已创建并核验；Release 包含 GitHub 自动生成的 ZIP/TAR 源码包，不发布空的软件包。

## 8. 重要技术决策

1. 用独立 Candidate Artifact 0.3，而不是扩展 Research Report 0.2 或让 Research 解析 Markdown。
2. 模型/Skill 只可提供候选判断和评分理由；总分、资格、首选、排序、身份、时间和 provenance 是机器字段。
3. 可核查性权重最高；Top 5 前先过轻量资料 Gate，不能因热度绕过。
4. `watch` 是保留未来可能性，不是低分推荐；它不在普通用户的 Top 5 中。
5. 选择编号转换为 JSON Handoff；模式 A 和模式 B 在 Research Workflow 汇合，避免重复实现研究逻辑。
6. API Seed 必须匹配本次 Web Search provenance；Codex Seed 仅在实际打开后标为 `manual_open`。
7. 完整真实热点列表、网页笔记与 Candidate Set 默认不提交公有仓库；只提交去内容化评测汇总。

## 9. 哪些问题需要产品经理决定

请 ChatGPT Review：

1. Candidate Artifact 0.3、五维评分与 Eligibility Gate 是否符合产品边界。
2. 事件键第一版去重和“单分类最多两项”是否足够保守，或是否需要下一版调整。
3. V0.3 是否正式验收通过，并是否进入 V0.4 Script Agent；若通过，Script Agent 只能读取已 `reviewed` 且经用户确认的 Research Report。

## 10. 建议下一阶段做什么

若 V0.3 通过 Review，进入 **V0.4 Original Script Agent**：只读取已通过 V0.2 Quality Gate 且用户确认的 Research Report，生成原创分析框架和口播稿，并保留事实回链、禁讲项、时长/结构和相似表达风险检查。不要提前做素材、剪辑或发布。

## 11. 本轮验收记录

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：101 项全部通过。
- 新增测试覆盖 Schema、未知/缺失字段、固定权重、机器总分、72 小时、14 天持续事件、陈旧事件、Source Seed URL、匿名传言、高风险弱证据 watch、Creator signal 缺失、无虚构 engagement、事件去重、类别多样性、历史不覆盖、latest 选择、编号交接、Codex/API、CLI error 和模式 A 回归。
- 已完成 Broad、Tech / Business、Social / Public 三类真实公开 Discovery 评测：前两类各形成一个可选候选，Social / Public 因资料不足只保留 `watch`；没有为凑足候选降低 Gate。Broad 场景实际运行了编号选择并生成 Research Handoff。
- `docs/TOPIC_DISCOVERY_EVALS.md` 记录方法，`evaluations/v0.3.0-summary.json` 只保留去内容化结果；完整 artifacts 位于 gitignored `discoveries/evaluations/`。
- `python3 -m compileall -q src tests`、示例 Research/Draft CLI、Discovery 选题与编号交接端到端、干净环境安装 `0.3.0`、JSON 校验、密钥扫描、Git diff 检查均已通过。
- `discover-topics` 和 `research-topic` Skills 已通过官方校验；GitHub `main` 与 `v0.3.0` Release 已核验。

## 12. 版本发布规则

每个正式版本继续使用 GitHub Release。V0.3.0 已提供 `v0.3.0` 标签和 GitHub 自动生成的 ZIP/TAR 源码包；项目当前仍不发布空 GitHub Package。发布过程没有 force push，也没有重写 `main` 历史。

## 给用户的下一步操作

下一步：只把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.3 Topic Discovery：GitHub 仓库是 https://github.com/HWang0310/deep-talk-studio ，Release 是 https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.3.0 。请完整阅读 HANDOFF.md，再 Review Candidate Artifact、评分模型、Eligibility Gate、事件去重、Source Seeds、用户选编号进入 Research 的流程、测试和真实评测。如果通过，请决定是否进入 V0.4 Script Agent，并直接给我下一轮发给 Codex 的任务。不要让我自己总结。

如果 ChatGPT 暂时打不开仓库，只需把本文件 `HANDOFF.md` 全文复制给它，不需要自己解释。
