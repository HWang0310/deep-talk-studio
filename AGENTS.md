# DeepTalk Studio 工程协作规则

本文件面向进入仓库的未来 Codex。用户不是工程师，不应被要求理解架构、代码或命令行。

## 开始任何任务前

按顺序阅读：

1. `HANDOFF.md`：当前状态、上轮决定和下一阶段建议。
2. `PRD.md`：产品目标、边界和验收标准。
3. `ROADMAP.md`：阶段划分，防止提前实现远期功能。
4. `docs/ARCHITECTURE.md`：模块与工件接口。
5. `CHANGELOG.md`：已经实际做过什么。
6. `RELEASE_POLICY.md`：正式版本如何发布到 GitHub。
7. 与任务直接相关的代码、测试和 Skill。

若文件与当前代码不一致，以可运行代码和测试为事实，同时在本轮修正文档。

## 工作原则

- 主动完成设计、实现、测试、调试、文档和安全的 Git 操作。
- 合理工程决策由 Codex 自行完成；只有会实质改变产品方向或需要新权限时才问用户。
- 面向用户只说结果、影响和下一步，不要求其自己总结技术内容。
- 任何功能或修复先写失败测试，再做最小实现。
- 不削弱校验器来迁就错误的模型输出。
- 保持模块单一职责，通过版本化 JSON 工件连接未来 Agent。
- 当前 V0.2 不提前实现 Topic Discovery、Script Writing、素材、视觉、剪辑和发布。
- Research Draft 与 Fact Check 必须是不同步骤；Fact Check 必须有新的搜索 provenance。
- 未通过质量 Gate 的报告只能保持 `draft`，不能手工改状态绕过。
- 即使质量 Gate 通过，未来 Script Agent 前也必须保留用户明确确认。

## 内容与研究安全

- Research Agent 建立原创研究底稿，不找别人稿子改写。
- 不复制、洗稿或模仿任何具体创作者的独特表达。
- 明确区分事实、报道、当事方说法、评论和尚未证实的信息。
- 重要事实保留来源；搜索摘要不算完成核查。
- 高风险、快速变化或证据不足的结论必须暴露局限性。
- 不把密码、令牌、API 密钥、登录信息或恢复码写入仓库、报告或日志。

## 验证命令

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
./scripts/deeptalk sample
./scripts/deeptalk validate examples/sample-research-report.json
./scripts/deeptalk prepare-draft examples/sample-codex-draft-input.json
```

修改 `.agents/skills/research-topic` 后，还要运行 Skill Creator 的 `quick_validate.py`。若本机脚本缺少 PyYAML，可在临时目录安装依赖运行，不能把临时依赖提交到仓库。

## 每轮结束前必须完成

1. 运行与风险相称的全部测试和端到端检查。
2. 更新 `CHANGELOG.md`，只记录实际完成内容。
3. 完整更新 `HANDOFF.md`，包括能力、限制、已知问题、决定和产品问题。
4. 保证 `HANDOFF.md` 最后有 `## 给用户的下一步操作`，写出用户可原样复制给 ChatGPT 的具体文字。
5. 检查 README、PRD、ROADMAP、架构和实际行为一致。
6. 检查 Git diff，避免提交报告草稿、密钥、缓存或无关文件。
7. 如果本轮形成新的正式版本号，严格执行 `RELEASE_POLICY.md`，创建并核验 GitHub Release；不要发布空软件包。

不允许只在聊天中汇报而不更新 HANDOFF。
