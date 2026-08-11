# DeepTalk Studio 交接

当前版本：V0.5.1 / `0.5.1`
本轮状态：工程实现、评测与本地验收完成，等待 ChatGPT 正式 Review
GitHub 仓库：https://github.com/HWang0310/deep-talk-studio
正式发布：将在本轮最终验证后创建 `v0.5.1`

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.5.0 的条件通过意见，完成不扩范围的 **V0.5.1 Material Gate Hardening**：强化 Rights actual-open provenance、Visual Spec 内部 grounding、reviewed Material Package 的可重新证明能力，以及 SVG / capture 安全边界。

## 2. 本轮完成了什么

- `ready_to_use` 现在必须同时有素材页与权利依据页的实际打开记录；`rights_evidence_url`、权利工具记录和检查记录必须一一对应。
- timeline、bar、comparison、diagram 的内部 event、数据点、比较项、节点均逐条验证已批准 Research Claim/Evidence；数值与屏幕标签不能不一致。
- r1 保存独立的 Material Input、Inspection、Rights provenance artifacts。读取 reviewed r2 时会重新建立 r1、验证精确 Review Artifact，并重新推导 r2。
- 手改 `reference_only`/`rejected` 为 `ready_to_use`，或改 rights、provenance、ranking、package status、review linkage，即使重算 package digest，正式 loader 仍失败关闭。
- SVG 允许正常 namespace；脚本、事件处理器、foreignObject、外部资源和危险 CSS URL 被拒绝。截图要求 1-based 页码与真实 PNG/JPEG/WebP 文件。

## 3. 创建或修改了哪些重要文件

- 核心：`material_schema.py`、`material_validation.py`、`material_review.py`、`material_storage.py`、`material_acquisition.py`。
- 测试：Material validation、review、storage/workflow、acquisition、visual renderer fixtures 与回归测试。
- 文档：README、PRD、ROADMAP、AGENTS、CHANGELOG、架构、素材契约、Visual Spec、评测、Skill、V0.5.1 release note、设计与实施计划。
- 公开评测摘要：`evaluations/v0.5.1-summary.json`。真实素材、package 和本地资产继续被 Git 忽略。

## 4. 当前架构是什么

```text
reviewed Script + exact Research
→ Material r1
  + immutable input / inspection / rights provenance artifacts
→ independent Material Review Artifact
→ deterministic Material r2
→ loader replays r1 → Review → r2 before trusting it
```

## 5. 已经可以运行什么

- 现有“给这期配素材”流程、实际打开检查、保守权利判断、安全静态获取、截图登记、原创 SVG 和独立 Material Review。
- 保存并再次读取 reviewed Material Package 时，自动执行 canonical revalidation。
- Python CLI 的 `prepare-materials`、`review-materials`、`materials` 和既有 Research / Discovery / Script 回归入口。

## 6. 还不能运行什么

仍未实现 Remotion、HyperFrames、完整 Composition、剪辑方案、字幕、BGM/SFX、标题、封面或平台发布。

## 7. 已知问题

- 权利检查记录公开页面在检查时所显示的依据，不能替代律师意见或许可后续变化监控。
- PDF 页是否真实存在由实际 capture 工具验证；本地登记层强制页码从 1 开始，但不实现 PDF 阅读器或 OCR。
- r2 的可信性依赖不可覆盖 r1/provenance/Review 存储链；本版不是带外部签名或远端公证的取证系统。

## 8. 重要技术决策

- 选择了更保守、可机器判断的权利关系：明确复用、CC 和官方媒体素材的素材页、rights evidence 页和 license 页均必须有实际打开记录；权利工具记录必须对应 rights evidence 页。
- 不做复杂语义理解：timeline label 直接使用 Research timeline event；bar 数字使用边界匹配；图表子项和顶层引用使用确定性集合关系。
- 不把普通 SHA-256 当作信任来源：它只用于一致性检查，正式可信状态来自 r1 provenance + Review 的重新推导。

## 9. 需要产品经理决定的问题

没有阻塞 V0.5 正式验收的技术问题。请确认：这一层的权利保守度、图表内部 grounding、r1→Review→r2 复验链和 SVG/capture 边界是否满足进入制作层前的安全要求。

## 10. 建议下一阶段做什么

若 ChatGPT 正式验收 V0.5，下一轮再进入一个受限的 Remotion / HyperFrames 制作层：只读取已验证的 `reviewed` / `reviewed_with_warnings` Material Package，先做单条可预览样片与素材缺口提示，不做自动发布。

## 11. 验证与评测

- 完整 unittest：**219 项通过**（原 205 项均保留）。
- 受控真实评测：Stable Business、Contested Public、Rights / Sparse 复跑；没有使用用户 API Key。
- Synthetic hardening：权利页未 actual-open 不可 ready、comparison C404/E404 在 render 前拒绝、手改 reviewed r2 在 loader 失败关闭。

## 给用户的下一步操作

下一步：把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.5.1 Material Gate Hardening。
>
> GitHub 仓库是
> https://github.com/HWang0310/deep-talk-studio ，
>
> Release 是
> https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.5.1 。
>
> 请 Review Rights actual-open provenance、
> Visual Spec nested grounding、
> reviewed Material Package canonical revalidation、
> Material Review linkage、
> SVG/capture hardening、测试和真实评测。
>
> 如果通过，请正式验收 V0.5，
> 并直接给我 Remotion / HyperFrames 制作层的下一轮开发任务。
>
> 不要让我自己总结。
