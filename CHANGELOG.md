# Changelog

本项目使用日期和版本记录实际完成的修改。规划中的功能只写入 ROADMAP，不写入已完成记录。

## [0.1.0] - 2026-08-10

### Added

- 初始化 DeepTalk Studio 独立 Git 项目。
- 新增仓库级 `research-topic` Codex Skill 和报告契约参考。
- 新增 Research Report 0.1 数据模型、JSON Schema 和交叉引用校验。
- 新增事实、报道、当事方说法、评论和未证实信息的分类。
- 新增时间线、多方观点、冲突、未决问题、内容角度和 Script Agent 交接结构。
- 新增 Markdown 渲染与按日期保存的 Markdown/JSON 双格式报告。
- 新增不依赖安装的 `scripts/deeptalk` 命令行入口。
- 新增 OpenAI Responses API `web_search` 可选提供器，支持结构化输出且不保存密钥。
- 新增虚构示例报告和 15 项自动测试。
- 新增 README、PRD、ROADMAP、AGENTS、HANDOFF、架构、设计和实施计划文档。

### Security

- 默认忽略真实研究报告、环境变量文件、缓存和本地虚拟环境。
- API 错误对外只显示状态与可操作信息，不回显密钥。

