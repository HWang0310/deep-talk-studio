# DeepTalk Studio 工程协作规则

> **本文件只负责工程行为与关键约束，不是项目进度流水账或全部业务合同的副本。** 完整 Project Engineer Roster 原样保留在文末。代码/产品状态以实时 GitHub 和对应 canonical 文档为准。

## 最短恢复流程

1. 确认本机仓库路径、当前 branch/HEAD、dirty/unpushed 工作；先看相关 GitHub Issue/PR 的真实状态及 exact SHA，不覆盖用户本地文件。
2. 读本文件（规则和 roster）及 [CURRENT_CONTROL_PLANE.md](CURRENT_CONTROL_PLANE.md)（**当前唯一开发主线**）。短期索引不是实时服务；若冲突以远端真实状态为准，先报告并核实。
3. **按任务**使用 [docs/INDEX.md](docs/INDEX.md) 定位对应 Skill/合同、实现和测试；[PROJECT_STATE.md](PROJECT_STATE.md) 只在涉及已验收能力、版本、发布或产品范围时深读。README、PRD、ROADMAP、ARCHITECTURE 按需查阅。
4. `HANDOFF.md`、旧设计/计划、历史评测、已关闭 PR 和 release notes 是追溯依据，不是默认上下文、当前待办或新任务授权。
5. Nexus 负责 PM / exact-head 评审；项目 Engineer 身份由文末 roster 决定，Codex/TeleAgent 是执行 backend，**切换 backend 不改变人员身份**。任何新的开发方向、发布、权限、付费调用、删除分支或修改正式 Gate，都要匹配 Owner 的授权。

## 产品与执行边界（所有任务适用）

- 最新正式发布为 **v1.0.0**；新合入 `main` 的 post-release 代码、开放 PR 上的实现、已验收和正式发布必须严格区分。当前 Owner 优先级、开发 SHA 和待审项以 Control Plane + GitHub 为准；V2 Phase D/E/F、原生 TTS/声音克隆不是自动激活任务。
- **创作路径分两类：** 可在聊天中自由讨论、生成/修改明确标为 `Creative Draft / 未审核` 的草稿，普通草稿不强制核查；正式 `Reviewed Script` 和 Research / Fact Check / Thesis / Rights / Production 的原有审批、质量 Gate 仍为强制条件。聊天文字不能代替明确的权限卡、费用同意或准确版本的人工审批；模型不能自报 approved/reviewed、revision、provenance、QA 成功。
- B 站/竞品视频只参考**叙事结构**，不得洗稿、复制独特表达或作为事实来源。区分事实、当事方说法、观点及尚未核实内容；来源必须真实打开、记录 provenance，搜索摘要不等于独立核查，不得制造证据或把同源报道充作独立来源。
- 时间轴、字幕与素材插入时间只能根据**最终真实音频/视频和实际 ASR/对齐**产生，不能按稿件估计或由模型伪造。PR #31 已提供窄范围 WAV/MP3 audio-only CLI 适配（未正式发布）；不得由此假定 Web UI 已完成端到端交付。缺 ASR、clean/rights/QA 或有效正式工件时 fail closed。
- 人工决定最终使用的素材、配音、剪映/NLE 剪辑及发布；不自动删剪 A-roll、拼接停顿、生成 NLE 工程、输出成片、发布或绕过下载网站的登录/付费/风控/DRM。仅授权范围内获取已验证许可素材；不可把参考视频直接当可复用素材。
- 不把 API Key、密码、Cookie、私人音频、下载媒体、真实研究原稿或私有会话提交 Git 或写进日志/截图。默认保存于 gitignored 本地目录，验证路径/MIME/大小/权限/内容指纹；不得无授权调用收费 API、下载大型模型或上传私人材料。测试夹具须诚实标记，不能冒充真实 DeepSeek/B 站/真实媒体验收。
- 未经 Owner 明确改变方向，不放宽独立 Review、Claim/Evidence、Rights、Clean、Artifact lineage、Renderer QA 等校验，不通过改状态字段、重写结果、伪造时间戳或静默降级来让错误数据“通过”。所有正式工件身份/版本/指纹由代码负责。

## 任务 → 必读规则（仅在命中场景时加载）

| 任务 | Skill 与 canonical 合同 |
|---|---|
| 选题推荐、候选编号选择 | `.agents/skills/discover-topics/SKILL.md`、`docs/TOPIC_DISCOVERY_CONTRACT.md`；候选排序、来源实看和风险 Gate 必须复验，不把 Discovery 种子当事实 |
| 独立研究与事实核查（**正式路径**） | `.agents/skills/research-topic/SKILL.md`；Research Draft 与独立 Fact Check 各自留证，先审再确认 |
| 正式原创写稿与修订 | `.agents/skills/write-script/SKILL.md`、`docs/SCRIPT_CONTRACT.md`；只绑定已批准 Research/Thesis，独立 Writer / Reviewer，不用网络补缺或虚构事实 |
| 素材研究、来源检查及许可 | `.agents/skills/prepare-materials/SKILL.md`、`docs/MATERIAL_CONTRACT.md`、`docs/VISUAL_SPEC.md`；已审核脚本、Evidence、rights 与独立 QA 为前置 |
| 动画、渲染、Production | `.agents/skills/produce-video-assets/SKILL.md`、`docs/PRODUCTION_CONTRACT.md`、`docs/PRODUCTION_EVALS.md`；只有 QA-ready 输出可交付，特殊渲染器细节在合同/Skill 中 |
| 最终音频或视频对齐、Edit Map | `.agents/skills/align-video/SKILL.md`、`docs/EDIT_BRIDGE_CONTRACT.md`；实际输入的 ASR/timing 与 gap 必须真实 |
| Creator Workbench、DeepSeek 设置、对话 UI | `docs/WORKBENCH_CONTRACT.md`、相关 PR / 具体实现与测试；区分自由草稿与正式生产门禁，收费请求显式授权 |

**只执行与本次任务相关的 Skill；合同与实施代码若不一致，先提供证据并交 Nexus 复核，不能静默拿历史协议覆盖当前已批准事实。**

## 工程操作、测试和交接

- 在原有任务分支/PR 继续单一 Writer 工作；先补可复现的失败测试，再做最小实现。现有用户工作区、未提交更改、Git tag 和 Release 不得被擅自覆盖、重写或清理。跨文件大重构、额外新 Issue/PR 或改 PR base 前，先核对真实依赖并交 Nexus 判定。
- 需要联网而终端失败时，先诊断系统代理，仅对当前进程临时传递代理；绝不把地址中的机密或凭据写进仓库、Git 配置或日志。
- 验证按风险选用 `PYTHONPATH=src python3 -m unittest discover -s tests -v`、任务相关 pytest、Skill / Contract 评测、真实浏览器或音频端到端（必须明确 fixture vs real）。可用 `./scripts/deeptalk` 查看命令入口；不得为凑 PASS 降低检查标准。修改 Skill 需运行 Skill Creator `quick_validate.py`。
- 自动化测试与试用数据必须隔离：`pytest` 与 `unittest discover` 两种入口均应使用临时用户级配置及聊天目录，不得读取或覆盖 Owner 已保存的 DeepSeek Key 或真实历史；测试代码和执行结果应检验此隔离。
- 交付前做 `git diff --check`、敏感内容排查、必要的回归与真实使用证据。只更新与事实变更有关的 canonical owner；`CHANGELOG.md` 只记录已完成改动，`HANDOFF.md` 只记录值得留存的历史。改变产品定位、主流程、Gate、发布/能力状态时，才协调 PROJECT_STATE / PRD / ROADMAP / ARCHITECTURE / README，避免机械复制。
- 向 Owner 只报**结果、体验影响与下一步**；向 Nexus 提供 PR、exact SHA、测试/浏览器证据、未解决风险和 `READY_FOR_NEXUS_REVIEW`。PR 被审核前不得自行合并、打 tag 或发布。

## Project Engineer Roster

This section is the **sole canonical roster source** for the DeepTalk project. Other documents may cross-reference this section but must not duplicate the full roster.

| Project name | Global role              | Backend / resource    | State  |
| ------------ | ------------------------ | --------------------- | ------ |
| Nexus        | Project Manager Role     | ChatGPT               | active |
| Atlas        | Deep Engineering Role    | Codex / GPT-5.6 Sol   | active |
| Forge        | Primary Execution Role   | TeleAgent             | active |
| Scribe       | Secondary Execution Role | TeleAgent             | active |
| Orion        | Primary Execution Role   | WorkBuddy HY4         | active |

Roster rules:

- **Backend routing does not change engineer identity.** Switching the execution backend for a task does not create, rename, or remove an engineer.
- **New tasks / new sessions must not rename existing engineers.** Existing engineer names are fixed project state.
- **Roster add / replace / rename requires Owner approval.** No engineer may self-authorize a roster change.
- **GitHub roster is the recovery source for new sessions.** New sessions recover engineer identity from this section, not from conversation memory.
- **Rename / replacement history:** None. No engineer has been renamed or replaced since roster establishment.
- **Roster addition history:**
  - Orion was added by explicit Owner approval recorded in [Issue #6 comment 5566089657](https://github.com/HWang0310/deep-talk-studio/issues/6#issuecomment-5566089657).
  - This was a roster addition, not a rename or replacement.
  - Atlas remains an existing active project engineer identity.
