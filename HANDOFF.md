# DeepTalk Studio 交接

当前版本：V0.6.0 / `0.6.0`

本轮状态：工程实现、真实渲染、测试与本地验收完成，等待 ChatGPT 正式 Review

GitHub 仓库：https://github.com/HWang0310/deep-talk-studio

正式发布：https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.6.0

## 1. 本轮任务是什么

根据 ChatGPT 对 V0.5.1 的正式 Review，完成 **V0.6 Motion Production Layer**：以通过 V0.5.1 canonical Gate 的 reviewed Material Package 为唯一输入，生成统一 Production Plan，并通过 Remotion 或 HyperFrames 生成真实运动素材、粗预览、产物清单与制作 QA。

## 2. 本轮完成了什么

- 建立统一 `ProductionProfile`、`ProductionPlan`、`MotionAssetManifest` 与 `ProductionQAReport` 契约。
- 新增 Remotion Adapter 与 HyperFrames Adapter；二者读取同一份 Plan/Profile，正常工作流一次只启用一个 renderer。
- 支持 bar、timeline、comparison、diagram 四类数据/解释型 motion，以及已审文档截图、图片、静态素材的安全使用。
- 真实生成 MP4 与 PNG still，并生成 rough visual preview、renderer project、manifest 和 QA 报告。
- 每个本地 asset 在进入 Plan 和 renderer 前检查规范路径、存在性、MIME、字节数、SHA-256、权利状态与生产资格。
- `reference_only`、`permission_required`、`rejected`、缺失或被篡改的素材不会进入 renderer，而是保留为 A-roll / material gap。
- 新增 Display Text Grounding：画面上的事实性数字与日期必须重新绑定 approved Research Claim/Evidence/Timeline，不能靠脚本或素材包里的自由文本绕过。
- 新增可复用 Skill：`.agents/skills/produce-video-assets`，并加入 `produce-assets` CLI。

## 3. 创建 / 修改了哪些重要文件

- 制作契约与验证：`production_schema.py`、`production_profile.py`、`production_validation.py`、`config/production-profile.json`。
- 计划与存储：`production_planner.py`、`production_storage.py`。
- 渲染：`production_renderer.py`、`production_renderers/base.py`、`production_renderers/remotion.py`、`production_renderers/hyperframes.py`，以及两套 renderer templates 与锁定依赖。
- 编排与 QA：`production_workflow.py`、`production_qa.py`。
- Skill / CLI：`.agents/skills/produce-video-assets/`、`cli.py`、`pyproject.toml`。
- 测试：Production contracts、Gate、planner、两个 adapters、QA、workflow、CLI、Skill 和真实渲染 integration tests。
- 文档：README、PRD、ROADMAP、AGENTS、CHANGELOG、架构、Production Contract、两个 Adapter 文档、Evals、Release Note、设计与实施计划。
- 公开评测摘要：`evaluations/v0.6.0-summary.json`。真实 package、renderer projects 和输出按要求保留在本地忽略目录，不进入 Git。

## 4. 当前架构是什么

```text
reviewed Script + exact Research + V0.5.1 reviewed Material Package
                         │
                         ▼
           canonical Material Input Gate
     provenance replay + asset path/MIME/SHA/rights checks
                         │
                         ▼
              deterministic Production Plan
        scenes + display text grounding + asset bindings
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
      Remotion Adapter      HyperFrames Adapter
       （正常只选一个）       （正常只选一个）
              └──────────┬──────────┘
                         ▼
        MP4 / PNG + rough preview + renderer project
                         │
                         ▼
           Motion Asset Manifest + Production QA
```

Renderer 没有被拆成两套业务系统：Production Plan、Profile、输入 Gate、Manifest 和 QA 全部共享；Adapter 只负责把同一语义计划翻译为各自的真实渲染工程。这样可以替换 renderer，又不会让安全规则和制作逻辑分叉。

## 5. 已经可以运行什么

- 对一个 V0.5.1 reviewed Material Package 运行 `produce-assets`，选择 `remotion` 或 `hyperframes`。
- 自动生成 Production Plan，并安全选择可制作的 motion/static scenes。
- 真实执行 renderer validation、preview、MP4 render 与 PNG still render。
- 输出 Motion Asset Manifest、rough preview 和 Production QA；只有 QA Gate 通过的包才标记为可交给后续剪辑。
- 对无法安全使用的素材记录清楚的 material gap，不会用占位文件伪装成已取得素材。

## 6. 还不能运行什么

- 不生成假主播，不生成真人替身或 TTS。
- 不做完整节目合成、最终剪辑、自动字幕、BGM/SFX、调色、标题、封面或平台上传发布。
- rough preview 只是核对信息结构与 motion 节奏的制作预览，不是可直接发布的成片。
- 不能绕过素材权利或 V0.5.1 review Gate；`reference_only` 仍只能作为检索/剪辑提示。

## 7. 已知问题

- 首次真实渲染仍需要本机已安装 Node.js、Chrome/Chromium，并需要安装锁定的 renderer 依赖；依赖安装和渲染速度受网络与机器性能影响。
- 两个 renderer 的像素和编码时长不会完全一致；V0.6 保证的是相同 Plan、source binding、分辨率/fps 与 QA 语义，不承诺逐像素一致。
- 静态网页/PDF 素材仍依赖 V0.5.1 已保存且通过检查的本地文件；本层不偷偷下载 reference-only 页面。
- Display Text Grounding 当前采用确定性规则，优先保证不把未经研究支持的数字/日期放上屏；复杂自然语言图形可能需要人工改写或补 Research。

## 8. 重要技术决策

- **一个统一 Plan，而不是两个工作流。** Remotion 与 HyperFrames 都只是薄 Adapter，避免 Gate、QA 和 source binding 各自演化。
- **非 ready 素材永不渲染。** 即使文件存在，只要状态、路径、MIME、SHA 或 provenance 不成立，就在创建 renderer 前失败或降级为 gap。
- **显示文字重新 grounding。** Script 已审不代表任意新增图中文字自动可信；事实性数字和日期必须有 Research 依据。
- **真实渲染才算 adapter 验收。** Mock 测试之外，两个 renderer 都实际生成了可探测的 MP4/PNG 并通过 QA。
- **制作输出与源代码隔离。** `production_packages/`、`production_assets/`、`production_projects/` 默认 Git ignore，避免把受权利约束素材、巨型依赖或视频二进制提交到公开仓库。

## 9. 哪些问题需要产品经理决定

V0.6 没有阻塞发布的工程问题。请产品经理 Review 后决定：

- 是否正式验收 Production Plan、V0.5.1 Input Gate、asset SHA Gate 与 Display Text Grounding 的边界。
- 是否认可普通工作流只选一个 renderer、跨 renderer 只做兼容性评测。
- 是否现在进入第一轮真实用户端到端试用：从用户主题开始，经过 Research、Script、Material 到 Motion Production，由用户在关键 Gate 做确认。
- 下一阶段应优先做受控端到端试用与问题修复，还是先加入完整 Composition / Editing Plan。工程建议先做小范围真实试用，不立即扩展自动发布。

## 10. 建议下一阶段做什么

若 ChatGPT 正式验收 V0.6，建议进入 **V0.7 Controlled End-to-End Trial**：选择 1 个真实但权利边界清楚的主题，跑通 Topic/Research → Script → Material → Motion，记录普通用户每一步需要确认什么、失败后如何恢复，并据此决定 V1.0 前真正缺少的能力。

此时已经接近第一轮普通用户端到端试用，但还不是“一键生成并发布完整视频”：主持人口播录制、最终剪辑与发布仍应由后续阶段明确设计。

## 11. 验证与真实评测

- 常规 unittest：**共 255 项，254 项执行通过，1 项真实渲染测试按默认设置跳过**；V0.5.1 的原 219 项全部保留。
- Cross-renderer integration：设置 `DEEPTALK_RUN_RENDER_INTEGRATION=1` 后，**1 项真实集成测试通过**。
- Remotion 4.0.507：同一 tiny Plan 生成 2 个 MP4（1920×1080、30 fps、约 1.045 秒）和 1 张 PNG，QA `pass`。
- HyperFrames 0.7.106：同一 tiny Plan 生成 2 个 MP4（1920×1080、30 fps、1 秒）和 1 张 PNG，QA `pass`。
- Stable Business：Apple bar motion、rough MP4 和 still 真实生成，package Gate `pass`。
- Contested Public：EU AI Act timeline 可生成；TechRadar `reference_only` 未进入 Scene，未取得的官方页记录为 gap。
- Rights Sparse：只使用 grounded diagram；AP 新闻 reference-only 未嵌入 renderer。
- Blocked / Tamper：draft、伪 reviewed、provenance 缺失、路径越界、MIME/SHA 不一致均 fail closed。
- Skill Creator validation：`produce-video-assets` 通过。

评测细节见 `docs/PRODUCTION_EVALS.md`，去内容化机器摘要见 `evaluations/v0.6.0-summary.json`。

## 给用户的下一步操作

下一步：把下面这段话原样发给 ChatGPT：

> 这是 Codex 完成的 DeepTalk Studio V0.6 Motion Production Layer。
>
> GitHub 仓库是
> https://github.com/HWang0310/deep-talk-studio ，
>
> Release 是
> https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.6.0 。
>
> 请完整 Review Production Plan、
> V0.5.1 输入 Gate、asset SHA Gate、
> Display Text Grounding、Remotion Adapter、
> HyperFrames Adapter、真实 render 输出、
> rough preview、Production QA、
> reference-only 隔离、测试和真实评测。
>
> 如果通过，请正式验收 V0.6，
> 并根据当前整体完成度判断：
> 是否已经应该进入第一轮真实用户端到端试用，
> 以及距离 V1.0 还缺什么。
>
> 不要让我自己总结。
