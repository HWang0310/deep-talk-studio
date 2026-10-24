# Issue #29 — 选题驱动创作：一句话任务 → 主动检索 → 起步产出（topic-first）

> **状态：READY_FOR_NEXUS_MVP_REREVIEW。** 按 Nexus 派工 issuecomment-6369945828 完成：用户输入「我想就王扁被打做个视频」这类明确任务意图时，不再用一组泛泛的基础问题反问用户，而是确定性识别任务 → 有界检索公开来源（免费 B 站匿名通道）→ 透明播报检索状态 → 把证据注入模型上下文 → 直接产出事件速览（已证实/未证实严格区分）+ 2-3 个可辩护角度 + 工作标题/大纲 → 「整理为草稿」生成可自由编辑的未审核草稿。正式审核门禁（Research/Fact Check/Thesis/Reviewed Script/Rights/Production Gates）全部保持 fail-closed，free draft 永不自动晋级。PR 保持打开，未合并。

## 需求与验收对照（Nexus 六点）

1. **区分「聊聊」与「我想做个视频」强任务意图**：`WorkbenchFlow._video_task_topic` 纯确定性关键词匹配（零模型调用）——命中任务标记（做个视频/做一期/拍个视频等）且能提取主题才进入任务流程；聊聊模式（无标记）与无主题任务（如「做个视频」）绝不硬造主题，真实模糊处才反问。
2. **直接给出有用产出**：事件速览（时间线+来源 URL+来源谱系、已证实 vs 未证实）+ 2-3 个可辩护角度 + 工作标题/大纲 + 可自由编辑的 Creative Draft；不逐字抄袭。
3. **诚实工具能力**：真实 B 站匿名检索（免费、产品既有 stage-1 同通道）在流式开始前跑一次有界检索并给透明来源证据；检索不可用/未接线/无结果一律记录 `status: unavailable`，UI 与模型两侧都如实声明「未联网核实」，绝不默默假装做过研究；检索永不阻断消息发送。
4. **渐进工作流不变**：topic → discovery/source notes → angle/storyline → 原创口播稿 → reviewed formal script（需独立核查 + Owner 显式批准）→ Owner 最终口播 → alignment + materials/edit map → Owner 剪辑发布。草稿永远 `creative-draft/1` / `unreviewed`，不写任何 approved/reviewed/quality-Gate 字段。
5. **验收案例实测通过**：输入 `我想就王扁被打做个视频` → 识别事件（基于检索证据的时间线，10-18 至 10-22 条目级来源）、引用来源链接（B 站条目 URL）、不编造警方/伤情/动机结论（「前经纪人」「爆头」「反转」「出院」全部标注未证实/待核实）、给出具体可编辑 storyline/draft、无四问泛问、结尾给清晰的下一步授权/批准门禁提示。
6. **测试**：CI 用确定性离线来源夹具（14 个新测试）；浏览器验收两级——8323 隔离夹具（离线 fixture 检索 + 8932 mock LLM，零真实调用零付费）+ 8321 真实环境（真实 B 站匿名检索免费 + Owner Key 真实 DeepSeek 调用 2 次聊天+1 次草稿=2 次，在单轮 ≤8 次授权先例内）；用户级设置/聊天历史不受影响（快照 + state 双确认）。

## 设计决策

- **确定性意图识别**：检索预算只花在明确的任务意图上；识别不依赖模型判断（识别在检索之前、检索在任何流式输出之前）。主题提取支持书名号/前后缀套话剥除（14 个提取用例），40 字截断。
- **会话级证据幂等**：`CreativeChatStore.set_discovery` 锁内 check-and-set——会话内**首个**任务 turn 的检索证据一次性持久化（首写胜出，绝不覆盖、绝不重检），刷新精确恢复；后续任务 turn 复用同一份证据，零重复网络请求。
- **证据跟随触发 turn**：聊天回复只在 `discovery.turn_id == 本条 user turn` 时播报 search 事件并注入证据（`【主动检索来源】` system 上下文：逐条标题/UP主/发布/链接/简介 + 「不是权威事实核查」谱系声明 + 「无来源支持的细节绝不能写成事实」规则）；草稿生成注入会话级证据（与聊天同源），`DRAFT_SYSTEM_PROMPT` 补充「末尾附参考来源行」规则。
- **三层诚实降级**：检索成功有结果 → 透明来源 + 谱系声明；检索回调异常/不可用/无结果 → `unavailable` + 原因 note；未接线检索（`topic_search=None`，如测试默认 flow）→ 同样记录 `unavailable`（「本环境未接入公开来源检索服务」）。三种情况模型都拿到明确指令，绝不把未核实内容写成事实。
- **接线边界**：`run_webui`（真实 UI）默认接线真实 B 竿检索适配器 `_default_topic_search`；`make_server(flow=None)` 不接线——测试/演示环境自行注入确定性夹具，绝不隐式发起网络请求。
- **SSE 透传**：`chat_stream_reply` 在任何 delta 之前 yield `{"type": "search", query, status, count}`；前端 `appendSearchNoteEl` 渲染 muted 小字行（`🔎 已主动检索公开来源「query」：N 条（B 站匿名检索，非权威事实核查）` / 不可用时如实声明未联网核实）；`renderChat` 刷新后按 `topic_discovery.turn_id` 在对应 user turn 后精确重渲染，不丢。

## 测试

- 新增 14 项确定性测试（全部离线零网络零付费）：意图/主题提取 10 用例、任务触发有界检索+证据注入+search 事件先于 delta、会话内幂等（不重检不重播报）、聊聊模式零检索零注入、未接线 unavailable 诚实声明、回调异常不阻断发送、空结果 unavailable、草稿生成注入证据、discovery 刷新精确恢复、store 层首写胜出幂等、HTTP SSE search 事件透传+state 恢复、webui 适配器映射（ok/blocked/空结果）、前端静态契约（search 分支/小字行样式/topic_discovery 恢复/未联网核实文案）。
- focused **159 passed**（145 既有零回归 + 14 新增）；全量 **1139 passed, 7 skipped**（main 集成基线 1125 + 14）。
- Post-merge main 集成 QA（先行完成）：全量 **1125 passed, 7 skipped**；8321 重启加载 main 后 masked Key `sk-f…8d17`、3 个 Owner 会话（4/2/12 turns + 3 drafts）完好；真实 `~/.deeptalk` 快照 sha256 前后一致。

## 浏览器证据

见 `browser-evidence.md`；截图 `screenshots/issue29-01…05`（01–03 = 8323 夹具：任务回复/草稿生成/刷新恢复；04–05 = 8321 真实环境：真实检索+起步产出/真实草稿）。
