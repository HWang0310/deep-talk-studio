# DeepTalk Studio｜从这里开始

> **这是给 Owner / 普通创作者看的入口，不是技术设计书。** 久未使用时先看本页即可；不需要重读旧 ChatGPT 会话、HANDOFF.md 或历史 Issue。
>
> 当前正式产品：**v1.0.0「一主四辅」**（[正式 Release](https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0)）。最新发布状态以 [PROJECT_STATE.md](PROJECT_STATE.md) 和 GitHub 为准。下一阶段规划不等于现在能直接用的功能。

## 先选你的目的

| 我现在想做什么 | 进入哪里 | 先说什么 |
| --- | --- | --- |
| **创作视频**：选题、研究、写稿、配素材、做动画 | 在能操作本地项目的 Codex 中打开 DeepTalk 仓库，开启**创作对话** | 「我以创作者身份使用已发布的 DeepTalk；不要开发功能。先检查环境，之后帮我选题。」 |
| **管理产品**：查版本、查进度、提需求、修问题 | 找 **Nexus / ChatGPT PM**，由 PM 使用 GitHub 最新事实恢复 | 「按最新 engineering-journal 恢复 DeepTalk 当前 control-plane，告诉我现状与未决事项；不要擅自启动新开发。」 |

**不要混淆两种对话。** 创作请求不是工程任务；查状态、更新工程规范也**不等于**授权启动 Roadmap 上的下一功能。只有 Owner 明确选择产品目标后，PM 才激活开发任务。

## A. 我要创作一条视频（5 分钟找回用法）

### 1. 打开

在 Mac 上打开 Codex，选择本机已经存在的 **`deep-talk-studio`** 项目文件夹。此前使用过的目录示例：`~/Movies/Program/DeepTalk/deep-talk-studio`；以本机实际位置为准。没有该目录时先检查现有克隆，不要重复创建第二套活跃工作区。

**复制这段话作为本次创作对话的第一条消息：**

> 我要以普通创作者身份使用 **DeepTalk Studio v1.0.0** 已发布功能，不是让你开发软件。请按仓库现有 AGENTS.md 和对应 Skills 行动；先检查本地项目、可用工具与必要的配置，用简明中文告诉我哪些功能可以实际运行、缺什么。不要修改源代码、创建 Issue/PR、切换或重置我的工作区，也不要自动启动 V2。随后从「今天有什么值得讲的？」开始，优先商业、科技、社会话题，给我五个适合深度口播的选题。

Codex 或其他具备文件、终端与必要联网能力的 Agent 才能执行项目 Skills；**直接在 GitHub 网页浏览仓库不是在运行产品**。如果 Agent 无法读取本地目录或联网，应先报告障碍而不是假装运行完成。

### 2. 按自然语言使用

| 步骤 | 你可以这样说 | 正常得到什么 |
| --- | --- | --- |
| **选题** | 「今天讲什么？」或「只看科技，给我五个选题」 | 候选主题和推荐依据 |
| **研究** | 「研究第 2 个」 | 有来源的 Research + 独立事实核查 |
| **确认写稿** | 先审阅研究结论，再说「确认开始写稿，做成 8 分钟口播」 | 经独立审稿的提词稿；没有你的明确确认不会越过门槛 |
| **改稿** | 「开头再紧凑一点」 | 新的审阅后稿件版本，不覆盖旧稿 |
| **真实穿插素材** | 「给这期配素材，先挑关键画面」 | 素材准备单、可用素材和来源/权利说明 |
| **MG / 小黑漫画 / 手绘** | 「这段做 MG」/「这段做小黑漫画」/「这段做手绘动画」 | 在插件已正确安装启用、且存在有效 Visual Opportunity 数据时，生成经 QA 的候选素材 |
| **口播后对齐** | 「这是整理好的正式真人口播 MP4/MOV，帮我做素材包和剪辑参考」 | 基于真实语音时间的素材包与 Edit Map |
| **剪辑后复盘** | 「对照剪辑表看看我实际用了哪些画面」 | 只读差异与反馈，**不会**自动改成片 |

**不要一次性跳过 Gate。** Research → Fact Check → 你的确认 → Reviewed Script → 素材与制作有前后依赖。没有正式 Clean A-roll，就不能假造精确口播时间。

### 3. 第一次试用的建议

先只做 **选题 → 研究 → 写稿**，确认自然语言体验顺畅后再做穿插素材；三种动画选一个测试即可。三种生成式视觉插件在仓库的示例配置里默认 `enabled: false`，需要独立的本地插件、准确版本和机器本地配置。请求 Agent **先检查缺什么，再协助准备**；不得擅自更改插件固定版本或把启用配置提交到 GitHub。

**当前不会帮你做：** 自动选最佳画面、自动剪辑真人口播、生成剪映/NLE 工程、输出或发布最终成片。创作者自己录制、选择素材和剪辑。

## B. 我要继续管理 DeepTalk

请在 ChatGPT 的 Nexus / PM 对话中直接说：

> 根据 `https://github.com/HWang0310/engineering-journal` **当前 remote default branch** 最新规范，恢复 `HWang0310/deep-talk-studio` 的 remote current state。先看 `CURRENT_CONTROL_PLANE.md`、`PROJECT_STATE.md`、open Issue/PR 和必要的 canonical docs；给我一个简短状态摘要。先不要启动开发、改 Roadmap 或派 Agent。

PM 工作规则：

- **工程规范**：以 [engineering-journal](https://github.com/HWang0310/engineering-journal) 最新 remote default branch 为准，旧会话里的模型、人员、流程假设不能覆盖它。
- **产品现状**：[PROJECT_STATE.md](PROJECT_STATE.md)；**恢复索引/当前唯一任务**：[CURRENT_CONTROL_PLANE.md](CURRENT_CONTROL_PLANE.md)；**职责文档入口**：[docs/INDEX.md](docs/INDEX.md)；人员 identity 只以本项目 [AGENTS.md](AGENTS.md) 的 roster 为准。
- **先恢复 current state**：只看 live remote + 当前 open Issue/PR。旧 [HANDOFF.md](HANDOFF.md)、closed Issue/PR、历史 commits/tags/releases 是永久证据，不是默认待办，不删除或重写。
- **Owner 决定产品方向**。PM 可以自行做低风险 docs/onboarding 修正；不能因 Roadmap 写着 next 就私自开始 V2、发布或不可逆操作。
- **一次只维护一条 active execution/review thread**；有实施 PR 时默认在 PR 持续 review，修正轮只带 **correction delta**；remote 有相关 mutation 或合理怀疑过期时才 refresh。
- **使用模式 ≠ 开发模式**。测试使用问题先诊断本地输入、Skills 与安装/配置；确认是软件缺陷后再由 PM 判断是否创建 Issue。

## 遇到问题从哪里查

| 表现 | 先查什么 |
| --- | --- |
| 找不到项目 / Codex 不认识 DeepTalk | Codex 当前打开的本地文件夹，仓库 `AGENTS.md` 是否能读到 |
| 选题 / 研究做不出来 | Agent 是否有可用联网与页面打开能力；不能把未打开的来源当已核查 |
| 写稿被阻止 | Research、独立 Fact Check、你的确认、Script Review Gate 是否齐全 |
| 动画不能运行 | 有无有效 Visual Opportunity、机器本地插件路径 / `visual-asset-plugins.local.json`、插件版本与 `enabled` |
| 不能生成精确时间的剪辑表 | 是否已提供**正式 Clean A-roll**、ASR/对齐是否可用 |
| 想知道目前开发到哪 | 回到 Nexus，读 live GitHub + `CURRENT_CONTROL_PLANE.md`，不要从旧聊天猜测 |

> **最短记忆：** 想创作 → 本地 Codex 打开 DeepTalk → 说「今天讲什么？」。想管理 → 找 Nexus → 说「恢复 DeepTalk 最新 remote current state」。两条路径不要混成一条工程任务。
