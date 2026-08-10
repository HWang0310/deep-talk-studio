# Original Script Agent 0.4 契约（V0.4.1 加固）

本文定义 DeepTalk Studio V0.4 从 Research Report 进入原创口播稿的正式边界。JSON 是机器接口；Markdown 只是给编辑和提词使用的派生物。

## 1. Approval Revision

Writer 只接受同时满足以下条件的 Research Report：

- `status = ready_for_script`；
- `quality_summary.gate_status = pass`；
- `fact_check.status = completed`；
- `approval_gate.status = approved`；
- `approval_gate.ready_for_script = true`；
- `approval_gate.user_confirmation` 非空。

确认操作必须创建新 Research revision，并保存用户原始确认文本。原 `reviewed` revision 不覆盖；后续任何研究内容 revision 都会重置 approval。用户撤回或更换底稿时，不能继续沿用旧批准状态。

## 2. Script Profile 0.4

`config/script-profile.json` 是默认创作配置：B 站、真人露脸、中文深度口播，默认 12 分钟、每分钟约 260 个有效口播字符、允许 20% 编辑容差。用户可用“8 分钟”“做长一点”“紧凑一些”等自然语言调整，程序只接受 3–30 分钟。

Profile 同时规定信息密度、故事性、观点冲突、自然归因和原创分析要求，并禁止洗稿、模仿特定创作者、长段引用、AI 报告腔和把未知写成定论。

## 3. Script Draft Artifact 0.4

正式 JSON 至少包含：

- 身份和历史：`artifact_version`、`script_id`、`revision`、`previous_revision`、时间；
- 精确输入绑定：`report_id`、`report_revision`、`script_profile_version`；
- 稿件状态和模式：`status`、`script_mode`；
- 编辑目标：目标时长、标题、论点、观众承诺；
- `beats`、`closing`、研究局限、研究空白；
- must-keep 覆盖和遗漏理由；
- 程序计算的有效字符数、估算时长和修订摘要。
- V0.4.1 的机器拥有 `review_state` 与 `beat_identity`：前者证明 reviewed 状态，后者记录下一个可分配 Beat ID 和退休 ID。

模型或 Skill 只能提交稿件内容。身份、revision、状态、Beat ID、字符数、时长和覆盖字段全部由代码创建，并在每次读取时重新计算。

## 4. Beat grounding

每个 Beat 有一种 `content_kind`：

| 类型 | 允许内容 | 强制边界 |
|---|---|---|
| `fact` | 已确认事实 | 必须引用 `verified confirmed_fact`；高风险 Claim 必须已在 Fact Check 中完成且未 unresolved |
| `attribution` | 当事方、媒体或评论者的说法 | 必须引用对应 Claim，并在自然语言中保留“谁说的”；不能把 confirmed fact 伪装为 Attribution |
| `analysis` | 作者推理、比较和原创洞察 | 必须填写 `analysis_basis_claim_ids`，不能添加研究底稿不存在的新事实 |
| `transition` | 结构推进 | 不得借转场偷放事实 |
| `question` | 开场或追问 | 不得用反问暗示未经支持的结论 |

Beat 的每个 Evidence Link 必须真实存在，并且关联本 Beat 引用或作为分析依据的 Claim。口播正文不得出现 Claim、Evidence 或其他机器 ID。

Research Handoff 的 `must_keep_claim_ids` 由程序计算覆盖；遗漏必须明确写理由，并在 Review 中显示。`avoid_claims` 直接出现在稿件时硬失败；改写后的语义越界由独立 Reviewer 阻断。

## 5. 独立 Script Review Artifact 0.4

Reviewer 读取同一 Research revision 和 Writer 的 Script Draft，但不继承 Writer 的角色，也不联网。它必须完整检查 15 项：

1. factual grounding
2. attribution integrity
3. uncertainty preservation
4. avoid-claim compliance
5. must-keep coverage
6. high-risk boundary
7. analysis / fact separation
8. perspective fairness
9. research-gap integrity
10. narrative structure
11. oral naturalness
12. information density
13. original expression
14. script usability
15. counterargument fairness

少任何一项，Review Artifact 都无效。Issue ID、severity、blocking count 和 gate status 由程序生成。无来源事实、归因错误、禁讲结论、未核实信息事实化、高风险过度断言、关键不确定性丢失、分析伪装事实、填补研究空白和观点歪曲属于 blocking；存在一项就不能进入 `reviewed`。

V0.4.1 使用 `review_consistency_version = 0.4.1` 的确定性 mapping。任何 `fail` check 都必须有对应 typed issue；以下安全 check 还必须有对应 blocking issue：

| Check | 允许的 blocking issue |
|---|---|
| factual grounding | `unsupported_fact` / `unverified_as_fact` |
| attribution integrity | `attribution_error` |
| uncertainty preservation | `material_uncertainty_loss` |
| avoid-claim compliance | `avoid_claim_usage` |
| high-risk boundary | `high_risk_overclaim` |
| analysis / fact separation | `analysis_as_fact` |
| perspective fairness | `perspective_distortion` |
| research-gap integrity | `research_gap_filled` |

编辑性失败也必须有映射的 advisory issue，但不一定阻断 Gate。`not_applicable` 仅可用于 `counterargument_fairness`，并必须提供理由；所有事实安全检查均不可跳过。只要 check、issue 或机器 Gate 不一致，Artifact 被拒绝，不会生成误标为 `reviewed` 的稿件。

通过 Review 的 Artifact 还保存被审稿件内容的 SHA-256。生成的 r2 `review_state` 保存 Review ID、r1 revision、`pass` 和相同指纹。读取 reviewed r2 时，系统会定位对应 Artifact，复验 report/script binding、15 checks、一致性 mapping、Gate 和指纹；仅修改 JSON 的 `status` 或伪造 Review 字段无效。Review fail 的 r2 保持 draft。V0.4.0 无该 linkage 的旧 reviewed JSON 必须重新审查，不能静默信任。

Review 不修改原 r1。它创建 r2：通过则 `reviewed`，失败仍为 `draft`。这不是发布审批，最终发布仍需人类确认。

## 6. 双 Markdown 输出

- Editor Version：显示结构、类型、Claim / Evidence refs、分析依据、风险、研究局限、研究空白和 must-keep 覆盖，供编辑核查。
- Teleprompter Version：只含可以朗读的 Beat narration 和 closing，不含 URL、机器 ID、证据语法或编辑提示。

两者都从同一份已校验 JSON 派生，禁止反向解析 Markdown 作为机器状态。

## 7. 修订和比较

所有 Script revision 位于同一 `report_id / script_id` 下，必须绑定同一 approved report revision，且 `previous_revision` 指向紧邻上一版。已存在文件拒绝覆盖。比较功能报告新增、删除和修改的 Beat，以及字数、时长、目标时长和 must-keep coverage 变化。

V0.4.1 不再按每版位置重编号。初稿从 `B001` 递增分配；修订会用受控的、可选 `origin_beat_id` 或唯一的结构化 grounding 匹配保留已有 ID。用户不管理最终 ID。新 Beat 从单调递增计数取得新 ID；删除 Beat 进入退休集合，之后永不复用。重复、未知或歧义的 origin 均会失败关闭。任何用户内容修订都会清空旧 Review linkage 并回到 `draft`，必须重新 Review。

## 8. 无搜索边界

Research 和 Fact Check 已负责联网。Script Writer / Reviewer 不启用 Web Search，不从记忆或网络补齐研究空白。OpenAI API 调用不传搜索工具；若 Provider 返回任何 search call 或 citation provenance，工作流立即失败。
