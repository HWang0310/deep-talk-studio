# DeepTalk Studio

> 当前开发分支包含 **Unreleased Audio Alignment + Visual Edit Bridge**。它已具备确定性媒体时间、带时间戳转录适配、Script/Transcript 对齐、Beat/Cue 画面标记、统一视觉 Placement、Remotion 粗预览和 A-roll 音频 presentation 保真能力；只有完成真实 Clean A-roll 用户试用后才可讨论正式版本或 V1.0。

DeepTalk Studio 是一个面向长期 B 站个人 IP 的 AI 内容生产项目。它服务于真人露脸深度口播：先建立可核查的研究底稿，再逐步扩展到原创口播稿、素材建议、可视化、剪辑和发布。

当前版本是 **V0.6.1**。研究、独立事实核查、原创写稿、素材准备和制作已连成可验证链路。已审查素材包可由 Remotion 或 HyperFrames 中的一个引擎生成真实 MP4 动画、粗剪视觉预览、PNG 定帧和制作质检报告；四类图表会按内部元素真正运动，不再只是整张 SVG 进场。

Audio Alignment + Visual Edit Bridge 正在 Unreleased 分支按批准计划实现。真实文件转录适配器遵循当前 OpenAI 官方 File transcription 契约：文件上限 25 MB；需要 word timestamp 时使用 `whisper-1`、`verbose_json` 和 `timestamp_granularities=["word"]`。大文件只使用版本化 PCM 自然停顿 Chunk Plan，不在 adapter 内任意切分，也不伪造 segment 的词级时间。

## 现在最简单的用法

在 Codex 中打开这个仓库，然后直接说：

> 请用 DeepTalk Studio 研究“你想研究的话题”，生成 Research Report。

或者直接说：

> 今天讲什么？

> 帮我找几个科技选题。

> 最近社会热点有什么值得讲？

仓库里的 `discover-topics` 和 `research-topic` Skill 会被 Codex 自动识别。前者只做轻量资料预检、去重和排序；后者才联网搜索、整理证据并完成独立 Fact Check。你不需要理解代码，也不需要自己拼命令。

当报告通过质量 Gate 后，直接说：

> 确认进入写稿，做成 8 分钟的 B 站口播稿。

仓库里的 `write-script` Skill 会先记录你的确认，再生成稿件和独立审稿结果。之后也可以直接说“做长一点”“第二段更紧凑”或“比较这两个版本”。每次修改都会建立新版本，不覆盖旧稿。

稿件通过审查后，直接说：

> 给这期配素材。

> 把画面准备一下，少一点，只配关键段落。

`prepare-materials` Skill 会核对稿件的真实 Review 凭证和精确 Research 版本，再搜索并实际打开候选页面、保守判断复用权利、生成画面提示和原创 SVG，并进行独立 Material Review。你不需要自己判断版权术语或管理文件。

素材包通过审查后，直接说：

> 生成视频素材。

> 做一下动画和粗剪预览。

`produce-video-assets` Skill 会自动找到最新合法输入，选择一个制作引擎，运行预览、渲染和 QA，并只告诉你生成了什么、哪些可用、哪些还需要真人口播或手工补画面。

当你已经把真人口播的口气剪好，只需要把 mp4/mov 拖进 Codex，然后说：

> 我视频剪好了，帮我把素材卡进去。

`align-video` Skill 会自动使用已审核稿件、素材和 Motion，导入原视频、完成转录与时间对齐，再生成 Edit Bridge 和 Aligned Preview。你不需要另外录音、提取音轨、标记时间点或选择技术参数。真实视频完成这一步并由你看过 Preview 之前，本阶段仍保持 Unreleased。

选题结果会保存在本机：

```text
discoveries/YYYY/MM/DD/选题批次ID.md
discoveries/YYYY/MM/DD/选题批次ID.json
discoveries/latest.json
```

每次都是独立历史记录；`latest.json` 只用于让你下一句回复“1”时能知道你选的是哪一题。真实选题列表默认不会上传 GitHub。

报告默认保存到：

```text
reports/YYYY/MM/DD/主题/报告ID/research-report-r0001.md
reports/YYYY/MM/DD/主题/报告ID/research-report-r0001.json
reports/YYYY/MM/DD/主题/报告ID/fact-check-for-r0001-核查ID.json
reports/YYYY/MM/DD/主题/报告ID/research-report-r0002.json
```

`reports/` 默认不会上传 GitHub，避免未经编辑审查的研究材料被意外公开。

稿件默认保存在本机：

```text
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0001.json
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0001.editor.md
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0001.teleprompter.md
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-review-for-r0001-审稿ID.json
script_drafts/YYYY/MM/DD/报告ID/稿件ID/script-draft-r0002.json
```

完整真实稿件同样默认不会上传 GitHub。

素材准备单和本地素材默认保存在：

```text
material_packages/YYYY/MM/DD/报告ID/稿件ID/素材包ID/material-package-r0001.json
material_packages/YYYY/MM/DD/报告ID/稿件ID/素材包ID/material-package-r0001.md
material_packages/YYYY/MM/DD/报告ID/稿件ID/素材包ID/material-input-for-r0001.json
material_packages/YYYY/MM/DD/报告ID/稿件ID/素材包ID/material-inspection-for-r0001.json
material_packages/YYYY/MM/DD/报告ID/稿件ID/素材包ID/material-rights-for-r0001.json
material_packages/YYYY/MM/DD/报告ID/稿件ID/素材包ID/material-review-for-r0001-审查ID.json
material_assets/素材包ID/generated/V001.svg
```

两类目录都默认不上传 GitHub，避免把受版权保护的真实素材或内部工作稿意外公开。

制作计划、真实输出和渲染工程分别保存在 `production_packages/`、`production_assets/` 和 `production_projects/`，三者均默认不上传 GitHub，且已存在的同次输出不会被覆盖。

## 项目现在能做什么

- 接受社会、时事、商业、科技、网络热点或公共事件主题；
- 当你没有选题时，寻找最近 72 小时、或最近 14 天持续事件的新进展；默认只给最多 5 个候选，并明确一个“首选”；
- 对候选执行轻量资料预检：只有实际打开或 API 可追溯的不同合格来源方向才可推荐；同链接、同发布者或同网站不能重复凑数；
- 自动拒绝事件时间倒置、明显未来时间或不足 7 个原始候选的“看似完成”结果；高风险但资料薄弱的事件只列为观察，不进入推荐；
- 候选的资格、理由、总分、推荐、展示顺序、首选和统计数均由程序重新计算；被手工改写的候选文件不能继续使用；
- 默认先让分类多样，再用同分类高分题补足空位，因此用户只看科技时仍最多可得到 5 个不同事件；
- 用可解释的五项评分计算总分：可核查性 30%、深度冲突 25%、新鲜度 20%、频道匹配 15%、公开关注信号 10%；总分由程序计算；
- 让你只回复“1”或“研究 1”就把候选的研究问题、核心冲突、风险提示和资料入口交给 Research Workflow；
- 搜集并登记可点击的公开来源；
- 记录来源是否真的出现在本次搜索或引用工具结果中；
- 整理事件时间线；
- 区分已确认事实、媒体报道、当事方说法、评论观点和尚未证实的信息；
- 汇总不同来源与不同立场；
- 指出观点冲突、证据边界和仍需追问的问题；
- 推荐原创内容切入角度，并生成给 Script Agent 使用的安全交接字段；
- 用 Evidence Ledger 标明来源是支持、反驳、归属说法还是只提供背景；
- 识别重复 URL、同发布者和疑似转载，避免把同一信源误算成多源；
- 只有明确标为独立、provenance 已匹配且属于不同分组的支持来源，才能形成两份独立确认；`unknown` 不会被猜成独立；
- 自动把高风险主张放入二次核查队列，并单独保存 FactCheck Artifact；
- 计算来源覆盖率、独立来源覆盖率、高风险核查率等质量指标；
- 保留不可覆盖的报告修订版和更正记录；
- 把用户的写稿确认保存为新的、不可覆盖的 Research Revision；未批准报告无法生成稿件；
- 用 Script Profile 0.4 生成适合 B 站真人露脸的原创口播稿，默认约 12 分钟，也可用自然语言调整时长；
- 在每个稿件段落保留事实、归因、分析、转场或问题类型，并回链 Research Claim 与 Evidence；
- 自动拦截未核查事实、禁讲结论、伪造机器字段和高风险越界；计算 must-keep 覆盖、字数和估算时长；
- Writer 完成后由独立 Reviewer 检查 15 个维度；有事实或归因阻断问题的稿件不能成为 `reviewed`；
- 同时输出含编辑线索的 Editor 版和可直接朗读、没有机器 ID 的 Teleprompter 版；
- 任何稿件修改都产生不可覆盖的新 revision，并可比较两个版本；
- Review 的 15 项检查都必须和具体问题闭环；事实安全检查失败时，系统拒绝把稿件误判为通过；
- `reviewed` 稿件会校验对应的 Review Artifact、原稿版本与内容指纹，单独改状态无效；
- 修改、移动或插入段落时保留已有 Beat 身份，删除的 Beat ID 不再复用，因此版本比较不会把一次插入误报为整篇重写；
- 在保存前执行完整 Schema 和跨字段校验，错误会给出中文提示。
- 只允许有真实 V0.4.1 Review linkage、内容指纹和精确 Research revision 的 `reviewed` 稿件进入素材流程；手改状态或伪造 Review 无效；
- 用短原句 anchor 给关键 Beat 安排证据、背景、说明或转场画面，不强迫每段都有素材；
- 搜索并实际检查公开文件、网页、截图、照片、视频引用、数据源和档案；搜索摘要只能算发现，不能算页面已检查；
- 对每项素材记录来源、发布者、检查方法、Claim/Evidence 回链、使用位置、时长和可证明/不可证明边界；
- 用单独 Rights manifest 判断 public domain、明确复用、CC、official press asset、仅编辑引用、需许可、未知或避免使用；未知版权绝不会成为可直接使用；
- 可直接使用的素材必须同时有素材页和权利依据页的实际打开记录；权利页工具记录必须能一一对应，不能只靠模型或文件自称；
- 只安全保存明确可复用的静态文件，拒绝本机/内网、危险 MIME、超大文件、脚本 SVG、路径越界和覆盖；截图保留页码、裁切区域和语境；
- 若素材搜索出现冲突或新事实，标记 `research_update_required`，不会静默改稿、改研究或改图表；
- 只用已批准 Research 数据生成 timeline、bar、comparison、diagram，实际输出 1920×1080 SVG 和 SHA-256；
- 每个图表内部事件、数值、比较项和关系节点都会逐条回查 Research Claim/Evidence；手改已审素材包的状态、权利、排序或审查关联，在重新打开时会被拒绝；
- 由独立 Material Reviewer 检查来源、权利、Claim 对齐、误导裁切、时效、身份、生成数据、AI/真实混淆、重复和用途；危险 item 可隔离，包级伪造会阻断。
- 将通过 V0.5.1 canonical Gate 的 Material Package 确定性映射为 Production Plan 0.6.1；`scene_payload` 保存 timeline、bar、comparison、diagram 的真实数据、顺序、文字和 Claim/Evidence binding。
- 渲染前重新检查本地路径、格式、大小和 SHA-256；`reference_only`、`permission_required`、`rejected` 与被篡改素材永不进入 Composition。
- 对所有事实画面文字重新做 Research Claim/Evidence/Timeline 语义 grounding；没有数字也不能绕过，无关 Claim ID 不能充数。
- 原始 PDF 只保留来源记录，只有 V0.5 已登记的 PNG/JPEG/WebP 页面截图可以进入图片 renderer；无截图时明确报告缺口。
- 普通制作只启动 Remotion 或 HyperFrames 中的一个；两者都能输出 1920×1080、30 fps 的动画片段、粗剪预览和定帧图。
- Motion Asset Manifest 保留路径、时长、尺寸、帧率、字节大小、SHA-256、来源 binding 和渲染命令摘要；Production QA 由结构化 check 自动推导 issue 和 Gate，检查失败不可能与通过状态并存。

## 还不能做什么

V0.6.1 生成的是可导入剪辑软件的辅助动画和 rough visual preview，不是含真人口播的最终成片。它不做假主播、TTS、精确音频对齐、自动字幕、BGM/SFX、标题封面、B 站上传或运营分析。来源与权利工程检查也不等于律师意见或最终发布批准。

## 不依赖联网的检查方式

项目要求 Python 3.9 或更高版本，不需要安装第三方包。

生成虚构示例报告：

```bash
./scripts/deeptalk sample
```

校验当前 Research Report 示例：

```bash
./scripts/deeptalk validate examples/sample-research-report.json
```

运行全部测试：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Codex Skill 模式还可以把研究内容整理为带机器字段的草稿，再应用独立核查：

```bash
./scripts/deeptalk prepare-draft examples/sample-codex-draft-input.json
./scripts/deeptalk review-report 草稿.json fact-check.json
```

普通用户不需要自己执行这两条命令，Codex 会代为完成。

V0.4 的底层调试入口包括：

```bash
./scripts/deeptalk approve-report reviewed-report.json --confirmation "确认开始写稿"
./scripts/deeptalk prepare-script approved-report.json script-content.json --duration "8 分钟"
./scripts/deeptalk review-script approved-report.json script-draft-r0001.json review.json
./scripts/deeptalk compare-script script-draft-r0001.json script-draft-r0002.json
```

这些命令面向测试和自动化；普通用户只需在 Codex 中用自然语言确认和修改。

V0.5 的底层调试入口包括：

```bash
./scripts/deeptalk prepare-materials approved-report.json reviewed-script.json material-content.json --inspection-manifest inspection.json --rights-manifest rights.json
./scripts/deeptalk review-materials approved-report.json reviewed-script.json material-package-r0001.json material-review.json
./scripts/deeptalk materials approved-report.json reviewed-script.json
```

普通用户仍只需说“给这期配素材”。

V0.6 制作调试入口：

```bash
./scripts/deeptalk produce-assets approved-report.json reviewed-script.json reviewed-material-package.json --renderer auto
```

普通用户只需说“生成视频素材”。

开发或自动化时也可以使用：

```bash
./scripts/deeptalk discover "今天有什么值得讲？"
./scripts/deeptalk discover "最近科技商业有什么值得讲？" --category tech
./scripts/deeptalk select-topic "1"
```

没有 API 密钥时，这些联网命令会提示回到 Codex 自然语言入口；不会假装完成搜索。

## 可选的 API 自动化入口

未来需要脱离 Codex 批量运行时，可以配置 `OPENAI_API_KEY`，再执行：

```bash
./scripts/deeptalk research "要研究的主题"
```

该入口使用 OpenAI Responses API 的 `web_search` 与结构化输出，并保留 `web_search_call`、URL citation 和完整 action sources 的可用 provenance。API 模型只生成研究内容；报告身份、修订、状态、质量和审批字段全部由程序生成，模型无法自报通过。研究与事实核查是两次独立调用。密钥只能放在环境变量或密码管理器中，绝不能写进仓库。没有 API 密钥也不影响在 Codex 中使用仓库 Skill。

实现依据：[OpenAI Web Search 文档](https://developers.openai.com/api/docs/guides/tools-web-search)、[Structured Outputs 文档](https://developers.openai.com/api/docs/guides/structured-outputs)、[Codex Skills 文档](https://learn.chatgpt.com/docs/build-skills)。

## 项目结构

```text
.agents/skills/discover-topics/ Codex 可自动发现的选题发现工作流
.agents/skills/research-topic/  Codex 可自动发现的研究工作流
.agents/skills/write-script/    Codex 原创写稿、独立审稿与版本修改工作流
.agents/skills/prepare-materials/ Codex 素材搜索、权利检查、原创画面和独立审查
.agents/skills/produce-video-assets/ Codex 动画素材、粗剪预览和制作 QA
config/channel-profile.json     V0.3 默认频道定位
config/script-profile.json      V0.4 口播风格、时长和原创性约束
config/material-profile.json    V0.5 B 站画布、视觉风格和安全获取限制
config/production-profile.json  V0.6 统一画布、设计 token 和渲染版本
renderer_templates/             锁定版本的 Remotion / HyperFrames 制作模板
src/deeptalk_studio/            研究、稿件、素材、制作、QA、保存和 API 适配
scripts/deeptalk                无需安装的统一入口
scripts/build_v061_motion_evidence.py 双引擎公开虚构动效证据生成器
examples/                       虚构 Research、Script 和 Review 输入示例
evaluations/                    去内容化真实编辑评测汇总
tests/                          自动测试
docs/                           架构、设计和实施计划
PRD.md                          产品要求
ROADMAP.md                      长期路线
AGENTS.md                       未来 Codex 工作规则
CHANGELOG.md                    实际修改记录
HANDOFF.md                      每轮开发交接
```

## 长期协作方式

- ChatGPT：产品经理 / 架构师，负责 Review、优先级和下一轮需求。
- Codex：工程师，负责实现、测试、修复、文档和 GitHub。
- 用户：只负责复制、粘贴和确认，不负责总结技术内容。

每轮开发结束后维护 [HANDOFF.md](HANDOFF.md) 作为项目记录，同时在面向普通用户的阶段回复底部直接提供可原样发送给 ChatGPT 的完整交接文字，不要求用户进入文件查找。V0.6 制作边界与真实评测见 [docs/PRODUCTION_CONTRACT.md](docs/PRODUCTION_CONTRACT.md) 和 [docs/PRODUCTION_EVALS.md](docs/PRODUCTION_EVALS.md)。

正式版本的 GitHub 发布与未来软件包规则见 [RELEASE_POLICY.md](RELEASE_POLICY.md)。
