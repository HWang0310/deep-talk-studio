# DeepTalk Studio

DeepTalk Studio 是一个面向长期 B 站个人 IP 的 AI 内容生产项目。它服务于真人露脸深度口播：先建立可核查的研究底稿，再逐步扩展到原创口播稿、素材建议、可视化、剪辑和发布。

当前版本是 **V0.2**。输入一个主题后，系统先生成 Research Draft，再单独进行一次新的事实核查，最后由透明的质量 Gate 决定报告只能停在草稿，还是可以进入人工确认。

## 现在最简单的用法

在 Codex 中打开这个仓库，然后直接说：

> 请用 DeepTalk Studio 研究“你想研究的话题”，生成 Research Report。

仓库里的 `research-topic` Skill 会被 Codex 自动识别。它会联网搜索、打开来源、整理证据，再用新的检索完成独立 Fact Check。你不需要理解代码，也不需要自己拼命令。

报告默认保存到：

```text
reports/YYYY/MM/DD/主题/报告ID/research-report-r0001.md
reports/YYYY/MM/DD/主题/报告ID/research-report-r0001.json
reports/YYYY/MM/DD/主题/报告ID/fact-check-for-r0001-核查ID.json
reports/YYYY/MM/DD/主题/报告ID/research-report-r0002.json
```

`reports/` 默认不会上传 GitHub，避免未经编辑审查的研究材料被意外公开。

## 项目现在能做什么

- 接受社会、时事、商业、科技、网络热点或公共事件主题；
- 搜集并登记可点击的公开来源；
- 记录来源是否真的出现在本次搜索或引用工具结果中；
- 整理事件时间线；
- 区分已确认事实、媒体报道、当事方说法、评论观点和尚未证实的信息；
- 汇总不同来源与不同立场；
- 指出观点冲突、证据边界和仍需追问的问题；
- 推荐原创内容切入角度，但不生成成品口播稿；
- 生成给未来 Script Agent 使用的安全交接字段；
- 用 Evidence Ledger 标明来源是支持、反驳、归属说法还是只提供背景；
- 识别重复 URL、同发布者和疑似转载，避免把同一信源误算成多源；
- 自动把高风险主张放入二次核查队列，并单独保存 FactCheck Artifact；
- 计算来源覆盖率、独立来源覆盖率、高风险核查率等质量指标；
- 保留不可覆盖的报告修订版和更正记录；
- 在保存前执行完整 Schema 和跨字段校验，错误会给出中文提示。

## 还不能做什么

V0.2 仍不包含自动选题、成品口播稿、素材下载、图片或视频生成、剪辑方案、B 站发布和其他平台分发。即使报告通过机器 Gate，也不会自动写稿；未来 Script Agent 前还保留一次用户明确确认。路线已预留，见 [ROADMAP.md](ROADMAP.md)。

## 不依赖联网的检查方式

项目要求 Python 3.9 或更高版本，不需要安装第三方包。

生成虚构示例报告：

```bash
./scripts/deeptalk sample
```

校验当前 V0.2 示例报告：

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

## 可选的 API 自动化入口

未来需要脱离 Codex 批量运行时，可以配置 `OPENAI_API_KEY`，再执行：

```bash
./scripts/deeptalk research "要研究的主题"
```

该入口使用 OpenAI Responses API 的 `web_search` 与结构化输出，并保留 `web_search_call`、URL citation 和完整 action sources 的可用 provenance。研究与事实核查是两次独立调用。密钥只能放在环境变量或密码管理器中，绝不能写进仓库。没有 API 密钥也不影响在 Codex 中使用仓库 Skill。

实现依据：[OpenAI Web Search 文档](https://developers.openai.com/api/docs/guides/tools-web-search)、[Structured Outputs 文档](https://developers.openai.com/api/docs/guides/structured-outputs)、[Codex Skills 文档](https://learn.chatgpt.com/docs/build-skills)。

## 项目结构

```text
.agents/skills/research-topic/  Codex 可自动发现的研究工作流
src/deeptalk_studio/            报告模型、校验、渲染、保存与 API 适配
scripts/deeptalk                无需安装的统一入口
examples/                       V0.2 虚构报告与 Codex Draft 输入示例
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

每轮开发结束后，以 [HANDOFF.md](HANDOFF.md) 为唯一交接入口。V0.2 的真实评测方法见 [docs/EVALS.md](docs/EVALS.md)。

正式版本的 GitHub 发布与未来软件包规则见 [RELEASE_POLICY.md](RELEASE_POLICY.md)。
