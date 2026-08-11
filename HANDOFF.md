# DeepTalk Studio 交接

当前版本：V0.5.0 / `0.5.0`
本轮状态：工程实现与本地验收完成，等待 ChatGPT 产品与架构 Review
GitHub 仓库：https://github.com/HWang0310/deep-talk-studio
正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.5.0

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.4.1 的正式验收，完成 V0.5 **Material Search & Visual Assistance**：从真实 reviewed Script 和精确 Research revision 出发，生成画面提示、搜索并核查素材、保守判断复用权利、安全获取允许的静态文件、生成 Research-grounded 原创 SVG，并执行独立 Material Review。

本轮没有实现完整 Remotion/HyperFrames 视频、剪辑时间线、字幕、BGM/SFX、标题封面、上传发布或运营分析。

## 2. 我完成了什么

- 建立正式输入 Gate：只有能复验 V0.4.1 Review Artifact、内容 digest 和 exact Research revision 的 `reviewed` Script 可运行。draft、手改状态、伪造 Review、缺失 Artifact 和错误 Research revision 全部失败关闭。
- 建立 Visual Cue Sheet：用短原句 anchor 定位关键 Beat，区分 evidence、context、illustration、transition，不强迫每段都配素材。
- 建立 Material Package 0.5：包括 Script/Research/Profile binding、Cue、Materials、Generated Visuals、Gaps、Research Update、Warnings、Provider provenance、Review state 和 package SHA-256。
- 建立真实 provenance：搜索结果只能标 `discovered`；只有 actual-open inspection manifest 中的 URL 才是 `inspected`。API 搜索调用、queries、source URLs 和 citations 原样保留。
- 建立 Rights/Reuse Gate：public domain、明确复用、CC、official press asset、仅编辑引用、需许可、unknown、avoid 分开；普通新闻和未知版权不会 ready-to-use。
- 建立 Claim/Evidence binding：证据素材必须关联真实 Claim/Evidence；插图必须 illustrative-only，不能冒充事实证据。
- 建立 Research Update escalation：新页面出现冲突、更新或新事实时标记 `research_update_required`，不静默改稿、Research 或图表。
- 建立安全获取：只下载明确 ready 的公开静态文件；拒绝本机/内网、异常状态、危险 MIME、超限文件、脚本 SVG、路径越界和覆盖；记录类型、大小和 SHA-256。
- 建立网页/PDF capture 登记与视频 reference 边界：保留页码、区域、上下文、caption、能证明/不能证明；无明确权利的视频不下载。
- 建立原创 Visual Spec 和实际 SVG：timeline、bar、comparison、diagram 均可输出 1920×1080、高对比、有 attribution metadata 的真实本地 SVG；数值和事件必须来自 approved Research。
- 建立独立 Material Review：检查 provenance、Claim、Rights、裁切、时效、身份、生成数据、AI/真实混淆、重复和用途；危险 item 可隔离，包级问题失败关闭。
- 建立普通用户阅读版：只显示画面提示、可用/参考/需许可数量、原创画面、缺口和提醒，不暴露 JSON 与机器 ID。
- 新增 `prepare-materials` Skill、API Provider boundary 和三个 CLI 命令；用户仍只需说“给这期配素材”。

## 3. 创建 / 修改了哪些重要文件

- 契约与实现：`material_schema.py`、`material_validation.py`、`material_review.py`、`material_acquisition.py`、`visual_renderer.py`、`material_workflow.py`、`material_storage.py`、`material_renderer.py`、`material_prompt.py`。
- 配置与入口：`config/material-profile.json`、`.agents/skills/prepare-materials/`、`providers/base.py`、`providers/openai.py`、`cli.py`。
- 正式文档：`docs/MATERIAL_CONTRACT.md`、`docs/VISUAL_SPEC.md`、`docs/MATERIAL_EVALS.md`、V0.5 设计/计划、Release Notes。
- 评测与测试：`evaluations/v0.5.0-summary.json`，6 个 V0.5 测试/fixture 文件；完整真实工件和本地 assets 在 gitignored 目录。
- 长期协作：README、PRD、ROADMAP、ARCHITECTURE、AGENTS、CHANGELOG、HANDOFF、版本号和 `.gitignore` 均已同步。

## 4. 当前架构是什么

```text
reviewed Script 0.4 + V0.4.1 Review Artifact + exact Research revision
  → Material Input Gate
  → Material Search + actual page inspection + rights inspection
  → Cue Sheet + candidates + Research update signals
  → code-owned provenance / rights / ranking / eligibility
  → safe acquisition + Research-grounded Visual Spec
  → actual SVG assets
  → independent Material Review
  → Material Package r2: reviewed / reviewed_with_warnings / blocked / research_update_required
```

Material Search 可以联网，但不是 Research Agent。完整 JSON 是机器接口；Markdown 只是给普通用户看的派生物。Remotion / HyperFrames 只收到 future render hints，不在 V0.5 运行。

## 5. 已经可以运行什么

- 用户对最新 reviewed 稿件说“给这期配素材”或“把画面准备一下”。
- 用户说“少一点，只配关键段落”或“多一点画面”，Skill 会调整 Cue 密度，不重复堆素材。
- 搜索公开文件、网页、截图、照片、视频 reference、数据/地图/档案入口，并保留真实检查记录。
- 生成简明素材准备单、正式 JSON、独立 Review Artifact 和不可覆盖 revision。
- 安全获取有明确复用依据的静态资源，登记网页/PDF capture。
- 生成实际 timeline/bar/comparison/diagram SVG。
- API 自动化的 `materials`，以及 Codex 模式的 `prepare-materials` / `review-materials`。

## 6. 还不能运行什么

- 不生成完整视频或 Remotion/HyperFrames Composition。
- 不做音频级时间码、镜头级剪辑、字幕、BGM/SFX、标题封面。
- 不自动绕过登录、付费墙、DRM、反爬或平台限制。
- 不自动下载 unknown/ordinary news/creator/video 素材。
- 不替代法律意见、编辑最终裁切检查或发布批准。
- 不上传 B 站、小红书、抖音，也不做发布后分析。

## 7. 已知问题

- API `web_search` 可以保留搜索来源，但没有单独 actual-open manifest 时只标 `discovered`，不会错误升级为 inspected/ready；Codex Skill 的实际打开链路更完整。
- 权利依据可能随网站条款变化；当前工件记录检查时点，但没有持续监控许可证变化。
- SVG 是静态最小实现；建议时长只是编辑意图，没有音频对齐。
- 工程能验证 Visual 忠于 Research Artifact，不能重新证明现实世界事实，也不能替代人类对裁切语境的最终判断。
- V0.5 只渲染 SVG；PNG 是可选未来能力，不影响本版验收。

## 8. 重要技术决策

- 沿用 V0.4.1 Review linkage，不新造一个较弱的素材入口状态。
- inspection 和 rights 使用两个独立 manifest；候选模型不能自认证页面已打开或拥有许可。
- 排序是透明加权，但 provenance、grounding 和 rights Gate 优先于总分与美观。
- unknown 默认 reference-only；明确复用/CC/press asset 必须保留 license URL。
- Search 新事实不写入 Package 图表，统一升级为 Research update。
- 生成 Visual 永远是 context/illustration，不是原始 evidence；SVG metadata 保留 Research 回链。
- 危险 item 与 package-level failure 分开：有安全替代时允许 reviewed_with_warnings，没有替代才阻断整个包。
- 只实现标准库静态 SVG，不在 V0.5 引入 Node/Remotion/HyperFrames 依赖或过度工程化。
- `material_packages/` 与 `material_assets/` 默认 gitignored；公开仓库不上传真实素材。

## 9. 测试与真实评测

- 完整 `unittest` suite：**205 项通过**；原 165 项全部继续通过。
- 新增 40 项覆盖：input Gate、伪造 Review、错版 Research、Cue anchor、provenance、rights、Claim/Evidence、illustration、去重、research update、下载、私网、MIME、大小、覆盖、capture、四类 SVG、虚构数字、Review consistency、item isolation、storage、Provider、CLI、Skill。
- Stable Business：真实 Apple 财报页 actual-open；因页面 `all rights reserved` 保守为 reference-only；approved 数字生成实际 bar SVG。
- Contested Public：真实欧委会页面和 CC BY 4.0 reuse notice actual-open，EU 页面 ready-to-use；普通新闻页无许可，保持 reference-only；生成实际 timeline SVG。
- Rights / Sparse：真实 AP 页面 actual-open，但不从媒体名称推断版权、不下载；优先使用 actual diagram SVG。
- 隔离 acquisition 场景实际保存明确复用的 PDF，记录 MIME/size/SHA-256，并验证不覆盖。
- Skill 已按 Skill Creator 规范生成 UI metadata；最终 quick validation 在发布前执行。

## 10. 哪些问题需要产品经理决定

当前没有阻塞 V0.5 发布的技术问题。请 ChatGPT 完整 Review：

1. Material Package、Cue 和 Visual Spec 字段是否足够进入制作层；
2. actual-open provenance 与 API discovered 降级是否符合风险口径；
3. Rights 状态和 ready/reference/permission/rejected 的保守规则是否接受；
4. Research update escalation 是否应作为下一阶段制作前硬 Gate；
5. 独立 Material Review 的 blocking issue 和 item isolation 是否符合编辑流程；
6. 若通过，下一阶段是否进入 Remotion / HyperFrames 与制作层集成。

## 11. 建议下一阶段做什么

若 ChatGPT 正式验收 V0.5，建议先做一个很窄的制作层：读取 `reviewed` / `reviewed_with_warnings` Material Package，把静态 SVG、已批准本地 assets 和 Cue duration 映射为可预览的 Remotion 或 HyperFrames Composition。先完成单条视频的可预览样片和素材缺口提示，不立即做全自动剪辑、上传和发布。

## 12. 版本发布规则

本轮正式版本为 `v0.5.0`。继续使用公有仓库 `HWang0310/deep-talk-studio`，不创建新仓库、不 force push、不重写 `main` 历史。GitHub Release 自动提供 ZIP / TAR 源码包；不发布没有安装价值的空 GitHub Package。

## 给用户的下一步操作

下一步：把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.5 Material Search & Visual Assistance。
> GitHub 仓库是 https://github.com/HWang0310/deep-talk-studio ，
> Release 是 https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.5.0 。
>
> 请完整 Review Material Package、Visual Cue Sheet、联网 provenance、
> Rights/Reuse Gate、Claim/Evidence binding、实际素材获取、
> PDF/截图流程、原创 Visual Spec 和 SVG 生成、Material Review、
> 测试与三类真实评测。
>
> 如果通过，请正式验收 V0.5，并根据当前完成度决定下一阶段
> 是否进入 Remotion / HyperFrames 与制作层集成。
> 不要让我自己总结。
