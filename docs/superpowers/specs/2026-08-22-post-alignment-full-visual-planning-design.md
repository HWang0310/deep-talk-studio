# Post-Alignment Full Visual Planning Design

## Goal

让 DeepTalk 在不修改 Script、Research、Transcript 或 Alignment 的前提下，为每期真人视频生成可审查的完整视觉计划；用户可用自然语言调整本期素材、动画和真人出镜的偏好，并在看片后继续修订。

## Scope and invariants

- Persistent Default、Episode Override、Human Preview Revision 三层分离，优先级依次升高；只有明确“以后默认”才更新 Persistent Default。
- 用户只说自然语言。内部只使用 `low`、`balanced`、`high` 三档，不暴露比例、密度或渲染参数。
- Preference 只在多个已 grounded、已安全定位的选择之间改变编辑倾向；绝不能放宽 provenance、Material/Motion、display-text、Alignment 或 timing Gate。
- 当前 episode 的 resolved preference 为：overall/high、real-material/high、motion/high、A-roll/balanced。它不能写回 Persistent Default。
- B011 保持 needs_review；依赖其不确定 span 的机会保持 unplaced。B018 的 trailing ad-lib 默认 A-roll。
- Production、Bridge、Preview 均为新 revision；不覆盖 2026-08-21 的 Material、Production、Bridge 或 Preview。

## New artifacts

### Episode Visual Preference 1

`episode-visual-preference/1` 是不可变、可存储的 episode artifact，包含：

- `persistent_default`：由配置文件提供的长期平衡默认值；
- `episode_override`：本期自然语言要求及其解析后的四项 preference；
- `human_preview_revisions`：看片后的自然语言补丁；
- `resolved_preference`：按 revision/revision precedence 得出的当前有效值；
- 可选 `section_intents`：只保存自然语言和可安全识别的 Beat 范围，不猜时间。

Parser 只识别有限、可解释的中文意图：整体丰富/收一点、真实截图/文件更多或更少、动画更多或更少、真人更多或更少，以及“以后默认”的长期限定。未识别内容只保留原话为说明，不改变安全或事实状态。

### Post-Alignment Visual Plan 1

`post-alignment-visual-plan/1` 绑定 reviewed Script、approved Research、reviewed Material、Production QA-ready Motion、exact Alignment 和 Episode Visual Preference。它有两层：

- 18 个 Beat audit：每个 Beat 的实际 narration range、叙事用途、A-roll 理由、已有/缺失素材和 timing feasibility；
- opportunities：一个 Beat 可有多个 Material、Motion、Hybrid 或 A-roll opportunity。每项保存 semantic Script span、global correspondence 投影得到的 Transcript units/time、grounding、偏好决策理由、placement status 与 source binding。

只有 unique、monotonic、locally continuous 的 global correspondence 能创建 `ready` timing。没有安全映射的一律 `unplaced`；计划不能创建或修改 Alignment。

### Coverage Gate 1

Coverage Gate 从完整 Plan 重新推导，分别给出 Visual、Real Material、Motion 三个结果。它检查全部 Beat 是否审计、复杂机制是否被审计为 Motion、事实来源是否被审计为 Material、High preference 是否影响可安全选择、是否存在低价值/字幕式/装饰性视觉、A-roll-only 是否有理由、以及 ready timing 是否安全。

Coverage Gate 是计划质量 Gate，不替代 Material Review、Production QA 或 Edit Bridge canonical QA。

## Production and bridge integration

新 Production Plan 继续使用既有 renderer payload、display-text 与 Motion QA。它新增可选的 `episode_visual_preference_digest` 与 `post_alignment_visual_plan_digest` binding，旧 0.6.1 artifact 仍可读取。新 Post-Alignment builder 只把 Material Review-ready captures 和 Production QA-ready Motion 映射成 ready Placement。

Edit Bridge 的新 root bindings 同样绑定两个 digest。Canonical QA 重放 preference resolution、Visual Plan、Coverage Gate、Material view、Motion manifest、Placement timing、Bridge 与 Preview；任何 hand edit、错版 preference/plan 或 unready asset 都失败关闭。

## Current episode policy

当前 HIGH policy 会积极审计并在安全时采用：官方事件/技术说明、AISI、SAFE、NASA ASRS、SB-53 等原始页面或已登记 capture；以及攻击链、Agent trust boundary、事故报告、NASA 制度、SB-53 双时限和三层制度组合等解释型 Motion。它不设画面数量、时长比例或固定切换频率；Hook、观点、转折和结尾保留 A-roll breathing space。

## Preview revision UX

首次视觉规划前展示一次非阻塞提示：用户可直接说“素材多一点”“动画多一点”“多留真人”等。Human Preview 后再次提示用户可自然说“机制部分多做动画”“结尾多留真人”等；系统创建新的 Episode Preference、Visual Plan、Production、Bridge 和 Preview revision，不重新 ASR/Research/Script。

## Out of scope

不做 Script/Research/Fact Check 修改、Whisper 重跑、Alignment core/threshold 修改、字幕升级、A-roll cleanup、BGM/SFX、标题封面、发布、模仿任何创作者或 V1.0 Release。
