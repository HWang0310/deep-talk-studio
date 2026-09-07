# DeepTalk Nexus Session Handoff — 2026-09-07

> 这是给下一任 DeepTalk 项目经理 / Nexus 的 GitHub-native 交接文档。
>
> **第一条必须执行：请参考 https://github.com/HWang0310/engineering-journal 的最新工程规范。**
>
> 不要把本文件里的 engineering-journal SHA 当成永久规范版本。新会话必须先读取 engineering-journal 当前 default branch 的最新 remote HEAD，再按最新规范工作。

## 1. 新项目经理的恢复顺序

不要让 Owner 重述项目历史，也不要依赖上一任 ChatGPT 会话记忆。

恢复顺序：

1. **请参考 https://github.com/HWang0310/engineering-journal 的最新工程规范。**
2. 打开 `HWang0310/engineering-journal` 当前 default branch，确认最新 exact SHA，并按 `NEW-SESSION-BOOTSTRAP.md` 读取全部必读规范。
3. 打开 DeepTalk Recovery Issue #3：`https://github.com/HWang0310/deep-talk-studio/issues/3`。
4. 读取本文件的 immutable exact-commit 版本。
5. 独立检查 `HWang0310/deep-talk-studio`：正式 `main`、canonical dev `agent/multi-asset-studio`、Phase 6 branch `agent/phase6-niulai-owner-demo`。
6. 独立检查三个插件仓库当前 `main` 与对应 Recovery Issue #1。
7. 当前 GitHub remote / exact SHA 永远覆盖本交接快照。
8. 恢复后向 Owner 简洁报告：当前阶段、当前阻塞、下一步、是否需要派 Agent；不要要求 Owner 搬运长技术 handoff。
9. 在 DeepTalk Issue #3 写 `PROJECT_RECOVERED` ACK。

本次交接时，engineering-journal 最新已核验 HEAD 为：

`755b20d854ec5f780345fb00dd6ec7c6d54a8c66`

但下一任 Nexus 必须重新 fetch 最新 HEAD，不得冻结在这个 SHA。

---

## 2. DeepTalk 项目身份与角色

项目：**DeepTalk Studio**

GitHub Core：`HWang0310/deep-talk-studio`

项目目标：为人类主导的深度口播视频提供从研究、内容论证、脚本、真实 A-roll 语义时间线，到视觉机会识别、候选视觉素材生成、QA、Candidate Asset Pack、Multi-option Edit Map 的完整生产辅助链路。

项目不是“一键自动剪辑器”。

DeepTalk 项目既有角色：

- **Owner**：用户 / 产品 Owner。负责目标、优先级、内容方向与最终创作者选择。
- **Nexus**：ChatGPT 项目经理。负责架构协调、任务拆解、backend 路由、Prompt、exact-SHA Review、验收、merge/release gate。
- **Atlas**：Deep Engineering engineer；历史上用于高风险 Core、Contract、跨 repo integration、复杂问题与高风险 Review。
- **Forge**：Primary execution engineer；历史上承担明确 scope 的主要实施任务。
- **Scribe**：Secondary execution / docs-support engineer；用于真正独立的第二执行流、文档或支持性任务。

**不要因为新任务、新 backend 或新阶段临时创造新的 DeepTalk 工程师名字。** 新增/替换 roster 必须遵守 engineering-journal 最新 stable roster 规则并由 Owner 明确批准。

WorkBuddy HY4 是 engineering-journal 已定义的可用高能力 execution/review backend，**不是新的固定 DeepTalk 工程师身份**。是否映射给 DeepTalk 既有 roster，必须按最新规范和 Owner 授权处理。

---

## 3. Product Thesis / 主体与插件分工

DeepTalk Core 的核心职责是：

> **决定哪里需要视觉、这段视觉要表达什么、调用哪些候选能力、如何保存/QA/编排候选；最终视觉选择和最终剪辑仍归创作者。**

当前整体工作流：

```text
Topic
→ Research / Fact Check
→ Content Thesis
→ human confirmation
→ Reviewed Script
→ Final Clean A-roll
→ ASR / Alignment
→ Semantic Timeline
→ Visual Opportunity
→ non-exclusive Candidate Portfolio
→ family-specific generation
→ Candidate QA
→ Candidate Asset Pack
→ Multi-option Edit Map
→ creator manual NLE selection
```

### Core

Core 是内容导演 + 视觉机会规划器 + 插件调度器 + 候选素材编排系统。

Core 不负责“把所有画面都自己生成”，也不自动做最终艺术决策。

### MG Visual

主要承担：

- 因果机制；
- 逻辑链路；
- 结构关系；
- 过程解释；
- 信息层级与动态图形表达。

当前产品判断：三条生成线中**最接近生产价值**，后续质量重点是减少 PPT / knowledge-card 感，提升 typography、hierarchy、composition、motion grammar、easing、transition、信息密度与视觉导演感。

### Illustrated Metaphor

主要承担：

- 抽象概念可视化；
- 情绪 / 社会心理 / 张力；
- 隐喻表达；
- 氛围与轻解释。

当前主要问题：semantic specificity 不够，模板/动作/隐喻复用明显。后续要扩充对象、动作、构图、隐喻词汇，让每个 opportunity 更像“这句话专属的画面”。

正式产品名称使用 **Illustrated Metaphor**；“小黑方向”只可作为 Owner 的口头参考，不应成为新的正式生产插件身份。

### Hand-drawn Animation

主要承担：

- 白板/草图式解释；
- 手绘流程；
- 更有人味的过程演示；
- 轻量机制 / 概念说明。

当前第一优先级不是美术升级，而是 **generation completeness**：Phase 6 真实机会中出现“渲染出 frames，但未按 Contract 完成最终 media / manifest”的缺陷。必须先修完整性并建立 regression，再进入美术、动作、表达力优化。

### 插件关系

插件不是互相争夺“冠军”。同一个 Visual Opportunity 可以同时得到 MG、Illustrated、Hand-drawn 等不同 candidate。

创作者可以：

- 一个都不用；
- 用其中一个；
- 前后组合多个。

Core 不自动选 winner，不自动消解 overlap。

---

## 4. Hard Product Boundaries

以下边界不得在没有新架构决策的情况下放宽：

- A-roll 永远是 base layer。
- Candidate 非互斥，可 overlap、可不同 duration、可不同 family。
- Creator 可选 none / one / multiple。
- 不自动选 winner。
- 不自动做 overlap resolution。
- 不自动生成 NLE project。
- 不自动修改 A-roll。
- 不自动生成 final finished cut。
- 不自动发布。
- V2 不新增假的 `KEEP_A_ROLL` Candidate；没有 Visual Opportunity 就是不需要额外素材。
- Generated explanatory asset 不得冒充 documentary / evidence material。
- V1 artifact compatibility 保持，除非另行做 versioned migration。

---

## 5. Formal Release 与 Core 当前状态

### Formal Release

`main`：

`8a0ac94cbaf6b2a472c3624c1c2e1f573cfb113d`

Formal Release：**v0.6.1**

当前开发仍是：**V1.0 Candidate — Unreleased**

不要把 dev branch、plugin main、Phase 6 evidence branch 描述成 release。

### Canonical dev

Branch：

`agent/multi-asset-studio`

当前已核验 HEAD：

`db172cecc60ca6b0c276ec42010b113a767bc7b3`

状态：**Phase 5 ACCEPTED / IMPLEMENTED_UNRELEASED**。

重要：该 SHA 上 `PROJECT_STATE.md` 有部分文字仍停留在“Phase 5 awaiting acceptance”，属于 state-doc lag；Nexus 后续的 exact-SHA Review / Issue #3 记录已经接受 Phase 5。不要因为旧字段把 Phase 5 错退回未验收状态。

### Accepted Core milestones

- Phase 3A-2：`990fc03922e527bef64b819cf898e4266d5669c1`
- Phase 3B：`ec595587a378d54bd2a18270ded504707b04ddea`
- Phase 4：`817ca8b424f18714e4280d3990c1bc4221ec8dbe`
- Phase 5：`db172cecc60ca6b0c276ec42010b113a767bc7b3`

Phase 4 artifacts：

- `candidate-asset-pack/1`
- `candidate-edit-map/1`

Phase 5 已证明：三插件 real runner synthetic integration、order independence、failure isolation、ABSTAIN/no-call、Portfolio/Pack/Map 以及普通 subprocess/file runner 可工作。

---

## 6. Phase 6 — Owner-visible Micro Demo

Task：`DT-CORE-6-001 — Phase 6 Owner-visible Micro Demo`

Branch：

`agent/phase6-niulai-owner-demo`

当前已核验 HEAD：

`b72b7c232d24f4b1e1ac531f6f6ef0396e001c0b`

它的 parent 是 accepted Phase 5 `db172ce...`。

Phase 6 使用真实《牛来》 A-roll 做 Owner-visible 微型 Demo，产生了 4 个 READY candidates，并明确暴露三插件真实边界。

正式状态：

**`TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW`**

这不是 PASS，也没有推进 canonical dev。

**下一任 Nexus 不得静默把 Phase 6 标记 ACCEPTED。** 只有 Owner 明确接受方向/质量，才可关闭 Owner Review gate。

已观察到的产品结论：

- MG：机制解释最有潜力，但视觉上仍偏文字密集 / 卡片 / PPT 感。
- Illustrated：视觉身份清晰，但不同 opportunity 容易复用相似隐喻和动作，semantic specificity 不够。
- Hand-drawn：Suitability 可以成立，但真实 generation 暴露最终 media/manifest completeness 缺陷。

Phase 6 本地 Owner Review media 保持本地 / gitignored，不要求把视频文件塞进 GitHub。

---

## 7. Contract V1 关键不变量

Contract：

`visual-asset-plugin-contract/1`

Suitability：

- `SUITABLE`
- `BORDERLINE`
- `ABSTAIN`

Generation operation：

- `COMPLETED`
- `FAILED`
- `BLOCKED`
- `UNAVAILABLE`

Candidate：

- `READY`
- `QA_REJECTED`

Core acceptance 独立：

- `ACCEPTED`
- `REJECTED`

关键规则：

- raw plugin status 不改写；
- creator pack 只允许 raw READY + Core ACCEPTED；
- machine portfolio 保留 failure/rejection/no-call/policy evidence；
- LEAN：所有 completed SUITABLE；
- STANDARD：有 SUITABLE 时生成 completed SUITABLE；没有 SUITABLE 才使用 completed BORDERLINE；
- RICH：completed SUITABLE + BORDERLINE；
- ABSTAIN / failure / disabled 不生成；
- 永远不做 winner selection。

---

## 8. 三插件的 Runtime baseline 与 governed main

必须区分：

- **runtime behavior baseline / Core exact pin**
- **plugin governed main（含后续 governance docs）**

### MG

Repo：`HWang0310/deeptalk-mg`

Governed `main`：

`b7b71855f31f269c348a6794e3d2b4146e9c36e7`

Accepted runtime behavior baseline / Core pin：

`7ae59f1115da8a011113c81f31d320783b0ce8a4`

Runner：

`node scripts/contract-runner.js`

Identity / version：

- `org.deeptalk.mg`
- `1.0.0-contract-v1`

### Illustrated Metaphor

Repo：`HWang0310/deeptalk-illustrated-metaphor`

Governed `main`：

`ad65204b95163bb57b7b5e32e099fcb769201336`

Accepted runtime behavior baseline / Core pin：

`48848affe018fc2cff8ee15bad7a09bb002776e4`

Runner：

`python3 scripts/contract_runner.py`

Version：

`0.2.0-contract-runner`

### Hand-drawn Animation

Repo：`HWang0310/deeptalk-handdrawn-animation`

Governed `main`：

`916322a85358d537ba06a233fb7fa386a2cfe75c`

Accepted runtime behavior baseline / Core pin：

`853618bdf19ae66ec393211b77d970911f53f4bc`

Runner：

`node src/contract-runner.js`

Version：

`handdrawn-animation-contract/0.1.0`

所有 Core static plugin production entries 仍应保持 disabled，除非另有明确 production-migration task。

---

## 9. Plugin governance / 独立优化模式

治理任务已完成：

- `DT-GOV-PLUGIN-001`
- `DT-GOV-PLUGIN-002`

`DT-GOV-PLUGIN-002` 对应 DeepTalk Issue #5，状态 CLOSED / completed。

统一规则：

```text
DeepTalk 总项目：DeepTalk GitHub
MG：MG GitHub
Illustrated：Illustrated GitHub
Hand-drawn：Hand-drawn GitHub
```

每个插件都拥有自己的：

- Recovery Issue #1；
- Task ID；
- branch/worktree；
- exact SHA；
- Plugin Curator Review；
- durable project memory。

插件内部：

`Plugin Curator ↔ plugin GitHub ↔ Agent`

跨项目：

`Plugin local acceptance → PLUGIN_OPTIMIZATION_READY + exact SHA → DeepTalk Nexus independent Core integration review → PASS 后才允许 Core repin`

原则：

> 插件 PM 决定“这个插件够不够好”；DeepTalk Nexus 决定“这个版本能不能接入 DeepTalk”。

Owner 不应搬运长技术报告；当 PM 能访问 GitHub 时，Owner 通常只需要报告 `Agent + Task ID 跑完了`。

---

## 10. 当前推荐产品路线

当前阶段已经从“走通”进入“走好”。

不要优先继续给 Core 增加新功能。下一阶段高价值方向是**插件独立质量优化**，然后回到 DeepTalk 做 integration review。

推荐顺序：

1. **MG Quality V2**：最接近生产价值，优先提升 composition / typography / hierarchy / motion grammar / pacing / transitions，降低 PPT/知识卡感。
2. **Hand-drawn generation completeness**：先修 Phase 6 暴露的最终 media/manifest 完整性，再进入视觉质量提升。
3. **Illustrated semantic specificity**：降低模板/动作/隐喻复用，提高 opportunity-specific variation 与 honest abstention。

这只是当前产品优先级建议，不是新的 immutable schema rule。Owner 可以调整优先级。

Phase 6 Owner Review 仍单独保持 HOLD；插件优化可以独立开始，但不得用插件优化自动代替 Phase 6 Owner acceptance。

---

## 11. 本地 workspace

历史已使用的 DeepTalk project workspace root：

`/Users/hwang/Movies/Program/DeepTalk/`

Repos：

- `/Users/hwang/Movies/Program/DeepTalk/deep-talk-studio`
- `/Users/hwang/Movies/Program/DeepTalk/deeptalk-mg`
- `/Users/hwang/Movies/Program/DeepTalk/deeptalk-illustrated-metaphor`
- `/Users/hwang/Movies/Program/DeepTalk/deeptalk-handdrawn-animation`

但下一任 Nexus 在任何本地施工前都必须按 **engineering-journal 最新 `LOCAL-WORKSPACE-STANDARD.md`** 重新验证 workspace、origin、branch/base SHA，不要仅凭本文件假定本地状态。

Agent 默认 workspace 不是正式 Project workspace。

---

## 12. 近期 anti-pollution 说明

`engineering-journal` 是工程规范与可复用知识仓库，不是 DeepTalk 的项目任务看板。

最近曾误创建 `engineering-journal` Issue #1 并把一次本地 workspace 清理当成独立项目任务；该 Issue 已明确标记：

`[VOID] Accidental local-workspace task — non-canonical`

并以 `not_planned` 关闭。

下一任 Nexus：

- 不要从该 VOID Issue 恢复任何 DeepTalk 项目状态；
- 不要继承其中的临时 engineer identity；
- 不要把那次 workspace 清理 handoff 混进 DeepTalk 项目记忆；
- 唯一应继承的是 **engineering-journal 正式 main 中已经存在的最新规范**，包括 HY4 capability routing、stable roster、local workspace、GitHub-native handoff、risk-based plan/review/evidence 等规则。

---

## 13. 新 Nexus 的第一轮动作

恢复后先做事实核验，不要直接派工：

1. fetch engineering-journal 最新 main；
2. fetch DeepTalk `main`、`agent/multi-asset-studio`、`agent/phase6-niulai-owner-demo`；
3. fetch 三插件最新 `main`；
4. 读取 DeepTalk Issue #3 最新 transfer comment；
5. 检查 plugin Recovery Issue #1；
6. 明确 Phase 6 仍 HOLD；
7. 明确当前是否先启动 MG 独立优化，或 Owner 是否有新的产品优先级；
8. 写 `PROJECT_RECOVERED` ACK；
9. 向 Owner 用简短中文报告恢复结果。

推荐 ACK：

```text
PROJECT_RECOVERED
ROLE: Nexus
ENGINEERING_STANDARD_HEAD: <latest engineering-journal SHA>
CORE_MAIN: <current full SHA>
CORE_DEV_BRANCH: agent/multi-asset-studio
CORE_DEV_HEAD: <current full SHA>
PHASE6_BRANCH: agent/phase6-niulai-owner-demo
PHASE6_HEAD: <current full SHA>
PHASE6_STATE: <verified state>
MG_MAIN: <current full SHA>
ILLUSTRATED_MAIN: <current full SHA>
HANDDRAWN_MAIN: <current full SHA>
NEXT_ACTION: <concise>
GITHUB_VERIFIED: YES
```

---

## 14. 最后一条治理原则

**请参考 https://github.com/HWang0310/engineering-journal 的最新工程规范。**

这句话不是背景资料提示，而是新 Nexus 的工程协作启动指令。

GitHub remote + exact SHA 是工程事实；Agent 自述、旧 handoff、旧会话记忆只能辅助恢复，不能覆盖当前 remote。

历史要保留，但当前 truth 必须集中、可核验、可恢复。
