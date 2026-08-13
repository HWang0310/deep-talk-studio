# DeepTalk Studio 产品需求文档

## 1. 产品愿景

建立一套适合长期运营 B 站个人 IP 的 AI 内容生产系统，服务真人露脸、信息密度高、有故事性和观点碰撞的深度口播。系统学习优秀内容的研究方法与组织方法，不复制、洗稿或模仿任何创作者的具体稿件和独特表达。

长期工作流：

```text
选题 → 研究 → 多来源观点 → 事实核查 → 分析框架 → 原创口播稿
     → 素材建议 → 可视化 → 剪辑方案 → 发布辅助
```

当前 Unreleased 产品设计方向是 Audio Alignment + Visual Edit Bridge：用户先在习惯的工具中完成口气清理，再把 Clean A-roll 作为不可变化的真人主时间轴。系统将 reviewed Script、Material Cue、真实图片/截图/视频和原创 Motion 对齐到真实口播时间，自动生成基本 rough cut；本轮只有 Design Review Candidate，尚未实现。自动 A-roll cleanup 不属于当前阶段。

## 2. 用户与协作角色

主要用户不是工程师，只提供主题、做内容判断和最终确认。产品必须把技术步骤隐藏在简单操作背后。

- ChatGPT：产品经理 / 架构师。
- Codex：首席工程师和实际执行者。
- 用户：在二者之间原样传递仓库链接、HANDOFF 和下一轮任务。

## 3. 已完成的 V0.1 基础

V0.1 建立正式项目基础和 Research Workflow。用户输入“某某事件值得怎么讲”，系统产出一份结构化、来源可追溯的研究底稿。

### 3.1 功能要求

1. 搜索并打开公开资料。
2. 记录事件基本事实和时间线。
3. 将信息分类为：
   - 已确认事实；
   - 媒体报道；
   - 当事人或当事机构说法；
   - 评论者、专家或创作者观点；
   - 尚未证实的信息。
4. 搜集不同类型来源和不同立场。
5. 发现观点与叙事之间的冲突。
6. 提炼仍值得核查和讨论的问题。
7. 给出多个原创内容切入角度。
8. 同时输出 Markdown 和 JSON Research Report。
9. 重要事实尽可能保留来源，所有来源使用可点击 URL。
10. 为未来 Script Agent 提供稳定的输入接口。

### 3.2 质量要求

- 不把搜索摘要当作事实证据，重要来源应打开检查。
- 不把“有人说”改写成“事实是”。
- 对争议性、快速变化或证据不足的信息明确降低置信度。
- 重要事实应优先多源交叉核查；来源质量比数量更重要。
- 同时呈现可信的支持、反对和替代解释。
- 不大段复制受版权保护内容，不从别人稿件出发改写。
- 报告保存前必须通过机器校验。

### 3.3 非功能要求

- Python 3.9+，V0.1 核心不依赖第三方包。
- 模块边界清晰，可替换研究提供器。
- 任何密钥不得进入代码、文档、报告或 Git 历史。
- 普通用户的主入口是自然语言，不要求其管理命令行。
- 每轮开发必须更新 CHANGELOG 和 HANDOFF。

## 4. V0.2：Research Quality Gate & Independent Fact Check

V0.2 将研究底稿从“结构完整”升级为“来源、证据和核查过程可机器追踪”。

### 4.1 产品要求

1. 所有入口使用同一套完整 Schema 校验，任何嵌套错误都返回可理解的 `ReportValidationError`。
2. Research Report 采用 0.2 契约，包含稳定报告 ID、修订号、生成时间、研究模式和透明质量指标。
3. 来源与主张通过 Evidence Link 连接，明确 `supports`、`contradicts`、`attributes`、`context`。
4. API 与 Codex Skill 分别记录真实工具 provenance，未匹配来源不能默认为已检查。
5. Research Draft 和 Fact Check 必须是两个独立步骤；Fact Check 需要新的搜索并主动寻找反证。
6. 主张包含重要性、风险等级和风险因素，高风险主张自动进入核查队列。
7. 质量 Gate 至少公开来源覆盖率、高风险核查率、confirmed fact 独立来源覆盖率、来源类型、重复转载、未解决高风险、无来源归属和 provenance 匹配率。
8. 未通过 Gate 的报告可以保存，但只能保持 `draft`；通过 Gate 后也要等待用户确认，不能自动写稿。
9. 报告更新产生新修订版，不能静默覆盖历史；更正必须保留原因和来源。
10. V0.1 报告可确定性迁移为 0.2 草稿，但迁移不能伪造已完成的独立核查。

### 4.2 V0.2 验收标准

- [x] 完整 Schema、枚举、类型、`additionalProperties` 和交叉引用校验。
- [x] Research Report 0.2、Evidence Ledger、风险字段和质量指标。
- [x] OpenAI API provenance 保留和来源匹配降级。
- [x] 独立版本化 FactCheck Artifact 与第二次搜索。
- [x] 来源规范化、去重、同发布者和疑似转载识别。
- [x] 不可覆盖的报告修订与更正历史。
- [x] 一次用户确认 Gate，显式展示高风险主张。
- [x] V0.1 → V0.2 兼容迁移。
- [x] 三类真实题材跑完整工作流并提交去内容化评测汇总。
- [x] 自动测试、Skill 校验、端到端验证和文档同步。

### 4.3 V0.2.1：Quality Gate Hardening

V0.2.1 是 V0.2 的正确性修订，不增加用户功能，也不升级正式 Report Schema。

- [x] confirmed fact 的独立确认只接受 `supports + matched + independent + 不同 group`。
- [x] `unknown`、`related`、`duplicate`、`syndicated` 不贡献独立确认数量。
- [x] API Research 模型不再生成身份、修订、状态、provenance、质量和审批等机器字段。
- [x] Fact Check 新来源与旧来源合并后统一确定性规范化和归组。
- [x] context-only、未匹配 attribution、重复或转载记录不能意外刷高相关质量指标。
- [x] 三类真实题材重新评测，证据不足的快速热点仍保持 `draft`。

## 5. 模式 B：没有选题（V0.3.1 已完成）

用户可以说“今天讲什么？”“帮我找几个选题”或加上科技、商业、社会等偏好。系统默认在最近 72 小时寻找事件，也接纳最近 14 天内发生、但在 72 小时内出现重要新进展的持续事件。输出最多 5 个简短候选卡，其中明确一个首选；用户只需回复编号即可进入 V0.2 Research Workflow，不需要重复标题。

V0.3 使用版本化 Channel Profile 和独立 `Topic Candidate Set 0.3`。每个候选保留 why now、核心张力、研究问题、时效、风险、2–4 个 Source Seeds、评分理由和机器计算的总分。Source Seeds 是研究入口，不是确认事实，也不是 Research Evidence Ledger。

候选先经过 Eligibility Gate：匿名传言、无公开资料、未经证实的严重指控、纯情绪、重复事件、模仿他人表达和极高风险却无资料基础的主题不能进入 Top 5。重大快速事件可作为 `watch` 保留。评分固定为：可核查性 30%、深度与观点冲突 25%、新鲜度 20%、频道匹配 15%、公开关注信号 10%；总分只由代码计算。Creator 公开主题只能作为可选辅助讨论信号，不能成为事实证据或洗稿来源。

### 5.1 V0.3.1：Discovery Gate Hardening

- Codex 只有实际打开、记录在后台 inspection manifest 的 Seed 才可标为 `manual_open`；Raw Candidate JSON 不能自认证。
- Candidate Set 的资格、理由、推荐、总分、展示顺序、首选和 watch/reject 统计必须由程序重新推导；任何不一致工件都拒绝读取。
- 至少两条研究方向只计算来源类型合格且 provenance 已匹配的不同 URL / publisher / host；社交或 creator Seed 不能凑数。
- 事件开始时间不得晚于更新，且时间不得比 discovery 时间晚超过 5 分钟。
- 至少 7 个 Raw Candidate 才可进行候选生成；这不要求最后必须有 5 个合格题。
- 分类多样性先保证每类最多两项，再按分数补齐展示位；同一事件仍永不重复。

模式 A 的用户直接主题入口保持不变。V0.3.1 不实现素材、视觉、剪辑和发布。

## 6. V0.4：Original Script Agent

V0.4 把已经核查并由用户明确批准的 Research Report 转成原创深度口播稿。Script Agent 不重新搜索，不从其他创作者稿件出发，也不能补写研究底稿没有支持的新事实。

### 6.1 进入写稿的硬条件

1. Research Report 已完成独立 Fact Check。
2. 透明 Quality Gate 为 `pass`。
3. 报告状态为 `reviewed`。
4. 用户明确确认进入写稿；系统把原始确认保存为新的、不可覆盖的 Research Revision。
5. 只有该新修订版的状态、审批状态和确认文本同时有效，Writer 才能运行。

任何草稿、未通过 Gate、未完成 Fact Check 或只有 `reviewed` 但没有用户确认的报告，都必须拒绝写稿且不产生文件。

### 6.2 稿件要求

- 默认平台为 B 站，形式为真人露脸深度口播；默认目标约 12 分钟，支持用户自然语言调整为 3–30 分钟。
- Script Draft 0.4 必须绑定准确的 Research Report ID 和 revision。
- 每个 Beat 标明 `fact`、`attribution`、`analysis`、`transition` 或 `question`。
- 事实 Beat 只能使用已核查的 `confirmed_fact`；当事方和评论者说法必须自然归因；分析必须声明它依据哪些 Research Claims。
- 所有重要表达保留 Claim / Evidence Link 回链；机器 ID 只出现在 Editor 版本，不能进入 Teleprompter 口播。
- 程序计算必须保留主张覆盖、字数和估算时长；Writer 不能伪造这些字段。
- `avoid_claims` 直接使用会被硬阻止；语义近似越界由独立 Reviewer 继续检查。
- 输出 Editor Markdown 和只含口播正文的 Teleprompter Markdown；完整真实稿件默认不上传 GitHub。

### 6.3 独立 Script Review

Writer 和 Reviewer 必须是两个独立步骤，二者都不能自行 Web Search。Reviewer 至少逐项检查事实 grounding、归因、不确定性、禁讲项、must-keep、高风险边界、事实与分析分离、观点公平、研究空白、结构、口语、信息密度、原创表达、可用性和反方公平。

阻断问题包括无来源事实、归因错误、使用禁讲结论、把未核实信息写成事实、高风险过度断言、丢失关键不确定性、把分析伪装成事实、擅自填补研究空白和歪曲观点。Gate 由程序从问题类型计算；存在任一阻断问题时，稿件保持 `draft`。

### 6.4 V0.4 验收标准

- [x] Approval 创建新的不可覆盖 Research Revision，普通内容修订会重置 Approval。
- [x] 未批准 Research 无法写稿。
- [x] Script Profile、Script Draft、Script Review 三个 0.4 契约可用。
- [x] Writer / Reviewer 分离，且不启用 Web Search。
- [x] Grounding、归因、分析、禁讲项、must-keep 和高风险边界可校验。
- [x] Editor / Teleprompter 双输出、不可覆盖修订和 revision 比较可用。
- [x] 支持自然语言时长和后续修改反馈。
- [x] 稳定商业、争议公共议题和未批准输入三类真实评测完成。
- [x] 原测试继续通过，新测试、Skill 校验和端到端检查通过。

V0.4 不包含素材搜索、图片或视频生成、剪辑方案和平台发布；这些能力仍属于未开始的 V0.5 及以后版本。

### 6.5 V0.4.1：Script Gate Hardening

V0.4.1 只修正 Script Workflow 的可靠性，不重新设计写稿能力：

- 任一失败的 Review check 必须有明确对应的 issue；八项事实安全检查失败必须有对应 blocking issue。缺失时拒绝 Artifact，不能推测为通过。
- `not_applicable` 不得跳过事实安全检查；仅在没有可审反方时允许用于 counterargument fairness，并保留理由。
- 通过 Review 的新 Script revision 必须保存机器拥有的 Review linkage：Review ID、被审 revision、通过状态和内容指纹；读取时必须找到并重新验证对应 Artifact。
- 用户任何内容修订自动回到 `draft`，旧 Review 不能沿用。
- Beat identity 在修订中保持稳定：已有段落尽量保留 ID，新段落取递增新 ID，删除 ID 永不复用；比较结果按真实连续性报告。

V0.4.0 的旧 `reviewed` JSON 没有上述 linkage 时不得自动信任；需要重新执行 Review。V0.4.1 已正式验收。

## 7. V0.5：Material Search & Visual Assistance

V0.5 从经过 V0.4.1 真实 Review 的 Script 和精确 Research revision 生成 Material Package。它提供逐段画面提示、来源与复用权利记录、安全获取、原创静态图和独立 Material Review，但不生成完整视频。

### 7.1 产品要求

1. draft、伪造 reviewed、缺 Review Artifact 或错误 Research revision 必须在搜索前拒绝。
2. Cue 使用短原句 anchor，区分 evidence/context/illustration/transition；不是每个 Beat 都强制配画面。
3. 搜索摘要不算 inspection；所有重要候选保留实际打开页面的 provenance。
4. Rights 状态和最终 eligibility 由程序保守推导，普通新闻和 unknown 不可 ready-to-use。
5. Evidence 素材绑定 Research Claim/Evidence；插图明确 illustrative-only。
6. 新事实只触发 research update，不静默改 Script/Research/Visual。
7. 仅安全保存明确复用的静态文件，保留路径、类型、大小、SHA-256 和截图语境。
8. 用 approved Research 生成 timeline/bar/comparison/diagram Visual Spec 和实际 1920×1080 SVG。
9. 独立 Reviewer 检查来源、绑定、权利、裁切、时效、身份、生成数据、AI/真实混淆、重复和用途。
10. JSON 为正式接口，Markdown 为普通用户简明阅读版；真实 Package/Assets 默认不上传 GitHub。

### 7.2 V0.5 验收记录

- [x] Material Package / Visual Spec / Material Review 0.5 完整契约。
- [x] V0.4.1 Review linkage 与 exact Research input Gate。
- [x] Provenance、Rights/Reuse、Claim/Evidence、排序、去重和 Research update Gate。
- [x] 安全下载、截图/PDF capture、视频引用边界和不可覆盖资产记录。
- [x] 四类静态 SVG renderer 与未来 Remotion/HyperFrames hints。
- [x] 独立 Material Review、item isolation 和 package-level Gate。
- [x] Skill、Provider、CLI、205 项测试和三类真实评测。

### 7.3 V0.5.1：Material Gate Hardening

- [x] `ready_to_use` 必须同时证明素材页和 `rights_evidence_url` 权利页均被实际打开，且工具记录一致；模型自称、伪造 license URL 或只打开素材页均降级。
- [x] timeline、bar、comparison、diagram 的内部 Claim/Evidence/Research binding 均确定性校验；数值采用边界匹配，显示数值不能与实际值不一致。
- [x] r1 保存不可覆盖的输入、inspection、rights provenance artifacts；读取 reviewed r2 时重建 r1、复验 Review Artifact，再确定性重建 r2。
- [x] 标准 SVG namespace 允许，脚本、事件、foreignObject 和外部资源仍拒绝；截图采用 1-based 页码和真实图片格式检查。
- [x] 全套回归测试、受控加固场景与公开去内容化评测已更新。

V0.5 不包含完整视频、剪辑时间线、字幕、音乐、标题封面、上传发布和运营分析。

## 7.4 V0.6：Motion Production Layer

V0.6 只把已审查的素材包制作成可复核的辅助动画，不代替真人出镜、最终剪辑和发布决策。

1. 入口只接受能由 V0.5.1 loader 重放验证的 `reviewed` / `reviewed_with_warnings` Material Package。
2. Production Plan 0.6.1 绑定精确 Script、Material revision、Review、Profile、Scene、时长、来源和预期输出；结构化 `scene_payload` 由 Python Core 拥有。
3. 普通制作只选 Remotion 或 HyperFrames 中一个；两者共用同一计划、设计 Profile、Manifest 和 QA。
4. 渲染前重验 asset root、本地文件、MIME、byte size、SHA-256、render status 和 eligibility。非 ready 素材永不进入 Composition。
5. 所有事实显示文字无论是否含数字，都必须从绑定 Claim/Evidence 或精确 Research Timeline 重新证明；只有版本化机器短语可不绑定。
6. 映射 timeline、bar、comparison、diagram、official document/webpage、screenshot、static image 和 A-roll placeholder；缺画面时记录 Production gap。
7. 输出 MP4 动画片段、MP4 rough visual preview 与 PNG hero still。Manifest 记录真实文件元数据和 SHA，QA 由程序计算 clip/package Gate。
8. raw PDF 只保留 provenance；只有已审 PNG/JPEG/WebP capture 可进入 renderer。计划、输出和渲染工程不可静默覆盖，且默认被 Git 忽略。
9. renderer 的 environment/install/lint/typecheck/compositions/doctor/validate/inspect/preview 结果均为 typed check；Core 确定性执行 check → issue → gate。

### V0.6 验收记录

- [x] Remotion Studio / compositions / real render 成功。
- [x] HyperFrames DESIGN-first、lint、validate、inspect、preview 和 real render 成功。
- [x] 同一 tiny plan 双引擎各产出 1920×1080、30 fps 真实 MP4，QA 均为 pass。
- [x] Stable Business bar 完整 project → validation → preview → render → QA 成功。
- [x] Contested Public 与 Rights Sparse 保持 reference-only 隔离，使用原创 timeline/diagram 或 A-roll。
- [x] blocked input 与 asset tampering 在 Renderer 前拒绝。
- [x] V0.6.1 四类逐元素 Motion、Display Text 语义 Gate、QA fail-closed 和 PDF/capture boundary 已完成。
- [x] 自动测试共 267 项（266 项执行通过、1 项真实渲染测试默认跳过），真实双引擎测试已显式启用并通过。

V0.6 不做假主播、TTS、最终 A-roll 合成、真实音频时码、字幕、BGM/SFX、标题封面、上传或自动发布。

## 8. V0.1 验收记录

- [x] 已初始化独立正式项目和 Git 历史。
- [x] 有可扩展的 Agent / Workflow 设计。
- [x] 有仓库级 Research Skill。
- [x] 可接收主题并生成结构化报告。
- [x] 报告保留来源并区分事实与观点。
- [x] 报告包含时间线、冲突、问题和切入角度。
- [x] 有 Script Agent 交接接口。
- [x] 有离线示例和自动测试。
- [x] 有 README、PRD、ROADMAP、AGENTS、CHANGELOG、HANDOFF。
- [x] V0.2 已使用三类真实题材完成编辑质量评估。

## 9. 成功信号

V0.4 的成功不是“AI 写得像一个知名博主”，而是：编辑能快速确认每句重要口播从哪里来，事实、归因和分析没有混在一起，真实争议没有被弱化，研究未知没有被擅自填满，同时稿子听起来仍像真人在讲述，而不是一份机器报告。

V0.5 的成功不是“搜到很多图”，而是：编辑能知道画面放在哪里、为什么放、它能证明什么、能否复用；未知版权不会混入 ready-to-use，原创图没有虚构数据，发现新事实会回到 Research，而不是悄悄改稿。

V0.6 的成功不是“渲染命令返回 0”，而是真实文件的尺寸、帧率、时长、大小和 SHA 与计划一致，不合法素材和未支持数字没有混入画面，缺口被说清楚。
