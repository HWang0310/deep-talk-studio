# DeepTalk Studio

DeepTalk Studio 是一个面向长期 B 站个人 IP 的 AI 内容生产项目。它服务于真人露脸深度口播：先建立可核查的研究底稿，再逐步扩展到原创口播稿、素材建议、可视化、剪辑和发布。

当前版本是 **V0.4.1**。现在有两个研究入口：直接给主题，或问“今天讲什么？”。研究完成并通过独立事实核查后，你只需确认“开始写稿”，系统就会把这次确认保存为新版本，再生成原创口播稿并做独立 Script Review。

## 现在最简单的用法

在 Codex 中打开这个仓库，然后直接说：

> 请用 DeepTalk Studio 研究“你想研究的话题”，生成 Research Report。

或者直接说：

> 今天讲什么？

> 帮我找几个科技选题。

> 最近社会热点有什么值得讲？

仓库里的 `discover-topics` 和 `research-topic` Skill 会被 Codex 自动识别。前者只做轻量资料预检、去重和排序；后者才联网搜索、整理证据并完成独立 Fact Check。你不需要理解代码，也不需要自己拼命令。

当报告通过质量 Gate 后，直接说：

> 确认进入写稿，做成 8 分钟的 B 站口播稿。

仓库里的 `write-script` Skill 会先记录你的确认，再生成稿件和独立审稿结果。之后也可以直接说“做长一点”“第二段更紧凑”或“比较这两个版本”。每次修改都会建立新版本，不覆盖旧稿。

选题结果会保存在本机：

```text
discoveries/YYYY/MM/DD/选题批次ID.md
discoveries/YYYY/MM/DD/选题批次ID.json
discoveries/latest.json
```

每次都是独立历史记录；`latest.json` 只用于让你下一句回复“1”时能知道你选的是哪一题。真实选题列表默认不会上传 GitHub。

报告默认保存到：

```text
reports/YYYY/MM/DD/主题/报告ID/research-report-r0001.md
reports/YYYY/MM/DD/主题/报告ID/research-report-r0001.json
reports/YYYY/MM/DD/主题/报告ID/fact-check-for-r0001-核查ID.json
reports/YYYY/MM/DD/主题/报告ID/research-report-r0002.json
```

`reports/` 默认不会上传 GitHub，避免未经编辑审查的研究材料被意外公开。

稿件默认保存在本机：

```text
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0001.json
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0001.editor.md
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0001.teleprompter.md
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-review-for-r0001-审稿ID.json
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0002.json
```

完整真实稿件同样默认不会上传 GitHub。

## 项目现在能做什么

- 接受社会、时事、商业、科技、网络热点或公共事件主题；
- 当你没有选题时，寻找最近 72 小时、或最近 14 天持续事件的新进展；默认只给最多 5 个候选，并明确一个“首选”；
- 对候选执行轻量资料预检：只有实际打开或 API 可追溯的不同合格来源方向才可推荐；同链接、同发布者或同网站不能重复凑数；
- 自动拒绝事件时间倒置、明显未来时间或不足 7 个原始候选的“看似完成”结果；高风险但资料薄弱的事件只列为观察，不进入推荐；
- 候选的资格、理由、总分、推荐、展示顺序、首选和统计数均由程序重新计算；被手工改写的候选文件不能继续使用；
- 默认先让分类多样，再用同分类高分题补足空位，因此用户只看科技时仍最多可得到 5 个不同事件；
- 用可解释的五项评分计算总分：可核查性 30%、深度冲突 25%、新鲜度 20%、频道匹配 15%、公开关注信号 10%；总分由程序计算；
- 让你只回复“1”或“研究 1”就把候选的研究问题、核心冲突、风险提示和资料入口交给 Research Workflow；
- 搜集并登记可点击的公开来源；
- 记录来源是否真的出现在本次搜索或引用工具结果中；
- 整理事件时间线；
- 区分已确认事实、媒体报道、当事方说法、评论观点和尚未证实的信息；
- 汇总不同来源与不同立场；
- 指出观点冲突、证据边界和仍需追问的问题；
- 推荐原创内容切入角度，并生成给 Script Agent 使用的安全交接字段；
- 用 Evidence Ledger 标明来源是支持、反驳、归属说法还是只提供背景；
- 识别重复 URL、同发布者和疑似转载，避免把同一信源误算成多源；
- 只有明确标为独立、provenance 已匹配且属于不同分组的支持来源，才能形成两份独立确认；`unknown` 不会被猜成独立；
- 自动把高风险主张放入二次核查队列，并单独保存 FactCheck Artifact；
- 计算来源覆盖率、独立来源覆盖率、高风险核查率等质量指标；
- 保留不可覆盖的报告修订版和更正记录；
- 把用户的写稿确认保存为新的、不可覆盖的 Research Revision；未批准报告无法生成稿件；
- 用 Script Profile 0.4 生成适合 B 站真人露脸的原创口播稿，默认约 12 分钟，也可用自然语言调整时长；
- 在每个稿件段落保留事实、归因、分析、转场或问题类型，并回链 Research Claim 与 Evidence；
- 自动拦截未核查事实、禁讲结论、伪造机器字段和高风险越界；计算 must-keep 覆盖、字数和估算时长；
- Writer 完成后由独立 Reviewer 检查 15 个维度；有事实或归因阻断问题的稿件不能成为 `reviewed`；
- 同时输出含编辑线索的 Editor 版和可直接朗读、没有机器 ID 的 Teleprompter 版；
- 任何稿件修改都产生不可覆盖的新 revision，并可比较两个版本；
- Review 的 15 项检查都必须和具体问题闭环；事实安全检查失败时，系统拒绝把稿件误判为通过；
- `reviewed` 稿件会校验对应的 Review Artifact、原稿版本与内容指纹，单独改状态无效；
- 修改、移动或插入段落时保留已有 Beat 身份，删除的 Beat ID 不再复用，因此版本比较不会把一次插入误报为整篇重写；
- 在保存前执行完整 Schema 和跨字段校验，错误会给出中文提示。

## 还不能做什么

V0.4.1 不包含素材搜索或下载、图片和视频生成、剪辑方案、B 站发布及其他平台分发。稿件成为 `reviewed` 只代表通过工程与独立编辑检查，不代表已经获准发布；发布前仍需要人类最终确认。路线已预留，见 [ROADMAP.md](ROADMAP.md)。

## 不依赖联网的检查方式

项目要求 Python 3.9 或更高版本，不需要安装第三方包。

生成虚构示例报告：

```bash
./scripts/deeptalk sample
```

校验当前 Research Report 示例：

```bash
./scripts/deeptalk validate examples/sample-research-report.json
```

运行全部测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Codex Skill 模式还可以把研究内容整理为带机器字段的草稿，再应用独立核查：

```bash
./scripts/deeptalk prepare-draft examples/sample-codex-draft-input.json
./scripts/deeptalk review-report 草稿.json fact-check.json
```

普通用户不需要自己执行这两条命令，Codex 会代为完成。

V0.4 的底层调试入口包括：

```bash
./scripts/deeptalk approve-report reviewed-report.json --confirmation "确认开始写稿"
./scripts/deeptalk prepare-script approved-report.json script-content.json --duration "8 分钟"
./scripts/deeptalk review-script approved-report.json script-draft-r0001.json review.json
./scripts/deeptalk compare-script script-draft-r0001.json script-draft-r0002.json
```

这些命令面向测试和自动化；普通用户只需在 Codex 中用自然语言确认和修改。

开发或自动化时也可以使用：

```bash
./scripts/deeptalk discover "今天有什么值得讲？"
./scripts/deeptalk discover "最近科技商业有什么值得讲？" --category tech
./scripts/deeptalk select-topic "1"
```

没有 API 密钥时，这些联网命令会提示回到 Codex 自然语言入口；不会假装完成搜索。

## 可选的 API 自动化入口

未来需要脱离 Codex 批量运行时，可以配置 `OPENAI_API_KEY`，再执行：

```bash
./scripts/deeptalk research "要研究的主题"
```

该入口使用 OpenAI Responses API 的 `web_search` 与结构化输出，并保留 `web_search_call`、URL citation 和完整 action sources 的可用 provenance。API 模型只生成研究内容；报告身份、修订、状态、质量和审批字段全部由程序生成，模型无法自报通过。研究与事实核查是两次独立调用。密钥只能放在环境变量或密码管理器中，绝不能写进仓库。没有 API 密钥也不影响在 Codex 中使用仓库 Skill。

实现依据：[OpenAI Web Search 文档](https://developers.openai.com/api/docs/guides/tools-web-search)、[Structured Outputs 文档](https://developers.openai.com/api/docs/guides/structured-outputs)、[Codex Skills 文档](https://learn.chatgpt.com/docs/build-skills)。

## 项目结构

```text
.agents/skills/discover-topics/ Codex 可自动发现的选题发现工作流
.agents/skills/research-topic/  Codex 可自动发现的研究工作流
.agents/skills/write-script/    Codex 原创写稿、独立审稿与版本修改工作流
config/channel-profile.json     V0.3 默认频道定位
config/script-profile.json      V0.4 口播风格、时长和原创性约束
src/deeptalk_studio/            研究与稿件模型、校验、渲染、保存和 API 适配
scripts/deeptalk                无需安装的统一入口
examples/                       虚构 Research、Script 和 Review 输入示例
evaluations/                    去内容化真实编辑评测汇总
tests/                          自动测试
docs/                           架构、设计和实施计划
PRD.md                          产品要求
ROADMAP.md                      长期路线
AGENTS.md                       未来 Codex 工作规则
CHANGELOG.md                    实际修改记录
HANDOFF.md                      每轮开发交接
```

## 长期协作方式

- ChatGPT：产品经理 / 架构师，负责 Review、优先级和下一轮需求。
- Codex：工程师，负责实现、测试、修复、文档和 GitHub。
- 用户：只负责复制、粘贴和确认，不负责总结技术内容。

每轮开发结束后，以 [HANDOFF.md](HANDOFF.md) 为唯一交接入口。V0.4.1 的稿件契约与真实评测见 [docs/SCRIPT_CONTRACT.md](docs/SCRIPT_CONTRACT.md) 和 [docs/SCRIPT_EVALS.md](docs/SCRIPT_EVALS.md)。

正式版本的 GitHub 发布与未来软件包规则见 [RELEASE_POLICY.md](RELEASE_POLICY.md)。
