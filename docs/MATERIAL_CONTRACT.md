# Material Search & Visual Assistance 0.5 契约（V0.5.1 加固）

本文定义 reviewed Script 到可复核素材准备单的正式边界。JSON 是机器接口，Markdown 是普通用户阅读版；任何 Agent 都不能从 Markdown 反向推断机器状态。

## 1. 输入 Gate

Material Workflow 只接受：

- `status=reviewed` 的 Script Draft 0.4；
- Script 的 V0.4.1 `review_state` 指向的真实通过 Review Artifact；
- 内容 SHA-256 与 Review 看到的稿件一致；
- 精确匹配 Script `report_id + report_revision` 的 Research Report；
- Material Profile 0.5。

入口会调用 V0.4.1 正式 validator。draft、手改状态、缺失或伪造 Review、错误内容指纹、错误 Research revision 均在搜索和文件写入前失败关闭。

## 2. Material Package 0.5

正式 Artifact 包括身份、revision、时间、模式、状态、Script ID/revision/digest/Review ID、Research ID/revision、Profile 版本、Cue Sheet、Materials、Generated Visuals、Gaps、Research Update、Warnings、Provider provenance、Review linkage、Package digest 和 machine-owned provenance bundle。

状态只由程序推导：

- `draft`：素材搜索和画面生成完成，等待独立 Review；
- `reviewed`：安全可用且无问题；
- `reviewed_with_warnings`：危险项已隔离，仍有安全替代；
- `research_update_required`：新资料可能改变现有 Research 或 Script；
- `blocked`：包级问题或没有安全可用项。

保存路径包含日期、Research、Script、Package ID 和 `rNNNN`。已存在文件拒绝覆盖。运行时 `material_packages/`、`material_assets/` 默认不进入 Git。

## 3. Visual Cue Sheet

Cue 使用短的、精确存在于对应 Beat 口播中的 `placement_anchor`，不伪造音频时间码。每项包含 Cue ID、Beat、画面作用、建议秒数、首选素材类型、优先级和理由。一个 Beat 可以没有 Cue；重复锚点、错误 Beat、超过 40 字或不在原稿中的 anchor 被拒绝。

作用固定分为 `evidence`、`context`、`illustration`、`transition`。插图必须 `illustrative_only=true`，不能充当证据。

## 4. 素材类型、来源与绑定

支持公开文件/网页、文件或网页截图、照片、视频片段引用、产品 UI、图表源、公开数据集、地图源、档案、原创图表/时间线/关系图/地图和插图参考。

Evidence 素材必须绑定当前 Research 的 Claim 与 Evidence Link，且 Link 必须真实关联这些 Claim。Context 可以保留 Claim 回链。Illustration 不能伪造 Evidence Link。

来源记录包括原始 URL、页面 URL、发布者/创作者、类型、发布时间、检查时间、检查方法和真实工具引用。搜索结果只产生 `discovered`，不能升级为 `inspected`；只有独立 inspection manifest 中实际打开的 URL 才是 `inspected`。

URL 会规范化并去除常见追踪参数；同一规范 URL 不能作为多个候选刷屏。相同 Cue 不推荐近似镜像或重复画面。

## 5. Rights / Reuse Gate

权利状态：

- `public_domain`
- `explicit_reuse_allowed`
- `creative_commons`
- `official_press_asset`
- `editorial_reference_only`
- `permission_required`
- `unknown`
- `avoid`

Rights manifest 必须保存素材 URL、`rights_evidence_url`、依据、许可证 URL、检查时间和工具引用。可直接使用的 public domain、明确复用、CC、official press asset 必须同时满足：素材页实际打开、权利页实际打开、rights evidence URL 存在、rights manifest 的 tool reference 与权利页 inspection 完全一致。明确复用、CC、press asset 的 license URL 必须是公开 HTTP(S) URL，且 license 页也必须有实际打开记录；这样允许“发布页声明 CC、链接跳到 CC 正式许可证”的正常结构。不能从“官方网站”“新闻媒体”“公开视频”“Press”或模型文本推断许可。

最终资格由程序决定：完整 actual-open proof 且权利属于前四种的静态素材才可 `ready_to_use`；普通新闻、API discovered、错配、伪造或未知权利为 `reference_only`；需许可为 `permission_required`；应避免素材为 `rejected`。模型 `claimed_rights_status` 从不拥有最终资格。

## 6. 安全获取、截图和视频

下载器仅允许公开 HTTP(S)，拒绝本机/内网、带账号 URL、非公开重定向、异常 HTTP、空文件、超过 25 MiB、危险 MIME 和目标覆盖。允许静态 JPEG/PNG/WebP/SVG、PDF、纯文本；SVG 中的脚本、事件处理器、外部资源和 `foreignObject` 被拒绝。网页 HTML、JavaScript、宏和可执行文件不保存或执行。

网页/PDF 截图通过本地静态 capture 登记进入包，必须保留原页面、从 1 开始的页码、截取区域、上下文、caption、能证明什么和不能证明什么。注册前检查真实 PNG/JPEG/WebP magic 与扩展名一致；PDF 页是否存在由真实 capture 工具负责验证。PDF 优先截相关页，不把整份文件当“已经证明”。

视频默认只记录页面、发布者、标题、建议起止秒和使用理由。没有明确复用权利时不自动下载；不绕过登录、付费墙、DRM、反爬或平台限制。

每个本地文件记录绝对路径、类型、字节数和 SHA-256；路径越界和覆盖均失败关闭。工作区迁移不改写 reviewed Material Package 或 Material Capture Manifest 中的绝对路径和 digest。运行时只可依据 Package/Material/Visual 身份推导 `material_assets/<package_id>/...` 相对路径，从显式可信历史仓库根映射到 machine-local canonical root，并重新验证 symlink/containment、存在性、类型、byte size 与 SHA-256；映射后的路径仅存在于临时 Material Production View，且与原 `recorded_local_path` 分开。

## 7. 透明排序

候选使用五项 1–5 分：相关性 30%、grounding 25%、画面清晰度 15%、复用安全 20%、获取成本的反向分 10%。总分由程序计算。准确性、核查和权利资格先于美观；高分不能绕过 Rights / provenance Gate。

## 8. Research Update Required

Material Search 可以联网寻找候选，但不能成为新的 Research。若新页面带来冲突、更新或可能改变稿件/图表的信息，只记录受影响 Beat、Claim、原因和新 URL，并将包标为 `research_update_required`。系统不静默改 Research、不改 Script、不把新数字写进 Visual。

## 9. Visual Spec 0.5 与静态 SVG

Visual Spec 支持 `timeline`、`bar`、`comparison`、`diagram`，包含标题、事件/数据/节点、Claim/Evidence、attribution、16:9、安全区、建议秒数、动画意图、样式 token、屏幕文字和 `static/remotion_candidate/hyperframes_candidate` hints。

- Timeline 的 date、Claim 组合、Evidence 组合和保守 label 必须精确存在于批准的 Research timeline。
- 数值图的每个数值以数字边界出现在绑定 Claim 文本中；`value_label` 必须显示同一个数值。
- comparison 的每个内部项、diagram 的每个 node，以及所有 Claim/Evidence/Beat/Node 引用必须存在并对应；顶层 refs 必须与子项 refs 的确定性并集一致。
- 生成画面只作 context/illustration，不能冒充原始证据。

标准库 renderer 实际输出 1920×1080、高对比、XML 转义、带 attribution metadata 的 SVG。V0.5 不承诺 PNG，不创建完整 Remotion/HyperFrames Composition；未来制作层可读取尺寸、时长、props 和 target hints。

## 10. 独立 Material Review

Reviewer 只检查已有 Package，可重新打开列出的 URL，但不能扩大研究或增加候选。10 项必检：provenance、Claim 对齐、Rights、裁切、时效、身份、生成图数据、AI/真实混淆、重复、编辑用途。任一失败 check 必须有 matching typed issue。

阻断类型至少包括：`missing_provenance`、`claim_mismatch`、`fabricated_source`、`rights_misrepresented`、`misleading_crop`、`outdated_factual_visual`、`wrong_identity`、`generated_visual_unsupported_data`、`ai_visual_as_real_evidence`。

Issue ID、严重度、阻断数量、item eligibility、package Gate 和最终状态都由代码推导并在读取时重验。r1 保存不可覆盖的 Material Input、Inspection、Rights artifacts；r2 读取时重新生成精确 r1，验证 Review Artifact 确实审过该 r1，再由 r1 + Review 确定性导出 r2。危险 item 可以隔离；若有安全替代，包为 `reviewed_with_warnings`，包级伪造或无安全方案则 `blocked`。手改 r2 的 eligibility、rights、provenance、ranking、status 或 review linkage 即使重算普通 digest 也会失败关闭。

## 11. 明确不做

V0.5 不实现完整视频、镜头级剪辑时间线、字幕、BGM/SFX、标题封面、上传发布或数据分析；不伪造新闻画面、文件、聊天、产品 UI、数字页面、真人或事件现场；不复制或模仿任何创作者的稿件与独特视觉表达。
