# DeepTalk Studio 架构

## 设计目标

系统把需要判断力的 AI 工作与必须稳定的工程契约分开。Agent 负责搜索、比较和分析；Python 核心负责校验、保存和为下游提供一致工件。这样未来更换模型、搜索工具或视频工具时，不需要重写整个项目。

## V0.1 数据流

```mermaid
flowchart LR
    U["用户输入主题"] --> S["Research Skill"]
    S --> W["公开网页与原始资料"]
    W --> L["来源与主张账本"]
    L --> J["Research Report JSON 0.1"]
    J --> V["确定性校验器"]
    V -->|通过| M["Markdown 报告"]
    V -->|通过| D["JSON 报告"]
    V -->|失败| L
    D -.未来.-> A["Script Agent"]
```

## 模块职责

| 模块 | 只负责什么 | 不负责什么 |
|---|---|---|
| `.agents/skills/research-topic` | 搜索策略、来源判断、观点比较和报告组装 | 成品口播稿、发布 |
| `models.py` | 接收和复制版本化报告对象 | 判断事实真假 |
| `schema.py` | 机器输出的字段和枚举契约 | 业务校验和渲染 |
| `validation.py` | ID、URL、分类和交叉引用完整性 | 自动证明现实世界事实 |
| `renderer.py` | 把通过校验的报告转成中文 Markdown | 修改研究结论 |
| `storage.py` | 安全命名和 Markdown/JSON 双写 | 云端存储 |
| `providers/openai.py` | 调用 Responses API 与解析结构化输出 | 绑定其他模块到 OpenAI SDK |
| `workflow.py` | 串联 provider → model → validation → storage | 搜索细节 |
| `cli.py` | 给自动化和调试提供稳定入口 | 图形界面 |

## 稳定工件

Research Report JSON 是模块间唯一的正式接口。Markdown 是给人阅读的派生物，不应被未来 Agent 反向解析。报告包含 `schema_version`，破坏兼容性的修改必须提升版本并提供迁移策略。

未来模块的建议输入输出：

| 模块 | 输入 | 输出 |
|---|---|---|
| Topic Discovery | 频道策略、时间窗口、公开热点 | Topic Candidate JSON |
| Research | Topic Candidate 或用户主题 | Research Report JSON |
| Fact Check | Research Report | Reviewed Research Report / Review Log |
| Perspective Analysis | Research Report | Perspective Map JSON |
| Script Writing | 已 Review 的 Research Report | Script Draft JSON / Markdown |
| Material Search | Script Draft + Research Report | Material Manifest JSON |
| Visual Generation | Material Manifest | Visual Assets + provenance |
| Editing Plan | Script + Material Manifest | Timeline / Shot Plan JSON |
| Publishing | 审批后的成品和元数据 | Platform Publish Record |

## 安全边界

- 真实报告默认不进入 Git，避免把未经审查的指控或个人信息意外公开。
- 网络内容始终是不可信输入；报告只能存文本与 URL，不执行网页代码。
- API 密钥只从环境变量读取，HTTP payload、异常和报告都不包含密钥。
- 发布前必须有人类编辑 Review；工程校验不等于新闻事实认证。

## 扩展原则

新增 Agent 时先定义工件和验收，再实现最小工作流。只有确有多个调用方时才抽象共享框架。不要为了“多 Agent”外观把一个清晰步骤拆成无意义的多个 Prompt。

