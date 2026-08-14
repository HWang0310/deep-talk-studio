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
7. 若任务涉及制作，完整阅读 `docs/PRODUCTION_CONTRACT.md`、`docs/PRODUCTION_EVALS.md` 和 `.agents/skills/produce-video-assets/SKILL.md`。
8. 用户说“我视频剪好了”、“帮我把素材卡进去”或“给我生成粗剪”时，完整阅读 `.agents/skills/align-video/SKILL.md` 和 `docs/EDIT_BRIDGE_CONTRACT.md`。
9. 与任务直接相关的代码、测试和 Skill。

若文件与当前代码不一致，以可运行代码和测试为事实，同时在本轮修正文档。

## 工作原则

- 主动完成设计、实现、测试、调试、文档和安全的 Git 操作。
- 合理工程决策由 Codex 自行完成；只有会实质改变产品方向或需要新权限时才问用户。
- 面向用户只说结果、影响和下一步，不要求其自己总结技术内容。
- 任何功能或修复先写失败测试，再做最小实现。
- 不削弱校验器来迁就错误的模型输出。
- 保持模块单一职责，通过版本化 JSON 工件连接未来 Agent。
- V0.5.1 与 V0.6.1 已正式验收；第一轮真实 E2E Material + Motion、Preview Hardening 与 canonical lineage 均已通过。Audio Alignment + Visual Edit Bridge + Basic Subtitle V1 当前为 Unreleased Integration Review 阶段；本地 ASR 选择 Gate 已完成，whisper.cpp multilingual medium 是 V1 默认候选，但正式接入仍待 ChatGPT Review，不能依此声称 V1.0。唯一正式路径是 `resolve_real_edit_bridge_session` → `run_real_edit_bridge_session` → repository-owned canonical QA。字幕必须来自 Timed Transcript，segment-only 不得伪装 word precision，Preview 必须烧录并绑定当前 Subtitle Artifact。V1 不依赖 API Key；现有 OpenAI Provider 只保留为后续可选能力。未经真实用户 Clean A-roll E2E 不得声称 V1.0 通过。不要扩展自动 A-roll cleanup、假主播、TTS、BGM、标题封面或发布。
- 用户说“今天讲什么”“找几个选题”“换一批”或带分类偏好时，先阅读 `.agents/skills/discover-topics/SKILL.md` 和 `docs/TOPIC_DISCOVERY_CONTRACT.md`，不要把它塞进 `research-topic`。
- 用户回复候选编号时，读取 latest Candidate Set 的结构化 Research Handoff，直接进入 `research-topic`；不要要求用户再复制标题，也不要把 Discovery Source Seeds 当成事实证据。
- Topic Candidate Set 0.3 的总分、资格状态、资格理由、推荐标签、展示顺序、首选、统计数、身份、时间和来源 provenance 由程序计算并在读取时重新推导；模型或 Skill 只能给评分理由和轻量预检内容。
- Codex Seed 只有在 `discover-topics` 后台 inspection manifest 中记录了实际打开 URL 后才是 `manual_open`；未记录 URL 必须是 `unmatched`，不能参与两条研究方向计数。
- Discovery Raw Candidate 少于 7 个时必须失败或继续搜索，不能以少量结果假装完成；Top 5 可以少于 5 个。
- Top 5 不展示 `watch` 或 `rejected`；高风险且资料薄弱的事件应降为 `watch`，而不是为凑热点上榜。
- Research Draft 与 Fact Check 必须是不同步骤；Fact Check 必须有新的搜索 provenance。
- 未通过质量 Gate 的报告只能保持 `draft`，不能手工改状态绕过。
- `unknown`、`related`、`duplicate`、`syndicated` 来源不能计作独立确认；不得为过 Gate 自动改成 `independent`。
- API 模型只生成研究判断，身份、revision、状态、provenance、quality 和审批字段由代码确定。
- Fact Check 新来源必须与 Draft 来源一起重新规范化和归组后才能保存或应用。
- 即使质量 Gate 通过，Script Agent 前也必须保留用户明确确认；确认必须通过 Approval Workflow 建立新的 Research Revision，不能只改内存状态。
- 用户要求“根据报告写稿”“做成 8 分钟”“做长一点”或修改稿件时，先阅读 `.agents/skills/write-script/SKILL.md` 和 `docs/SCRIPT_CONTRACT.md`。
- Writer 只能读取绑定的 `ready_for_script` Research Revision；草稿、未通过 Gate、未完成 Fact Check 或没有确认文本的报告一律拒绝。
- Script Writer 与 Script Reviewer 必须独立执行，二者均不得自行 Web Search，也不得用网络内容补齐 Research gap。
- Fact Beat 只能引用已核查的 `confirmed_fact`；party statement / commentary 必须使用 Attribution Beat；Analysis Beat 必须保存 basis Claim。
- `avoid_claims` 是禁止结论，不是写作建议；直接使用必须失败，语义近似越界必须由 Reviewer 检查。
- Script Draft 的身份、revision、状态、Beat ID、时长、字数和 must-keep coverage 由程序生成和重新校验，Writer / Reviewer 不能自报。
- Script Review 必须完成 15 个必检维度；每个失败 check 必须有类型匹配的 issue，八项事实安全 check 还必须有 blocking issue。缺失关联时拒绝 Artifact，绝不猜测为通过。
- `reviewed` Script 必须能在读取时找到匹配的通过 Review Artifact，并复验 review ID、来源 revision、内容指纹和 Gate；V0.4.0 旧 reviewed JSON 缺少 linkage 时必须重新审查。
- Script 修订只接受程序校验过的 continuity hint；保留 Beat 的 ID 不变，新 ID 单调递增，退休 ID 永不复用。
- Editor Markdown 用于追踪 Claim / Evidence / 风险；Teleprompter 只保留可朗读正文，不得包含机器 ID、URL 或编辑标签。
- 所有 Script revision 必须不可覆盖并绑定同一份已批准 Research revision；新研究内容会重置旧 Approval，旧稿不能偷换新底稿。
- 用户说“给这期配素材”“把画面准备一下”或要求素材多一点/少一点时，先完整阅读 `.agents/skills/prepare-materials/SKILL.md`、`docs/MATERIAL_CONTRACT.md` 和 `docs/VISUAL_SPEC.md`。
- Material Workflow 只接受能复验 V0.4.1 Review Artifact、内容指纹和 exact Research revision 的 `reviewed` Script；任何 draft、伪造 linkage 或错版 Research 在搜索前拒绝。
- Material Search 可以联网找候选，但不是新 Research。冲突、更新或新事实必须写 `research_update_required`，不得静默改稿、改报告或把新数字写进 Visual。
- 搜索摘要只能是 discovered。只有实际打开并进入 inspection manifest 的 URL 是 inspected；模型不能自报 provenance。
- Evidence 素材必须绑定有效 Claim/Evidence；context 与 illustration 必须明确，illustration 永远不能冒充证据。
- Rights/Reuse 状态只能来自实际打开的素材页与 `rights_evidence_url` 权利页；rights manifest 的 tool reference 必须与权利页 inspection 完全相同。普通新闻、creator 内容和 unknown 只能 reference-only；不得从发布者名称推断许可。
- 自动获取只处理 ready-to-use 的安全静态文件；拒绝登录/付费墙/DRM/反爬绕过、本机内网 URL、危险 MIME、脚本 SVG、超限文件、路径越界和覆盖。
- 网页/PDF capture 必须记录从 1 开始的页码、区域、上下文、caption、能证明和不能证明的内容，并验证真实 PNG/JPEG/WebP 格式；视频无明确权利时只保存 reference，不下载。
- Visual Spec 只能使用 approved Research timeline/Claim/Evidence；所有内部 event/data point/comparison/node 也必须逐项验证。数值采用边界匹配，value label 不能显示不同数值；生成 SVG 不得伪造新闻、文件、聊天、UI、人物或事件现场。
- Material Reviewer 与 Search 分离，只审已有 Package，不扩大 Research。failed check 必须有 typed issue；issue severity、item eligibility、package Gate 和最终状态由代码拥有。
- Material r1 同时保存 input、inspection、rights provenance artifact；reviewed r2 在读取时必须由精确 r1 和 Review Artifact 重建，任何手改 eligibility、rights/provenance、ranking、package status 或 review linkage 均失败关闭。Material Package、Review 和 Assets 不可覆盖，默认位于 gitignored `material_packages/` 与 `material_assets/`。Markdown 只给普通用户阅读，不能当机器接口。
- 用户说“生成视频素材”“做动画”或“出粗剪预览”时，使用 `produce-video-assets` Skill。先通过 V0.5.1 canonical loader，再创建 Production Plan。
- 普通 Production run 只创建 `selected_renderer` 对应的一个适配器。双引擎只用于明确评测，且必须使用同一 tiny Production Plan。
- 素材 stage 前重验 root/path/MIME/size/SHA/eligibility/render status。reference-only、permission-required、rejected、missing 或 tampered asset 不得进入 renderer。
- 除版本化 `machine_editorial` 白名单外，屏幕事实文字即使没有数字也必须语义回查绑定 Claim/Evidence 或精确 approved Research Timeline；合法但无关的 Claim ID 不算通过。
- raw PDF 永远不能作为 CanvasImage/img；Production 只消费 V0.5 已登记、已审且带 capture metadata 的 PNG/JPEG/WebP。无 capture 必须生成固定 gap。
- 四类 Visual 必须由 Python Core 生成结构化 `scene_payload`，renderer 逐元素动画；V0.5 SVG 只能作静态 fallback/debug，不得作为四类 Motion 主体。
- Remotion 必须 frame-driven，使用 `useCurrentFrame` / `interpolate` / `staticFile`，不用 CSS animation/transition。HyperFrames 必须先 DESIGN.md、再 HTML，使用 paused 同步 GSAP timeline，按 lint → validate/inspect → preview → render 执行。
- Renderer 命令成功不等于 asset ready。所有命令以 typed check 进入 Core；任一关键 fail 必须产生 blocking issue。只有输出通过 ffprobe、size、SHA、duration、dimensions、fps 和 binding QA 才可用。
- Production Plan、Manifest、QA、输出和 renderer project 不可覆盖，分别位于 gitignored `production_packages/`、`production_assets/`、`production_projects/`。

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
./scripts/deeptalk prepare-discovery <discovery-input.json> --output discoveries
./scripts/deeptalk select-topic "1" --output discoveries
./scripts/deeptalk approve-report <reviewed-report.json> --confirmation "确认进入写稿"
./scripts/deeptalk prepare-script <approved-report.json> <script-content.json> --duration "8 分钟"
./scripts/deeptalk review-script <approved-report.json> <script-r1.json> <review.json>
./scripts/deeptalk compare-script <script-r1.json> <script-r2.json>
./scripts/deeptalk prepare-materials <report.json> <reviewed-script.json> <content.json> --inspection-manifest <inspection.json> --rights-manifest <rights.json>
./scripts/deeptalk review-materials <report.json> <reviewed-script.json> <package.json> <review.json>
./scripts/deeptalk produce-assets <report.json> <reviewed-script.json> <reviewed-package.json> --renderer auto
./scripts/deeptalk align-video --session <current-session-directory>
PYTHONPATH=src:. python3 evaluations/audio-alignment-edit-bridge/run_full_eval.py --verify-repeat
npm --prefix renderer_templates/aligned_preview_remotion run lint
npm --prefix renderer_templates/aligned_preview_remotion run typecheck
```

修改 `.agents/skills/research-topic`、`.agents/skills/discover-topics`、`.agents/skills/write-script`、`.agents/skills/prepare-materials`、`.agents/skills/produce-video-assets` 或 `.agents/skills/align-video` 后，还要运行 Skill Creator 的 `quick_validate.py`。若本机脚本缺少 PyYAML，可在临时目录安装依赖运行，不能把临时依赖提交到仓库。

## 每轮结束前必须完成

1. 运行与风险相称的全部测试和端到端检查。
2. 更新 `CHANGELOG.md`，只记录实际完成内容。
3. 完整更新 `HANDOFF.md`，包括能力、限制、已知问题、决定和产品问题。
4. 保证 `HANDOFF.md` 最后有 `## 给用户的下一步操作`，写出用户可原样复制给 ChatGPT 的具体文字。
5. 检查 README、PRD、ROADMAP、架构和实际行为一致。
6. 检查 Git diff，避免提交报告草稿、密钥、缓存或无关文件。
7. 如果本轮形成新的正式版本号，严格执行 `RELEASE_POLICY.md`，创建并核验 GitHub Release；不要发布空软件包。

不允许只在聊天中汇报而不更新 HANDOFF。
