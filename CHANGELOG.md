# Changelog

本项目使用日期和版本记录实际完成的修改。规划中的功能只写入 ROADMAP，不写入已完成记录。

## [0.2.0] - 2026-08-10

### Added

- 新增 Research Report 0.2：稳定 `report_id`、修订号、生成元数据、研究模式、更正历史、风险字段、质量摘要和人工确认 Gate。
- 新增正式 Evidence Ledger，区分来源对主张的支持、反驳、归属和背景关系。
- 新增 OpenAI Responses API 搜索调用、完整 action sources 与 URL citation provenance 提取和来源匹配。
- 新增独立版本化 FactCheck Artifact、第二次搜索、反证记录和高风险主张自动队列。
- 新增来源 URL 规范化、追踪参数清理、重复页面、同发布者和疑似转载分组。
- 新增透明质量指标和 Gate，包括来源覆盖、独立来源、高风险核查、来源类型、重复转载、无来源归属和 provenance 匹配。
- 新增不可覆盖的 r1/r2 报告历史、独立核查工件保存和更正记录。
- 新增 Research Report 0.1 → 0.2 确定性迁移与兼容读取。
- 新增 V0.2 Codex Draft 示例、真实编辑评测方法和三类题材的去内容化汇总。

### Changed

- `research-topic` Skill 改为 Research Draft → 新检索 Fact Check → Quality Gate 的两阶段流程。
- 所有构建、API、Skill、迁移和复核入口统一执行完整嵌套 Schema 与业务规则校验。
- 报告输出路径加入主题、报告 ID 和修订号，避免同名报告静默覆盖。
- OpenAI API 自动研究改为两个独立调用，并请求完整搜索来源元数据。
- 示例报告、README、PRD、ROADMAP、AGENTS、架构和 HANDOFF 同步到 V0.2。

### Validation

- 68 项自动测试全部通过，覆盖完整 Schema、错误输入、API Schema 兼容、provenance、Fact Check、人工确认 Gate、来源去重、修订和迁移。
- 三类真实公开题材完成端到端评测：两份通过并停在 `reviewed`，一份高风险动态热点按预期被 Gate 拦在 `draft`。
- 官方 Skill Creator 校验通过；离线示例、迁移、修订安全和干净虚拟环境安装检查通过。

### Security

- 完整真实 Research Report 和 FactCheck Artifact 继续只保存在被 Git 忽略的 `reports/`。
- 无法对应真实工具 provenance 的来源会降级，不能默认为已检查或支撑 confirmed fact。
- 任何报告都不会自动进入未来 Script Agent；通过质量 Gate 后仍需用户明确确认。

## [0.1.0] - 2026-08-10

### Changed

- GitHub 仓库 `HWang0310/deep-talk-studio` 已改为公有，便于 ChatGPT 直接进行产品与架构 Review。
- 新增正式版本的 GitHub Release 与未来软件包发布规则。
- 已发布首个正式版本：[DeepTalk Studio V0.1.0](https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.1.0)。

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
