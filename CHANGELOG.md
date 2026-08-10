# Changelog

本项目使用日期和版本记录实际完成的修改。规划中的功能只写入 ROADMAP，不写入已完成记录。

## [0.2.1] - 2026-08-10

### Fixed

- confirmed fact 独立确认现在只接受 `supports + matched + independent + 不同 independence_group`；`unknown`、`related`、`duplicate`、`syndicated` 均不能贡献独立确认。
- context-only 与未匹配来源不再抬高 claim source coverage；未匹配 attribution 不再解除无来源归属；duplicate / syndicated 不再抬高来源类型或 provenance 指标。
- Fact Check 新来源与 Research Draft 来源统一执行 URL 规范化、追踪参数去除、重复、同发布者、转载和 independence grouping；保存的 Artifact 与 reviewed report 使用相同确定性结果。
- 重复 URL 的判断优先于显式转载提示，使来源规范化可重复执行且结果稳定。

### Changed

- 新增内部 `API_RESEARCH_DRAFT_JSON_SCHEMA`；OpenAI Research Pass 只生成研究内容，身份、revision、时间、状态、Fact Check、provenance、quality 和审批字段由程序生成。
- 保持 Research Report / FactCheck Artifact Schema `0.2` 和全部质量阈值不变。
- `research-topic` Skill、报告契约、示例和架构文档同步 hardened 规则。

### Validation

- 85 项自动测试全部通过，原 68 项继续通过，新增独立来源、API 字段所有权、质量指标和 Fact Check 归组回归测试。
- 三类真实公开题材重新运行：稳定商业与争议公共政策进入 `reviewed`；快速公共安全热点因未解决高风险信息保持 `draft`。
- sample、validate、prepare-draft、review-report、迁移、修订防覆盖、Skill、Python 3.9、干净安装和密钥扫描完成验证。

### Security

- 模型无法通过 API Research payload 伪造 quality summary 或 approval 状态。
- 完整真实评测报告继续只保存在 gitignored `reports/`，公开仓库仅保存去内容化汇总。

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
