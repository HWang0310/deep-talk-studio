# DeepTalk Studio 交接记录

更新时间：2026-08-10  
当前版本：V0.1 / `0.1.0`  
当前分支：`main`  
GitHub：`https://github.com/HWang0310/deep-talk-studio`（公有仓库）

## 1. 本轮任务是什么

从零创建可长期维护的 DeepTalk Studio 项目。V0.1 只搭建项目基础和 Research Workflow：用户给出一个主题后，系统能搜索公开资料、区分事实与观点、整理时间线和多方立场、发现冲突、提出原创切入角度，并保存带来源的结构化 Research Report。

## 2. 本轮完成了什么

- 建立独立 Git 项目、V0.1 设计和实施计划。
- 建立 Codex 可自动发现的 `research-topic` Skill。
- 建立 Research Report 0.1 的结构化契约。
- 实现来源、主张、时间线、观点、冲突、问题、角度、事实核查和 Script Agent 交接字段。
- 实现跨字段 ID、HTTP(S) URL、事实来源和枚举校验。
- 实现 Markdown/JSON 双格式输出和安全文件路径。
- 实现离线示例、报告构建、报告校验和可选 API 联网研究命令。
- 实现 OpenAI Responses API `web_search` + Structured Outputs 适配器。
- 编写并运行 15 项自动测试。
- 补齐长期协作、产品、路线、架构、变更和交接文档。

## 3. 创建 / 修改了哪些重要文件

- `README.md`：普通用户入口和项目总览。
- `PRD.md`：产品目标、边界、要求和验收。
- `ROADMAP.md`：V0.1 到发布辅助的阶段路线。
- `AGENTS.md`：未来 Codex 的阅读顺序、工程和交付规则。
- `CHANGELOG.md`：V0.1 实际修改记录。
- `.agents/skills/research-topic/`：Research Workflow Skill。
- `src/deeptalk_studio/`：模型、校验、渲染、保存、CLI 和提供器。
- `scripts/deeptalk`：无需安装的统一命令入口。
- `examples/sample-research-report.json`：虚构格式示例。
- `tests/`：15 项自动测试。
- `docs/ARCHITECTURE.md`：模块、数据流和未来接口。
- `docs/superpowers/`：V0.1 设计说明和实施计划。

## 4. 当前架构是什么

当前是“Research Skill + 确定性 Python 核心”的两层架构。Codex Skill 负责需要判断力的联网搜索、来源比较和观点分析；Python 核心只负责稳定的报告契约、校验、渲染和保存。

模块间使用版本化 JSON 工件连接。未来 Topic Discovery、Fact Check、Perspective Analysis、Script Writing、Material Search、Visual Generation、Editing Plan 和 Publishing 都应消费或产生明确工件，不共享一个巨大 Prompt。

## 5. 已经可以运行什么

普通用户可在仓库内直接对 Codex 说：

> 请用 DeepTalk Studio 研究“某个话题”，生成 Research Report。

开发或验收入口：

```bash
./scripts/deeptalk sample
./scripts/deeptalk validate examples/sample-research-report.json
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

配置 `OPENAI_API_KEY` 后，还可独立运行：

```bash
./scripts/deeptalk research "某个话题"
```

## 6. 还不能运行什么

- “今天讲什么”的自动 Topic Discovery。
- 独立二次事实核查与人工 Review 面板。
- 原创成品口播稿生成。
- 新闻截图、图片、视频片段和公开文件的自动素材包。
- 图表、Remotion、HyperFrames 等视觉生成。
- 剪辑方案、字幕、标题、封面和 B 站发布。
- 小红书、抖音等平台适配。

## 7. 已知问题

- Codex Skill 依赖宿主提供联网搜索工具；若宿主没有联网能力，只能处理用户提供的来源。
- 独立 `research` 命令需要用户自己的 OpenAI API 密钥，会产生 API 使用费用；V0.1 没有做费用预算界面。
- 机器校验能保证“引用结构完整”，不能自动保证现实世界中的每个结论都正确，发布前仍需人类编辑 Review。
- 真实研究报告默认不提交 Git；未来是否建立私有内容库需要产品经理决定。
- 目前只有虚构示例和工程测试，尚未使用一个真实热点完成编辑质量评分。
- 当前电脑的普通 `git push` 在 HTTPS 通道中持续挂起，因此首次发布改用已授权的 GitHub API。远程 `main` 与本地 `main` 的文件树已做哈希比对并完全一致，但两边提交历史的 SHA 不同。未来 Codex 不应盲目强推；先检查远程树，再继续用 API 发布或修复 Git 传输通道。

## 8. 重要技术决策

1. 把自然语言研究放在仓库级 Skill，而不是塞进一个巨大应用 Prompt。
2. 用 Python 标准库实现核心，V0.1 无需安装第三方依赖。
3. Markdown 给人阅读，JSON 是未来 Agent 的正式接口。
4. 强制区分 `confirmed_fact`、`media_report`、`party_statement`、`commentary`、`unverified`。
5. `confirmed_fact` 必须有来源，所有跨字段 ID 必须存在。
6. 研究提供器通过接口隔离；OpenAI 只是当前可选实现，不锁死未来工具。
7. 真实报告默认忽略 Git，防止未经审查的内容意外公开。
8. V0.1 不提前实现自动选题和写稿，控制复杂度。
9. 每个正式版本号必须创建并核验 GitHub Release；软件包只在存在真实可安装交付物时发布。

## 9. 需要产品经理决定的问题

请 ChatGPT Review 后决定：

1. V0.2 是否按建议优先做“研究质量 + Fact Check”，再做 Topic Discovery。
2. 第一批真实评测选题选哪 3–5 个，以及编辑评分标准。
3. 真实 Research Report 是仅保存在本机，还是进入单独的私有内容仓库。
4. 高风险议题是否需要强制两个人工确认点。
5. V0.2 是否保留当前报告字段，还是先调整契约再积累真实报告。

## 10. 建议下一阶段做什么

建议下一阶段是 **V0.2 Research Quality & Fact Check**，先不要立即做自动选题或写稿。

最小目标：选 3–5 个真实话题跑通 V0.1；建立人工评分表；补充来源去重、转载识别、主张—来源覆盖率、争议主张二次核查和报告更正记录。只有研究底稿稳定，未来 Script Agent 才不会把不可靠信息包装成流畅口播。

## 11. 本轮验收记录

2026-08-10 已完成以下最终验收：

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`：15 项全部通过。
- Python 源码编译检查：通过。
- `./scripts/deeptalk sample`：成功生成 Markdown 和 JSON 两份报告。
- 对刚生成的 JSON 再运行 `validate`：通过。
- 在全新临时虚拟环境安装项目并运行 `deeptalk --help`：通过。
- 官方 Skill Creator `quick_validate.py`：`Skill is valid!`。
- Git diff 空白错误、占位符和常见密钥格式扫描：通过。
- GitHub 远程 `main` 与本地最终文件树哈希比对：完全一致；`v0.1.0` 已指向远程最终版本。

## 12. 版本发布规则

用户已要求后续每个正式版本发布到 GitHub。项目新增 `RELEASE_POLICY.md`：每个正式版本号都必须有 GitHub Release、清晰更新说明和自动源码下载；未完成的小改动不单独发布。V0.1.0 将作为第一个正式 Release 发布。软件包暂不创建，因为当前没有需要安装的成品。

## 给用户的下一步操作

下一步：把 GitHub 仓库链接发给 ChatGPT，并原样复制下面这段话：

> 这是 Codex 完成的 DeepTalk Studio V0.1：https://github.com/HWang0310/deep-talk-studio 。请作为产品经理和架构师完整 Review。先阅读 README.md、PRD.md、ROADMAP.md、AGENTS.md 和 HANDOFF.md，再检查 Research Workflow、报告结构、事实与观点分类、来源规则、测试和未来扩展方式。请重点判断 V0.1 是否达到验收标准，并决定 V0.2 的优先级。最后请直接给我一段可以原样发给 Codex 的下一轮任务，不要让我自己总结。

如果 ChatGPT 表示无法访问仓库，你只需把本文件 `HANDOFF.md` 的全文复制给它，不需要自己解释。
