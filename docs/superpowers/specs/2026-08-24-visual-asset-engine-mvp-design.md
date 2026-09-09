# DeepTalk Visual Asset Engine MVP Design

**状态：设计草案，等待产品/架构 Review；未实现、未提交。**

## 1. 产品定位与不可违反的边界

Visual Asset Engine 的目标不是把一整期视频自动塞满动画，更不是替代剪映等剪辑软件。它在已经审核的内容和已经对齐的真人口播之间，挑出少量真正值得视觉化的时刻，交付独立素材包和普通人能用的剪辑表。

```text
reviewed Script + approved Research + reviewed Material
       + Clean A-roll + Timed Transcript + Script Alignment
                              │
                              ▼
                        Visual Director
                              │
       KEEP_A_ROLL / REAL_MATERIAL / MG_MOTION / ADVANCED_MOTION
                              │
                              ▼
                     Visual Plan Review（自然语言）
                              │
                              ▼
     Material / MG Spec / Advanced Motion Spec → Asset generation → QA
                              │
                              ▼
                     Asset Pack + Edit Map → 用户在 NLE 剪辑
```

以下原则是 MVP 的硬边界：

- **A-roll 优先。** `KEEP_A_ROLL` 是正常且重要的决策；没有高价值视觉时，不生成任何视觉。
- **真实时间优先。** 所有视觉机会的开始、结束、时长只来自通过 Gate 的 Script Alignment / Timed Transcript；Visual Director 不得估算、补齐或改写时间。
- **内容和事实优先。** Research、Fact Check 和 reviewed Script 是视觉的上游真值，视觉不得新增事实、改变结论或把 illustration 伪装成证据。
- **独立素材优先。** MVP 的交付是 MP4、真实素材、manifest 与 Edit Map；最终镜头取舍仍由用户在 NLE 决定。
- **无额外 API Key。** 核心路径只用结构化图形、SVG、HTML/CSS、现有本地 renderer、FFmpeg 和已合法取得的素材。生成视觉底图仅是将来的可选实验适配器。

## 2. 现有能力如何接入

| 现有模块 | 在新系统中的地位 | 本轮设计结论 |
| --- | --- | --- |
| Research / Fact Check / Script Review | 内容、事实和叙事唯一上游 | 复用；不允许 Visual Director 修改它们 |
| Material Package / Review / capture provenance | 真实素材候选与权利/来源边界 | 复用；只有现有 safe capture 可成为 `REAL_MATERIAL` |
| Timed Transcript / Script Alignment | 唯一时间真值 | 复用；无 safe alignment 一律不创建 ready visual window |
| Episode Visual Preference / Post-Alignment Visual Plan | 用户偏好、Beat 审计和当前视觉机会 | 后续演进为 Visual Director Plan；V1 读取兼容，不能手改旧计划 |
| Production Plan / scene_payload / Manifest / QA | 已有确定性 Motion 交付与审计链 | 复用并扩展，MG 与 Advanced Motion 共用 asset/QA 基线 |
| Edit Bridge | 技术 placement、Preview binding 和 canonical QA | 保留；V1 的人类交付由其上层 Edit Map 表达，不强迫自动粗剪 |
| 长片自动 Preview / Basic Subtitle | 已有能力 | 保留但暂时冻结为主要优化方向；不得作为本 MVP 成功标准 |

推荐 MVP 只新增契约、选择逻辑和用户可读的打包层；不新建第三套 renderer。确定性渲染优先复用当前 Remotion production 路线，HyperFrames 仍可作为未来同 payload 的 adapter 评测，但不是 MVP 的额外硬依赖。

## 3. Visual Director Contract 1

### 3.1 输入

`visual-director-input/1` 仅接受以下已验证根工件：

| 输入 | 必须满足 | 用途 |
| --- | --- | --- |
| reviewed Script + passing Script Review | 精确 revision、content digest 与 review linkage | 找到叙事 Beat 和原句，不创作新文案 |
| approved Research / Fact Check | 精确 revision、claims/evidence/timeline | 判断事实风险和 display/fact binding |
| reviewed Material Package + capture view | 重放通过，资产 SHA/eligible 状态有效 | 判断有没有可用真实素材 |
| Clean A-roll media / Timed Transcript / Script Alignment | 同一 media 与 alignment lineage；局部映射 unique、monotonic、continuous | 提供 source time range，绝不由 LLM 重估 |
| Episode Visual Preference + Human Preview Revisions | 当前 resolved preference | 只影响已安全选项之间的倾向 |
| 已 QA-ready Motion Manifest（如有） | 同一 Script/Research/Material lineage | 识别可复用的既有 Motion，不篡改 payload |

任何根缺失、digest 不一致、alignment 非 ready、素材不安全或旧 review linkage 无法重建时，Director 不输出 ready opportunity；它只记录 `KEEP_A_ROLL` 或明确 gap。

### 3.2 输出：Visual Director Plan

提议新增不可覆盖的 `visual-director-plan/1`。它是时间排序的视觉决策账本，不是 renderer 输入，也不是用户看的 JSON。

每个 `opportunity` 至少包含：

| 字段 | 合同 |
| --- | --- |
| `opportunity_id` / `beat_id` | Core 生成的稳定身份；用户界面不展示 |
| `source_time_range` | Decimal seconds + 可读 timecode；从 Alignment 投影，包含 `alignment_digest` 与 transcript unit span |
| `source_script_span` | reviewed Script 的 Beat / cue / 原句短锚点；不得重写正文 |
| `visual_intent` | 一个可理解的认知任务，例如“解释双时限为何不同” |
| `why_visual` | 说明为什么这段值得视觉或为什么应留真人 |
| `decision` | 严格枚举：`KEEP_A_ROLL`、`REAL_MATERIAL`、`MG_MOTION`、`ADVANCED_MOTION` |
| `importance` | `supporting`、`explanatory`、`turning_point`、`memory_point`；不是“动画密度” |
| `risk_flags` | factual/numeric/person/org/date/attribution/rights/display-text 等显式风险 |
| `review_requirement` | `not_needed`、`plan_review`、`advanced_spec_review`；规则而非模型自报 |
| `bindings` | Script/Research/Material/Alignment/Preference 的精确 ID、revision、digest 与局部 refs |
| `candidate_spec` | 仅对 MG 或 Advanced 指向经过验证的后续 Spec；不得嵌入自由事实文本 |
| `status` | `keep`、`proposed`、`approved`、`changes_requested`、`generated`、`qa_passed`、`fallback`、`not_used` |

排序键为 alignment-derived `source_time_range.start`，同一时间段不可并行强制占满。Director 可以在一个 Beat 中只输出 `KEEP_A_ROLL`，也可以输出一个真实素材和一个 Motion 的互斥候选，但必须写清 primary/alternative，不能把它们自动叠加。

### 3.3 决策规则

1. 没有安全、清晰且能提高理解的视觉理由 → `KEEP_A_ROLL`。
2. 已有经 Review 的真实截图、文件页或许可素材，且它本身能证明/帮助理解该句 → `REAL_MATERIAL`。
3. 该句是可参数化的机制、变化、关系或结构 → `MG_MOTION`。
4. 该句是全期少量认知高潮、反常识判断或抽象转折，并能被一个中性物理动作清晰表达 → `ADVANCED_MOTION`。
5. `KEEP_A_ROLL` 不是失败；装饰性、重复字幕式、风险过高或时间不可靠的机会必须留真人。

## 4. MG / Semantic Motion Grammar 1

MG 是 V1 的主力能力：以结构化数据与可审阅的文字 binding 生成高频、稳定、可复渲的解释镜头。不是“十个死模板”，而是统一的 `semantic intent → grammar → structure → primitives → timing → renderer requirements` 契约。

通用限制：16:9；通常 6–12 秒，最长 15 秒；一个镜头只承担一个主判断；屏幕中文不超过 2 个短标题 + 每个元素 8 个汉字或 20 个字符（超限 fail/degrade，不缩写事实）；全部显示文字须来自现有 Display Text Binding；默认不写长句/口播逐字字幕。

| Grammar | 适用语义与不适用情形 | 结构和 primitives | 限制 / 推荐时长 / 同步 |
| --- | --- | --- | --- |
| `timeline` | 历史变化、事件顺序；不用于不确定日期或密集年表 | baseline、ordered markers、focus sweep | 3–6 节点；6–12 秒；按 A-roll 的“先后”语义段依次出现 |
| `causal_chain` | A 推动 B 推动 C；不用于只是并列事实 | nodes、connectors、propagation、optional block | 2–5 节点；7–12 秒；节点先出现、连线后传播 |
| `comparison` | 已有稳定维度的两/三项对照；不用于假装两派阵营 | independent cards、dimension labels、focus switch | 2–3 items、每项最多 2 事实；8–12 秒；一次只强调一维 |
| `mechanism` | 规则、制度、工作机理；不用于需展示真实证据页的事实 | stages、container、trigger、outcome | 3–5 stage；8–15 秒；按触发→处理→结果 |
| `relationship_network` | 人/机构/系统责任或连接；不用于未经核实的关系 | nodes、typed edges、focus halo | 3–7 nodes、最多 8 edges；8–14 秒；先中心后关系 |
| `numeric_change` | 已经绑定的规模、比例、增减；不用于无独立数据的修辞数字 | numeral、scale、bar/area delta、annotation | 1–3 metrics；6–10 秒；值不动画为未绑定数值 |
| `state_transition` | 从状态 A 到 B；不用于连续多阶段系统 | before/after states、transition connector | 2 states；6–10 秒；A 建立→转变→B 稳定 |
| `old_model_new_model` | 某解释被另一解释替换；不用于把事实争议伪装为定论 | old structure、break/recede、new structure | 各 1 个模型；8–12 秒；必须标清是分析/解释而非事实 |
| `process_pipeline` | 输入、处理、输出、瓶颈；不用于复杂组织图 | input、stages、flow tokens、output | 3–6 stages；8–15 秒；token 沿单向管线走 |
| `hierarchy` | 层级、范围、从属关系；不用于有循环关系的网络 | levels、nesting、focus zoom | 2–4 levels、最多 8 nodes；7–12 秒；由上至下或由整体到局部 |

**V1 分批范围**：首批实现/真实验收为 `timeline`、`causal_chain`、`comparison`/`mechanism`、`relationship_network`、`numeric_change`；其余 `state_transition`、`old_model_new_model`、`process_pipeline`、`hierarchy` 已进入 V1 contract，但必须经独立小批次验证后才能列为 production-ready。这样不牺牲统一语法，也不一次性承诺十类实现。

MG 可以在 Visual Plan 已批准后自动生成，前提是：只使用结构化、已绑定数据；无高风险人物/事实展示；未超过 grammar capacity；无需生成视觉底图；当前 renderer profile 已生产认证。其余 MG 仍需 plan review，但不需要像 Advanced Motion 一样逐元素审阅。

## 5. Advanced Motion Spec 1

Advanced Motion 是低频的记忆点工具，V1 只允许：`svg_path_drawing`、`whiteboard_reveal`、`controlled_conceptual_metaphor`。每个 Spec 只能表达一个认知锚点，默认 8–20 秒，必须在渲染前先过人工 Review。

提议不可覆盖的 `advanced-motion-spec/1`：

| 字段组 | 必填内容与规则 |
| --- | --- |
| identity / roots | spec ID、Director opportunity、Script/Research/Material/Alignment digests、Spec revision；任何 root 改变都新 revision |
| source truth | `source_time_range`、`source_script_span`、`semantic_beats`、`timing_cues`；全部从 Alignment / reviewed Script 投影 |
| intent | `visual_intent`、`motion_type`、`duration`、`why_advanced_not_mg`；不能以“画面更丰富”为理由 |
| sequence | `element_sequence`：每个元素的角色、出现顺序、进入/停留/退出时间、使用的 primitive；一个元素只承载一个概念 |
| spatial safety | `protected_regions`、`allowed_masks`、`reveal_order`、safe area；保护区保证后续元素不会提前泄露，容量不足必须 fail/degrade |
| factual safety | `display_text_binding`、`fact_binding`、`source/provenance_binding`；姓名、机构、数字、日期、事实标签一律绑定，图片模型不得自由生成它们 |
| dependencies | 已有安全真实素材、结构化 SVG、许可图形、或可选的“已审阅、无事实文字”视觉底图；缺失即不可渲染 |
| renderer / QA | 指定现有 local deterministic renderer、期望帧率/尺寸、required checks、preview sampling、fallback chain |

允许掩码/保护区是机器数据，不是用户要编辑的技术参数。它吸收研究中“按叙事顺序揭示、后续元素不提前出现”的通用工程思想，但不复制任何参考作者的角色、画风、固定手部、构图或提示词。

## 6. Asset Manifest 与普通用户 Asset Pack

机器侧新增 `visual-asset-manifest/1`，聚合并引用每个已 QA 的真实素材、MG MP4 与 Advanced Motion MP4。每项保存 asset class、可读文件名、局部 time range、来源/Spec/Plan binding、dimensions/fps/duration、SHA、QA state、fallback provenance 和 Edit Map item ID。它只登记真实存在、通过 ffprobe/SHA/binding QA 的文件。

普通用户不需要看 manifest。每期在本地输出一个清晰目录：

```text
<episode-topic>/
  01_竞品参考/
  02_竞品转录与拆解/
  03_研究与证据/
  04_口播稿/
  05_真人口播/
  06_真实素材/
  07_MG动画/
  08_高级动画/
  09_剪辑表/
  10_成片/
  _DeepTalk记录/                 # manifest、QA、绑定；普通用户无需打开
```

不复制/重新分发无授权第三方视频；原始 A-roll 和私密转录继续处于项目外的受保护位置或本期用户目录，gitignore 保持有效。

## 7. Edit Map Contract

Edit Map 是 V1 的主要用户交付，分为同一内容的机器版和人类版：

- `edit-map/1.json`：根 digest、asset SHA、对齐 time range、placement mode、状态、fallback、QA 等机器字段；不得靠 Markdown 反向解析。
- `剪辑表.md` 与可导入 CSV：按真实 A-roll 时间排序，不显示 artifact ID、digest 或 renderer 参数。

每个普通用户条目采用如下固定表达：

```text
02:14–02:24
素材：电影票变成互联网入场券.mp4
建议：全屏使用约 9 秒
用途：本段核心认知转折
为什么：把“电影消费”正在变成“互联网事件参与资格”这一判断视觉化
备选：如果觉得太花，保留真人；不要使用无关素材替代。
```

条目还可用自然语言标记“真人主画面 + 右下角资料”“先真人后全屏 MG”“只作为 2 秒补充”。只有 `qa_passed` 的 asset 才会出现在推荐使用列表；未就绪项只出现在“暂不建议使用”，绝不伪装成可拖入剪映的素材。

## 8. Human Review UX

用户看到的是按时间排序的少量视觉建议卡，而不是 JSON：

```text
02:14–02:24｜建议：概念隐喻动画
核心意思：电影消费正在变成互联网事件参与资格。
画面：电影票进入转换装置，另一侧成为“参与资格”，再出现讨论元素。
出现顺序：电影票 → 转换 → 参与资格 → 讨论元素。
原因：这是本段认知转折，单靠真人可能不够直观。
```

用户可以回复“可以”“这段不要动画”“这里改成 MG”“素材多一点”“多留真人”“这个太花了”。解释器只能在已显示的卡片和已安全的决策范围内解析；指代不清时必须请求用户指出时间或卡片，不得猜测。每次反馈创建新的 preference/plan/spec revision，不改 Script、Research、Transcript、Alignment 或历史资产。

## 9. Gates 与状态机

| Gate | 进入条件 | 通过条件 | 失败动作 |
| --- | --- | --- | --- |
| G1 Script / Research | reviewed Script、approved Research、passing review linkage | 所有根 digest/revision 可重建 | 停止；返回上游，不从视觉层改文案 |
| G2 A-roll Alignment | Clean A-roll、Transcript、Alignment | 机会有 unique/monotonic/continuous local range | 该机会 `KEEP_A_ROLL` / `unplaced`，不得猜时间 |
| G3 Visual Plan Review | Director Plan 已通过 machine validation | 用户自然语言确认本期视觉方向；低风险 MG 可在已确认 plan 内批量生成 | `changes_requested` 创建新 Plan；不渲染 Advanced |
| G4 Advanced Motion Spec Review | `ADVANCED_MOTION` + validated spec | 用户确认视觉意图、出现顺序和是否值得做 | 降级 MG / real material / A-roll |
| G5 Asset QA | renderer 输出真实文件 | ffprobe、SHA、尺寸/时长、binding、display/fact text、视觉/安全 QA 全通过 | asset 不进入 Edit Map，执行 fallback |
| G6 Edit Map Finalization | 已 QA asset + human-readable recommendations | Map/CSV/manifest binding 一致，用户能看懂如何使用 | 只保留可用条目，其他标为不建议使用 |

状态机：`prerequisites_pending → alignment_ready → visual_plan_proposed → visual_plan_approved → (mg_generating | advanced_spec_review) → asset_qa → edit_map_ready → user_nle_editing`。任意失败走 `fallback`，创建新 revision；历史 plan/spec/asset 不覆盖。

## 10. Failure / Fallback Matrix

| 失败或不适合情况 | 必须采取的降级 |
| --- | --- |
| Alignment 没有安全局部时间 | `KEEP_A_ROLL`；不猜 timing |
| 真实素材无 safe capture、SHA 不符或来源/权利不满足 | 有结构化已绑定数据时 MG；否则 `KEEP_A_ROLL` |
| MG 数据太多、文字超容量或语义并非结构化机制 | `REAL_MATERIAL` 或 `KEEP_A_ROLL`，不压缩/改写事实 |
| Advanced Spec 未获用户确认 | 不渲染；降级 MG、真实素材或真人 |
| Advanced 视觉底图缺失、不合格或产生事实/中文风险 | 仅保留程序化/SVG 子集；不调用付费 API 作为救火手段 |
| Renderer、ffprobe、binding 或视觉 QA 失败 | asset 标记 failed；回到已有 approved fallback，绝不进入 Edit Map |
| 用户说“太花/多留真人” | 新 Visual Plan revision，优先切换为 `KEEP_A_ROLL`，不修改上游事实 |

## 11. V1 / Later Scope Matrix

| V1 MVP | Later / Experimental | 明确不做 |
| --- | --- | --- |
| Visual Director 四选一、自然语言 Review、Asset Pack、Edit Map、G1–G6、五类首批 MG、三个受控 Advanced 类型 | 可选视觉底图 generator adapter、其余 MG grammar、同 payload 的 HyperFrames adapter、更多 NLE 导出格式 | 自动十分钟整片、复杂角色表演、逐帧动画、商业级 3D、高复杂 2.5D、视频模型驱动整链、自动上传发布 |

Optional/Experimental Visual Generator 将来只能位于 `Advanced Motion Spec.dependencies` 的“无事实文字视觉底图”插槽；其输出永远先过独立图像 QA，失败不会阻塞核心 MG/真实素材/A-roll 路径，也不会要求用户设置 API Key。

## 12. 第一条真实 episode 验收

使用一份真实精品 reviewed Script、approved Research 和用户真实 Clean A-roll；不以“整片自动成片”作为成功标准。

1. 先过 G1/G2，产出完整 Visual Director Plan，并由用户用自然语言确认。
2. 只挑少量高价值机会：至少 3 个不同 MG、1 个 `svg_path_drawing`、1 个 `controlled_conceptual_metaphor`；白板 reveal 可作为 path 的变体或下一小批。
3. 每项独立产出 MP4，执行 G5；不合格项按 fallback 留真人。
4. 输出 Asset Pack 和 Edit Map；用户在剪映实际拖入、比较并决定是否使用。
5. 验收必须同时满足：无 blocking provenance/binding/QA 问题；时间范围可用；用户能理解剪辑表；用户实际愿意使用至少一部分素材，并认为它提升成片质量或明显降低素材制作成本。

技术 render 成功不是产品成功。若用户不愿在剪映使用，即使 QA 全绿也应作为产品失败信号进入下一轮设计。

## 13. 仍需产品经理确认的事项

1. V1 首批真实验收是否以“5 个高价值素材”为固定上限，避免视觉过密。
2. 频道的中性默认视觉风格是否先使用“现代、克制、高对比、非角色 IP”，待真实用户审美反馈后再固化 Style Profile。
3. G3 是否要求每期对所有视觉机会一次确认，或仅对 Advanced/高风险条目强制确认；本设计推荐前者的首期体验、后者的成熟期体验。
4. Edit Map 的首批用户格式推荐 Markdown + CSV；是否需要特定 NLE 的项目文件导出，留到 Later。
