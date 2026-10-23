# Changelog

## Unreleased — 2026-10-23 — Issue #44 — Owner UX：一体化对话工作区 + 8321 运行时修复 + Owner Key 持久化验证 + 限额真实模型端到端（issuecomment-6364369899）

- **一体化聊天工作区（Owner UX 验收契约 1–6 逐项）**：移除「顶部巨型 hero + 下方独立对话面板」的双区结构，改为 ChatGPT/Claude Code 式单一连续工作区——空态为安静居中欢迎（`#welcome-pane`：标记 + 标题 + 一句计费说明 + 灵感 chips，设置在右上角）+ 贴底 composer（`#composer-dock`，sticky bottom）；首次发送后 welcome 隐藏，user/assistant turns 与草稿卡/旧集折叠入口（`#conversation`）共享同一滚动流，composer 始终贴在视口底部，后续消息在同一输入框键入，绝不需要滚回顶部。滚动跟随策略：新消息（显式发送）滚到最新，流式增量只在用户靠近底部（`nearBottom()`，90px 阈值）时跟随，向上翻阅历史不被强行拉回，实测 scrollY 37 保持顶部、回到底部恢复跟随。空态内容不足一屏时由 `fitCreatorHeight()` 按实测顶栏高度撑满视口使 composer 恰好贴底（不猜测 header 高度，resize 重算）。
- **失败不丢输入 + 服务版本真实指引**：发送失败/400/404 时未发送内容恢复到输入框并回写 localStorage 草稿；错误信息含 404/「路径不存在」时如实提示「本机服务可能是旧版本，请重启本地服务后刷新页面」，绝无乐观假「已发送」。
- **草稿集成紧凑化**：草稿卡保留在同一对话流内（turns 之后），「草稿与正式审核的关系」长说明收进默认收起的 `<details class="gate-details">`；不可变 revisions/编辑/复制/导出/「未审核」诚实来源标注全部保留。旧集正式工作流折叠入口移出对话流、独立显示（无聊天时也可访问），B1 防护不变。
- **8321 运行时故障修复（mutation 前 same-process 路由验证）**：Owner 遇到 `POST /api/workbench/chat/stream` 返回 JSON 404「路径不存在」——根因是 LaunchAgent 8321 进程（pid 19938，17:28 启动）加载的是 chat MVP 落地**之前**的陈旧代码（`scripts/deeptalk` 的 `PYTHONPATH=src` 模块解析本身正确，无需诊断模型问题）；`launchctl kickstart -k` 重启后同进程验证：空消息返回 400「消息内容不能为空」（路由存在、零模型调用），服务器日志中 Owner 的 4 次 404 均为旧进程产物。
- **Owner DeepSeek API Key 持久化（已验证，零重新输入）**：`config/workbench.local.json` 被仓库 `.gitignore:43` 覆盖（git 操作/分支切换/升级不动该文件），8321 重启后掩码 `sk-f…8d17` 完整保留、`/api/workbench/state` 仅暴露掩码字段（无明文 Key）、设置页徽章「已连接」（官方端点 + deepseek-flash）；浏览器截图/日志/提交零密钥泄漏（diff 扫描过）。
- **限额真实模型端到端（Owner 授权，产品内使用 Owner Key，共 5 次 ≤ 8 上限）**：真实流式聊天（2.6s，「deepseek-flash · 真实模型回复」诚实标注）→ 带完整上下文 follow-up（2.4s）→ 真实草稿生成（3.9s，meta「真实模型回复」）→ 本地编辑两次 v2/v3（零调用）→ 刷新精确恢复（6 turns + v1/v2/v3 + 编辑内容）→ 真实 stop（计费诚实文案 + 半截清除）→ 幂等 retry（5.8s 完整 60 秒口播稿，turns 5→6 只增 assistant）→ 设置往返（「已连接」徽章、返回创作零丢失）。服务器日志精确计数：stream 200 ×4 + draft 200 ×1 = **5 次真实模型调用**；404 ×4（旧进程）、400 ×1（空消息校验）均为零调用；本地编辑 2 次零调用。夹具测试不作为真实模型 PASS 依据，本轮为产品内真实调用。
- **375px 移动端**：横向溢出 0px、composer 全宽适配视口且不被安全区遮挡、最后一条 turn 不被 composer 遮挡、无需回顶即可继续输入。
- 测试：静态断言按新结构更新（welcome-pane/conversation/composer-dock/sticky/nearBottom/updateWelcomeVisibility/失败恢复/版本指引）；focused 136 passed；全量见对应轮记录；8322 夹具验收 + 8321 真实模型验收截图 25–32（新旧布局对比：19 为旧 hero+双区结构、25 为新一体化空态）。

## Unreleased — 2026-10-23 — Issue #44 — B2/P0 修正：重叠消息拒绝先于持久化（Nexus exact-head review #5627594838）

- **修复 mutation-before-rejection**：`_handle_chat_stream` 的单飞准入检查+预约（`chat_in_flight`）前移到任何 `chat_send_start` 存储变更**之前**——此前重叠的 B 消息会先被持久化再收到 400，留下 `[user A, user B(被拒), assistant A]` 污染会话与后续模型上下文。预约检查+注册在 `chat_flight_lock` 内原子完成（check-and-reserve race-safe），并发首次发送（尚无会话）与稳态重叠同路径覆盖；flight key 改为固定 `"chat"`（聊天为单会话设计，不依赖 `chat_send_start` 结果）；预约在所有失败/断开路径（含 `chat_send_start` 抛错）经 finally 释放；等待模型期间不持有任何全局锁；retry-by-turn-ID 与 Key/空消息防护不变。
- **确定性 HTTP 回归**（按 review 四步要求增强/新增）：① A 慢流提交 user A 保持进行；② B 重叠发送 → 400，A 运行期间存储恰 `[user A]` 且 B 内容零出现、零模型调用；③ A 完成 → 存储恰 `[user A, assistant A]`，B 仍零出现；④ 预约释放后 C 正常发送照常可行（A+C 各一次显式调用）。新增并发首发测试：Barrier 对齐两线程同时首次发送 → 恰一个 200 一个 400，存储只有被放行方一问一答，被拒方不创建会话不写 turn。
- 8322 真实 HTTP 实测：15 条基线完整保留，B 在 mid/final 存储双检零出现，新增恰一问一答，8931 mock 调用恰 +1（B 零调用）。
- 测试：focused **136 passed**（+1 并发首发用例、单飞用例增强为四步回归）；全量见对应轮记录。

## Unreleased — 2026-10-23 — Issue #44 — Nexus B1–B4 阻断修复（Chat-first MVP delta review #5626927896）

- **B1 旧集工作流与聊天首页明确分离**：hero 永远是首页主体；即使存在历史 canonical 会话，其 stage-bar/参考/授权表单/候选也默认隐藏，只在新增的 `<details id="legacy-workbench-entry">` 折叠入口（「查看既有正式工作流（与聊天相互独立）· 本集：<主题>」）显式展开时才渲染；无会话/新一集模式下折叠入口同样隐藏；legacy sessions 一律保留不删除。8322 隔离夹具（旭日旗旧集 + 图书馆聊天共存）浏览器验证：默认态文本节点级零泄漏（leakCount=0），展开渲染/收起隐藏双向正确。
- **B2 陈旧快照写入防护（数据不丢）**：`CreativeChatStore` 全部跨请求持久化改为存储锁内 re-load 最新会话后追加（`start_user_turn`/`retry_user_turn`/`append_assistant_turn`/`append_draft_latest`/`latest_session_id`），绝不把内存旧快照整体写回；webui 层增加同会话单飞（`chat_in_flight`，重叠发送 400「上一条回复还在进行中」，finally 释放），等待模型期间不持有任何全局锁。交错场景（A、B 两个流式以任意顺序完成）与「流式中并发草稿编辑」均验证零丢失。
- **B3 重发幂等 + 计费诚实**：停止后的「重发上一条」携带服务器持久化的 `retry_turn_id`，后端 `retry_user_turn` 验证目标仍是「最后一条且无回复」的 user turn 后原样复用，绝不追加重复用户消息（前端也不再本地重复渲染 user 气泡，并清除停止遗留的半截 streaming 气泡）；已有回复/ID 不匹配一律拒绝且零模型调用。停止文案改为诚实表述「已停止显示并尝试中断模型请求；已产生的费用可能仍会计入账单。」（`llm.py` 注释同步），删除不可能的「不会继续计费」承诺；重发按钮只在「上一条未完成」（停止/失败/中断）时出现。8322 实测停止→重发：12→13 只增加 assistant 气泡、存储中该 user 消息仅一条、mock 调用恰两次显式流式零隐藏。
- **B4 草稿来源标注持久化**：`provider_kind` 在 `append_draft` 的 revision JSON 内原子持久化（此前只在内存 `draft["provider_kind"]` 赋值、重载即丢）；8322 新生成 v4 重载后 `provider_kind="fixture"` 保留，历史草稿不做迁移。
- **修复本轮引入的回归**：webui 服务器 `__init__` 曾被批量编辑误删 `output_dir`/`provider_factory`/`discovery_lock`/`workbench_lock` 四行导致 discover/workbench 路由 500，已恢复并保持 B2 单飞字段；静态断言中旧停止文案同步更新为新契约。
- 测试：新增 flow 级 5 项（交错完成零丢失/流式中并发草稿编辑不覆盖/停止后幂等重发无重复/已回复或未知 ID 拒绝/草稿 provider_kind 重载保留）+ HTTP 级 2 项（在飞流单飞 400/断开后带 retry_turn_id 重发一问一答）+ B1 静态断言 1 项；focused 135 passed；全量见对应轮记录；8322 真实 Chromium 浏览器验收（B1 默认/展开/收起、B3 停止/重发、B4 新草稿重载、375px）；截图 19–22 按当前行为重拍，新增 23（legacy 展开）/24（停止计费诚实）。零付费调用、无 Owner Key、不自行合并。

## Unreleased — 2026-10-23 — Issue #44 — Chat-first Creative Draft MVP（Owner 批准 Option A, issuecomment-6361415259）

- P0 设置加固（先行落地）：`provider_mode=deepseek` 服务端无条件锁定官方端点/模型，丢弃残留 custom 值（显式提交旧端点同样被覆盖），新粘贴 Key 绝不路由到旧自定义端点；前端切换无条件重置隐藏字段；「测试连接」在飞防抖（连点仅一对请求）；官方文档确认 `deepseek-flash` + `stream:true` SSE。
- 真实流式聊天：`POST /api/workbench/chat/stream`（SSE start/delta/done/error），上游 `stream:true`、浏览器 ReadableStream 增量渲染、AbortController 停止；user turn 流前持久化、assistant turn 流完成才写入——停止/断开不保存半截回复、重连不重复调用；重试为显式动作；输入/刷新零隐式请求。
- `creative-chat/1` 会话存储：`workbench/chat/*.json` 0600 权限、无秘密、不可变 turns；`/state` 携带完整会话实现刷新精确恢复。
- `creative-draft/1` 原创草稿（未审核）：显式生成（付费动作）+ 自由编辑产生不可变 revisions（v1/v2/v3 回看）+ 复制/导出 .md；永不写 `research/thesis/script` 的 approved/reviewed 路径或质量门禁字段，不解锁正式生产；「进入正式审核」说明卡解释现有门禁路径，无自动转换；canonical 门禁测试保持 fail-closed。
- Chat-first 首页：单一自然语言 composer（选题/观点/请求/粘贴 URL → link chips 如实「未读取」）、夹具/真实诚实标注（loopback 即夹具，绝不冒充）、计费说明一次性常驻；仅两个顶级页面（聊天 + /settings）；旧 canonical 阶段工作流对既有会话仍可达，门禁不变。
- 测试：新增 flow 层 8 项（流式持久化/停止不写半截/未配置阻断/草稿修订不可变/门禁隔离/0600 权限/无秘密/loopback 标注）+ HTTP SSE 3 项（事件契约/恢复/客户端断开）+ 静态断言；focused 127 passed、全量 pytest 见对应轮记录；8322 真实 SSE 夹具浏览器验收（增量实测、停止/重发、两次草稿修改、刷新精确恢复、375px、无 Key 泄漏）；零付费调用、无 Owner Key、不自行合并。

## Unreleased — 2026-10-23 — Issue #44 — paste→Test 旅程修复（Nexus delta, issuecomment-6358124584）

- 「测试连接」点击后先安全持久化当前表单（含刚粘贴的 API Key，POST JSON 走本机 loopback），保存成功后才对刚保存的配置执行连接测试；保存失败立即停止并显示中文错误（含「未连接测试」），绝不发出测试请求。保存与测试共用 `settingsFormPayload()` / `persistSettings()`，消除保存/测试双路径不一致。
- 已输入 vs 已持久化：输入框粘贴新 Key 时徽章即时「已输入未保存」（琥珀色 state-warn），不再误导显示「未配置」；清空输入恢复持久化徽章；保留「空 Key 保持已存 Key」与显式「清除 API Key」语义，夹具仍为「开发测试环境」徽章，仅显式点击才发起测试，零付费调用。
- 证据：8322 隔离夹具实测请求顺序「先保存（含新 Key）→ 再测试」、掩码 `sk-p…ey-2` 持久化、开发测试状态诚实；8321 真实配置实测保存先行 + 测试请求中止（零外部调用）+ 重载掩码持久化 + 保存失败（HTTP 500）阻断测试；截图 17/18；`tests.test_webui` + `tests.test_workbench` 113/113、全量 pytest 见对应轮记录；diff 无密钥，真实 DeepSeek 连接质量仍为 `WAITING_FOR_OWNER_API_KEY`，不自行合并。

## Unreleased — 2026-10-23 — Issue #44 — DeepSeek 设置体验：只需填 API Key + 诚实开发夹具标注

- DeepSeek 默认模式下普通用户只需填写 API Key：模型与官方 API 地址自动配置（说明行「模型与官方 API 地址已自动配置（deepseek-flash），只需填写 API Key」），模型名称与 API 地址字段仅在切换其他服务商时出现。
- 测试连接文案自然语言化：未填 Key 提示「设置尚未完成：请填写API Key后保存，再点「测试连接」」，后端两处用户可见消息不再暴露 `WAITING_FOR_OWNER_API_KEY`（机器状态 `waiting_for_api_key` 等仍完整保留在 API payload，契约不变）。
- 开发夹具诚实标注：指向本地测试服务的连接显示独立「开发测试环境」琥珀徽章与「开发测试连接通过：这是本地测试服务，不代表真实的 DeepSeek 连接。」文案，绝不冒充「已连接」；移除「（本地服务）」「（模拟服务）」后缀与底部端点显示；修复模式切换提示 `openai`→`responses` 的错误分支。
- 设置页视觉打磨（评审反馈逐项落地）：未配置徽章改琥珀警示色；徽章提示与自动配置说明去重；说明行括号内只保留模型名；按钮行重排为「取消/测试连接/清除 API Key 靠左、保存设置靠右」；状态文字与保存按钮间距加大；连接状态行 `word-break: keep-all` 防止「模型」等中文标签被拆到两行（375px 实测修复）。
- Key 占位符窄屏自适应：桌面为「粘贴你的 DeepSeek API Key」，窄屏 canvas 实测放不下（190px > 输入框内宽 168px）时自动降级为「粘贴你的 API Key」，resize 双向切换，避免占位符截断。
- 配置隔离：真实 `config/workbench.local.json` 重置为 DeepSeek 官方默认（无 Key）；mock 配置仅存在于 8322 隔离演示环境独立根目录。
- 证据：`evaluations/issue44_minimal_ux/` 新增/重拍截图 12–16（含 03/04 按新行为重拍），`tests.test_webui` + `tests.test_workbench` 112/112、全量 pytest 见对应轮记录；浏览器实测掩码替换、`launchctl` 重启恢复、清除回未配置；图像评审三次误报（按钮换行、deepseek-flash 断行、桌面占位符截断）均用 Range/canvas 确定性测量推翻并记录。真实 DeepSeek 连接质量仍为 `WAITING_FOR_OWNER_API_KEY`，零付费调用，不自行合并。

## Unreleased — 2026-10-22 — Issue #44 — 两页极简 UX：创作页 + 独立大模型设置页

- 创作页收敛为极简两态：全新状态只有大选题输入 + `开始创作`；开集后是阶段条（本集主题 + `＋ 新一集`）与 `① 视频参考 / ② 观点与资料 / ③ 原创口播稿` 三个概念阶段，一次只渲染当前阶段，随时回看不丢会话；无侧边栏、无六步仪表盘。
- 参考视频改为一页短卡片（标题两行截断、已核验播放、状态徽章），BVID/时间戳/转写/叙事分析收进详情折叠；授权声明与部分分析理由保留在动作现场；音频与素材仅在口播稿审核通过后经 `继续做音频与素材` 成为可选阶段。
- 新增独立 `大模型设置` 页（`/settings` 路由 + pushState 单文档切换）：服务商（DeepSeek 默认）、模型名称、掩码 API Key、保存与测试连接为主字段；连接状态徽章如实分级 `未配置/已保存未验证/已连接/连接失败/模拟服务` 并自动标注本地端点；服务端点藏进高级设置、下载位置独立折叠；`← 返回创作` 保留选题草稿（localStorage）与会话进度。
- 修复 Nexus B1/B2：`＋ 新一集` 进入独立空白创作态，阶段条和旧阶段全部隐藏，取消后可恢复上一集；进入新会话时清空旧文稿 DOM，定稿异步请求绑定 session/script/revision，旧响应不能写入新会话。
- 修复 Nexus B3：离线演示来源统一使用主题一致的五条材料，页面显示固定“离线演示夹具”免责声明；设置页 API 地址标签随服务商同步，避免通用 Chat 连接显示为 DeepSeek 端点。
- 视觉证据见 `evaluations/issue44_minimal_ux/`（真实 Playwright Chromium 桌面/375px 截图与 B1/B2 浏览器断言）；`tests.test_webui` + `tests.test_workbench` 109/109、全量 pytest 1089 pass / 7 skipped；LLM 为本地诚实 fixture，零付费调用，真实 DeepSeek 质量仍为 `WAITING_FOR_OWNER_API_KEY`。

## Unreleased — 2026-10-22 — Issue #38 — Creator Workbench 离线浏览器验收

- 增加 `evaluations/issue38_workbench/fixture_server.py` 与可重复的 `smoke_playwright.py`：仅使用 loopback 离线夹具，验证设置掩码、五条参考候选、音频二进制导入/预览、`WAITING_FOR_OWNER_REVIEW`、刷新恢复、Tab 键可达、375px 无横向溢出与健康检查；fixture 状态不会冒充真实模型或真实 Bilibili 结果。
- 修复创建会话后 `/api/workbench/session/start` 返回不完整状态导致设置区清空的问题；响应现在保留掩码设置与会话状态。长 SHA/本地路径状态文案支持断词，避免移动端横向滚动。
- 证据截图保存在 `evaluations/issue38_workbench/screenshots/`（运行时副本在 `output/playwright/`）。`tests.test_workbench` + `tests.test_webui` 101/101、`tests.test_audio_only_delivery` 18/18、`tests.test_deepseek_tools` 4/4；全量 `unittest discover -s tests` 1088 pass、7 skipped。
- 本轮没有调用 DeepSeek/Search/Fetch 或其他付费模型，没有上传 Owner 私人音频；真实模型创作质量、Owner API Key、版权/审核决定仍为 **UNVERIFIED / WAITING**。

## Unreleased — 2026-10-22 — Issue #37 — local audio timeline and Edit Map delivery

- Added a bounded, atomic local narration import for WAV/MP3/M4A/AAC/FLAC/MP4/MOV/M4V. Each session records the declared origin, byte size, SHA-256 and import status without overwriting existing files or following traversal/symlink targets.
- Added a real delivery action that delegates to the existing local ASR/alignment and audio-only Asset Pack/Edit Map chain. Missing reviewed Production/Material inputs remain an explicit `WAITING_FOR_OWNER_REVIEW`; injected deterministic runners are labeled `fixture` and never presented as real delivery.
- The loopback UI now shows resumable import/delivery status, timeline spans, `AUDIO_ONLY`/`VISUAL_GAP` gaps, QA state and allow-listed session-local artifact download links. No human frame, finished cut or automatic NLE edit is fabricated.
- Tests: focused audio/workbench/WebUI regressions 5/5; existing `tests.test_audio_only_delivery` 18/18. Browser smoke and full-suite evidence will be recorded under Issue #38; no real ASR/model API or paid DeepSeek call was used in this phase.

## Unreleased — 2026-10-22 — Issue #36 — opt-in DeepSeek Search/Fetch sources

- Added a dependency-free DeepSeek Search/Fetch client using the official tool paths with typed, secret-free HTTP/timeout/response errors; all tests use injected offline transports and no paid request was made.
- Search and Fetch are separate explicit UI actions. Each session persists an opt-in latch, a monotonic 1–20 request cap, redacted request provenance, and resumable search candidates; cap exhaustion and missing `WAITING_FOR_OWNER_API_KEY` configuration fail closed.
- Only an explicitly fetched result becomes a `deepseek_fetched` research source, carrying request ID, retrieval time, publication metadata, method/status, and SHA-256. Search snippets remain discovery-only and are never treated as evidence; existing manual URL/paste sources are unchanged.
- Tests: DeepSeek client + Workbench/WebUI focused regressions 8/8; full Workbench/WebUI suite 95/95. Real DeepSeek Search/Fetch was not called.

## Unreleased — 2026-10-22 — Issue #35 — resumable reference transcription and analysis

- Authorized acquisition failures and model-analysis failures now survive reloads with attempt/error provenance; failed or `unverified` references remain in the readiness denominator and cannot silently count as analyzed.
- Local transcript artifacts retain segment timestamps, SHA/model/runtime provenance, and a visible transcript preview. LLM-unavailable studies are explicitly `unverified`; the UI offers a re-analysis retry that reuses the saved transcript without another download or ASR run.
- Tests: `tests.test_workbench` + `tests.test_webui` 90/90 pass, including restart persistence and outage→retry regressions. No real model call was made; real-model acceptance remains `WAITING_FOR_OWNER_API_KEY`.

## Unreleased — 2026-10-22 — Issue #34 — first-class DeepSeek settings

- Added a named DeepSeek preset (`https://api.deepseek.com`, `deepseek-flash`) with one-time `/chat/completions` endpoint composition while retaining Responses and generic Chat modes.
- Settings now persist only masked connection observations (`not_tested`, `passed`, `failed`, or `waiting_for_api_key`) and distinguish real connections from explicit test fixtures; blank key updates preserve the stored key and an explicit clear removes it.
- Connection failures expose actionable 401/402/403/429/timeout guidance without secrets; the local UI shows provider, model, endpoint, and truthful real-vs-fixture status.
- Tests: `tests.test_workbench` + `tests.test_webui` 87/87 pass; no real DeepSeek request was made.

## Unreleased — 2026-10-22 — Issue #23 — Nexus round-2 hardening (PR #33)

- **B3 — Authorized acquisition failures remain unresolved.** A valid authorization followed by a failed `yt-dlp` attempt is now persisted in both the session and the latest acquisition record with status, reason, timestamps and retry count. Failed authorized references remain visible in `eligible`/`pending`, show their reason in the UI, block research until a retry succeeds, or require the existing explicit reason-bearing partial-analysis override; a successful retry clears the active failure.
- **B1 — Adjacent topics no longer pass on generic overlap.** The deterministic topic guard keeps the coverage floor but also requires a distinctive subject anchor, excludes the server-controlled report `topic` field from evidence scoring, rejects the concrete Moscow/flag versus university-exam mismatch, and retains the semantic-paraphrase positive case.
- **B2 — Network regressions are fully offline.** The pinned-public-IP test now uses a fake socket, and deterministic HTTP(S) redirect fixtures cover rejection of loopback/private destinations before any private dial plus a valid public redirect path.
- Mock providers and fixtures verify orchestration and gates only; real-model creative quality remains **UNVERIFIED** pending a configured-model review.
- Verification: focused workbench/WebUI regressions 68/68, `tests.test_workbench` 28/28, full suite 1062 tests OK (7 skipped).

## Unreleased — 2026-10-21 — Issue #23 — Nexus round-1 CHANGES_REQUIRED fixes: topic guard (B1), SSRF-guarded fetch (B2), enforced five-way synthesis (B3)

- **B1 — Off-topic output can never pass gates (fail-closed topic consistency).** The first browser E2E proved the real failure: a Moscow-University topic produced a library-themed "Gate pass" script because the flow overwrote the payload topic with the session topic. New `ensure_topic_consistency` compares the session topic's signal tokens (CJK bigrams + ASCII words) against research/thesis content and rejects obvious foreign-topic output **before saving** (research and thesis generation), at **approval boundaries** (research approval, thesis confirmation) and at **script delivery** (report, card and final teleprompter all re-checked) — semantic paraphrases stay allowed (≥20% topic-token coverage). The exact observed mismatch is a locked regression: a Moscow session + library fixtures cannot generate, approve or deliver (`test_off_topic_research_is_rejected_not_relabelled` etc., plus an HTTP-level 400 regression in `tests/test_webui.py`); no silent relabelling happens anymore.
- **B2 — User-supplied source URLs can only reach public HTTP(S) destinations.** New `workbench/netfetch.py` replaces the raw `urlopen` fetcher: scheme/userinfo pre-flight, per-connection DNS resolution requiring **all** A/AAAA answers to be public unicast (rejects loopback, private, link-local, CGNAT, benchmarking, documentation, multicast, reserved — hostnames and IP literals alike), connections **pinned** to the validated addresses (validation and dial are atomic — no DNS-rebinding window), http(s)-only redirects capped at 4 hops (each hop revalidated through the same pinned path), and **proxies explicitly disabled** (an OS proxy would dial on our behalf and bypass the IP validation). Deterministic tests cover private literals, private/mixed/failed resolutions, redirect-to-ftp rejection and the rebind-simulation (only the validated public IP is ever dialed). Legitimate public fetches and the paste-text fallback keep working unchanged.
- **B3 — Claimed five-way synthesis is now covered and enforced.** The reference-analysis study schema gains an optional `creator_viewpoint` (attributable stance summary, never facts, never copied expression; requested by prompt, supplied by fixtures, honest「未提取」fallback for older studies). `generate_research` now (a) refuses to run while **any authorized (downloaded) reference is still unanalyzed**, requiring an **explicit partial-analysis override with a ≥10-char reason** stored verbatim (`reference_comparison.partial`), (b) injects a deterministic **N-way comparison block** — per-reference attributable viewpoints + shared-pattern/hook/pacing statistics computed locally, hard-labeled never-a-fact-source — into both the research and thesis prompts (thesis prompts may now reference reference creators' viewpoints *by attribution* for differentiation, never as evidence), and (c) reports honest `analyzed N / eligible M` readiness in the UI, the research result, the state view and every script delivery view (`reference_synthesis`) — 1/5 can never be labeled full synthesis again. Deterministic regressions: full-five analysis → comparison injection → research/thesis/script chain with 5/5 delivery metadata, and the incomplete case (blocked without override; override records honest partial state).
- Browser E2E re-run with the topical-consistent, clearly-labeled MSU mock (see `evaluations/issue23_workbench/` round-2 section) plus in-browser negatives: off-topic research blocked (typed error), loopback/private source fetch rejected by the B2 guard. Real Whisper.cpp transcription now covers **all five** authorized references. Two real-chain-only defects were fixed during the re-run: the pinned B2 connection initially broke legitimate public fetches (stdlib `_create_connection` hook now validated-dial-wrapped instead of overriding `connect()`), and a wrong relative import in `thesis_prompt.py` made real thesis-card generation 500 (fakes never exercised the real prompt builder; new `ThesisPromptTests` guard the builder directly). Creative content quality remains **UNVERIFIED** (mock-supplied text), as honestly labeled in the evidence report.
- Tests: `tests/test_workbench.py` 23/23 (was 9, incl. NetFetchTests 6 / TopicConsistencyTests 4 / ReferenceSynthesisTests 2 / ThesisPromptTests 2), `tests/test_webui.py` (routes: B1 negative + partial-override plumbing) OK, full suite re-run on the final code OK.

## Unreleased — 2026-10-21 — Issue #23 — unified creation workbench (topic → authorized references → research → thesis card → reviewed script)

- **The Web UI becomes the full creation workbench.** Beyond reference search, the page now walks a normal creator from topic to a fully-reviewed original narration script with five steps: ① topic + optional user links → real Bilibili discovery (Reference Discovery Contract v1) — ② authorized local download + whisper.cpp large-v3 transcription + narrative-technique analysis — ③ independent-source research draft + real Fact-Check gate — ④ content thesis card with independent review and owner confirmation — ⑤ original script with independent 33-check Schema review and full teleprompter delivery. New UI keeps all round-1 UX fixes (live progress timer, disabled resubmit, responsive layouts).
- **Honor-bound acquisition boundary.** Downloads require an owner-typed authorization statement (stored verbatim per reference), a pre-configured existing local folder, anonymous no-cookie yt-dlp bounded to ≤720p with a 900s per-item timeout; platform blocks (403/412/429/risk-control) fail honestly with typed Chinese errors — never bypassed. Acquisition records file size + SHA-256. Reference outputs influence research only as narrative-technique `insights`; they are never fact sources, never enter any delivery asset pack.
- **Research chain reuses canonical engines unchanged.** Research drafts land in the canonical `reports/` tree with real research mode provenance; Fact-Check re-fetches/uses source bodies and verifies 「」 quotes ≥12 chars verbatim server-side — failing quotes are downgraded to `unverified` and reported, never silently passed. Research approval needs ≥1 user source; thesis-card confirmation needs the explicit 确认+进入写稿 phrase; script generation runs content-profile V1 + thesis card with the full independent Script Review (all 33 checks) — none of the existing gates were relaxed.
- **Two LLM modes with honest limits.** OpenAI Responses (model-side web research) or any Chat-compatible endpoint (**only user-supplied sources**; a research output citing an un-supplied source URL fails closed). API keys live only in gitignored `config/workbench.local.json`, always masked in the UI; a fixed-prompt connectivity test ("正常") validates the endpoint before saving work.
- **Loopback safety extended to all workbench routes.** Existing Host/Origin/Content-Type/Content-Length defenses plus per-route body caps (`WORKBENCH_ROUTE_CAPS`) and one `workbench_lock` serializing all state mutations; settings/test/session/reference/source/research/thesis/script endpoints all ride the same loopback-only server. New contract doc: `docs/WORKBENCH_CONTRACT.md`.
- **Tests:** `tests/test_workbench.py` 9/9 (full-loop fixture: session → sources → research → fact-check pass → approval → thesis → review → confirm → script → review → delivery; chat-mode invented-source fail-closed; bad-quote downgrade) + `tests/test_webui.py` WorkbenchRoutesTests 49 OK (route caps/handshake; incl. the two E2E regressions below). Browser E2E evidence with screenshots: `evaluations/issue23_workbench/`.
- **Real E2E bug fixes (found by the browser run, fixed with the run):** ① `flow.acquire_references`/`analyze_reference` state-persistence callbacks ignored `SessionStore.update`'s `mutate(session)` protocol — the session dict landed in the `ref_bvid` parameter and crashed with `TypeError: unhashable type: 'dict'` after a successful download (the unit fixtures had bypassed both real method bodies). Both callbacks now take the session dict positionally and update the store-loaded state. New regressions execute the REAL method bodies end-to-end (fixture runners + mock LLM) and assert `session.json` persistence. ② Re-running acquisition re-downloaded already-downloaded references and re-archived duplicate authorizations — the front end now splits "needs download" vs "already downloaded pending analysis", and the server skips references whose media file is already on disk (`skipped: already_downloaded`, asserted by an idempotent re-run test). ③ The ④ thesis-card and ⑤ script areas were permanently hidden while their own status was `not_started` — after approving research a real user had NO way to start the thesis step (and no way to reach the script step after confirming the thesis). Both areas are now driven by the upstream readiness state (research `ready_for_script` → ④ visible; thesis `approved_for_script` → ⑤ visible), which is exactly the acceptance path the browser E2E walked.
- **Platform throttle observed honestly:** one reference's audio stream was throttled to ~2KB/s by Bilibili; the product failed honestly at the 900s timeout (no bypass), and a re-authorization used yt-dlp's resumable download to finish that item — recorded in `evaluations/issue23_workbench/README.md`.
- Scope discipline: no publishing, no auto-editing, no TTS/voice synthesis, no platform-limit bypass, no change to the narration schema, discovery contract or any canonical engine.

## Unreleased — 2026-10-21 — Issue #29 — first autonomous UI trial & UX fixes (PR for reference-discovery workbench)

- **First real-creator UI trial (Chrome/Playwright, Issue #29):** exercised the Mac-local Web UI end to end — real Bilibili searches (topic entry, Enter submit, result rendering with verified play counts), invalid-input paths (empty topic, malformed reference URL gracefully skipped server-side, 5-URL limit, 200-char topic cap), responsive layout at 375px/768px/1440px, and console-error checks (zero). Trial report and screenshots: `evaluations/issue29_ui_trial/`.
- **Slow-search feedback (P1):** verified searches can take 20–80s (per-video play-count verification) with only a static "正在检索" line. The busy status now shows a live elapsed-seconds timer, an expected-duration hint and a do-not-resubmit reassurance; `document.title` gains a 检索中… prefix and is restored afterwards. Verified in-browser: timer sampled live 1→19s on a real search.
- **Stale-results dimming (P1):** while a new search runs, the previous result card (still reading "检索完成") is now dimmed via a `stale` class (opacity .55) so the in-flight status and the old results cannot be mistaken for one consistent state; removed on completion.
- **Responsive & empty-state layout (P1/P2):** on ≤600px screens the reference-link input now takes the full row with the remove button right-aligned below it (88×40 tap target) and the search button spans full width; on desktop the footer is anchored to the viewport bottom (flex column) and the empty-state form is vertically centered (`justify-content: safe center`, which falls back to top-alignment without clipping for long result pages — verified with a 12-candidate tall-content render).
- **Verified non-issues (kept unchanged, no over-engineering):** Enter submit, aria-live/aria labels, submit disabling already existed; malformed URLs are intentionally handled by graceful server-side degradation with an explicit已跳过 note.
- Front-end only: single-file change in `src/deeptalk_studio/webui_static/index.html`; no server/API/business logic touched. Tests: `tests/test_webui.py` 46/46 OK, including 2 new contract tests locking the progress timer, stale dimming, interval cleanup and responsive rules.

## Unreleased — 2026-10-21 — Issue #30 — Nexus round-2 CHANGES_REQUIRED fixes for PR #31 (delivery truthfulness, minimal delta)

- **Audio-only edit-guide wording (no implied human frame):** `asset_pack_workflow.py::build_production_asset_pack` gains a fail-closed `media_kind` parameter (`video` default / `audio`; anything else raises). The video guide keeps its original wording verbatim; the audio-only guide intro now states the delivery is pure narration audio with no human frames — material rows are used per the table and gap rows need manual frame-filling — and never says「保持人物画面」. `audio_delivery.py` passes `media_kind="audio"`, and the QA Asset-Pack replay (`_audio_asset_pack_rederived`) derives the same kind from the controlled media artifact so re-derivation stays byte-identical. Deterministic regressions cover both media kinds, both gap shapes and the invalid-kind fail-closed path.
- **Synthetic rights data is clearly marked as simulated:** `tests/integrated_upstream_factory.py::_rights_entries` (the positive E2E fixture) now writes a `rights_basis` that explicitly says the rights data is simulated — no real web page is opened, no real third-party reuse license is granted; it only exercises the canonical Rights Gate flow. The production Rights Gate itself is unchanged (still strict, still fail-closed). The refreshed E2E evidence (`evaluations/issue30_cli_e2e/`) and its README state the same explicitly, so no fixture provenance can be read as an actually verified license.
- Scope: only these two fixes plus related regressions and evidence refresh; the four round-1 blockers are preserved untouched; no narration-schema change, no embedded TTS, no B站 module changes, no new UI, no release/tag change.

## Unreleased — 2026-10-21 — Issue #30 — Nexus CHANGES_REQUIRED fixes for PR #31 (audio-only delivery hardening)

- **Blocking 1 (rights boundary):** `audio_delivery.py::derive_audio_assets` now enforces the canonical Rights/Reuse contract — only materials with a validated `rights_status` in `SAFE_REUSE_STATUSES` (public_domain / explicit_reuse_allowed / creative_commons / official_press_asset), inspected provenance, ready_to_use eligibility and verified file/SHA may enter the Asset Pack. unknown / permission-required / reference-only candidates become `AUDIO_ONLY` rows with the reason recorded and never enter the asset manifest. (`production_status=ready` only proves file integrity; `material_bridge` deliberately keeps `rights_reuse_affects_production_gate=False`.) Negative fixtures: rights unknown and permission-required E2E runs produce all-`AUDIO_ONLY` tables with an empty manifest; positive fixture: a self-built synthetic image whose rights data is explicitly simulated (no real web page is opened, no real third-party reuse license is granted — it only exercises the Rights Gate flow).
- **Blocking 2 (real Clean A-roll Gate):** `run_audio_only_delivery` now runs `inspect_clean_aroll` on the real transcript (full retake / multi-run detection), binds the controlled gate result into the delivery roots instead of hardcoding `accepted`, writes `clean-aroll-gate.json` into `05_A-roll/`, and blocks `needs_manual_cleanup` with the gate's own owner-facing message. Latent gate bug fixed: the gate now reads `spoken_text` from real `timed-transcript/1` units (it previously read a nonexistent `text` field, so retake detection never fired on real transcripts); plain `{"text": ...}` inputs keep working. New E2E fail-closed test: a transcript containing an explicit retake marker is rejected before any Edit Map is written; QA re-derives the gate (`clean_aroll_gate_rederived`) so `accepted` cannot be forged.
- **Blocking 3 (no vacuous QA):** `edit_bridge_qa.py::_audio_no_preview` no longer contains a `pass` placeholder. Preview frame fields are timeline-derived metadata shared with the video branch, so the check now verifies every ready/preview-enabled placement's frames equal the deterministic derivation from its real-time range and profile fps, every disabled/unready placement stays -1, and no preview path/manifest/file exists — all fail closed. Deterministic negative tests cover frame tampering and disabled-placement frames.
- **Blocking 4 (artifact digest verification):** new `validate_audio_delivery_artifacts` runs before any re-derivation: recomputes and verifies the on-disk `edit-map.json` `map_digest` and `visual-asset-manifest.json` `manifest_digest` (via `compute_edit_map_digest` / `compute_manifest_digest`, now the single digest definition in `asset_pack_workflow.py`), verifies edit-map↔manifest↔delivery-roots cross-bindings, and requires every manifest asset `local_path` to stay inside the current Episode and match an accepted candidate with intact SHA. JSON digest-only tamper and a fully self-consistent path substitution (recomputed digests, matching bytes) are both rejected by regression tests. `validate_audio_delivery_assets` (post-hoc audit) now also enforces Episode containment.
- CLI: `align-video` reports gate/session failures in plain language (exit 2) instead of a traceback.
- Tests: `tests/test_audio_only_delivery.py` 16/16 pass; focused modules (clean gate, edit bridge QA, real session, material bridge, asset pack, CLI) 57 pass; full suite 1025 tests — 1023 pass + 2 pre-existing Remotion/Chrome environment failures in `tests/test_visual_asset_engine_fixture.py` / `tests/test_visual_asset_renderer.py` (verified to fail identically on the pre-change head `2346c47`; unrelated to this change).
- Pending: refreshed real CLI E2E evidence in `evaluations/issue30_cli_e2e/` (the committed artifacts are from the pre-fix run and must be regenerated with the rights-verified fixture via `.temp/run_cli_e2e.py` before Nexus review).
- Scope unchanged: no narration-schema change, no embedded TTS, no B站 module changes, no new UI, no release/tag change, no auto-editing/publishing.

## Unreleased — 2026-10-21 — Issue #30 — audio-only final-delivery (WAV/MP3 real timeline → Asset Pack + Edit Map)

- **Final narration audio owns the timeline.** `align-video --session` now accepts a single WAV/MP3 (human-recorded or externally AI-generated narration, provenance declared by the owner) in addition to MP4/MOV; the existing narration/ASR/alignment chain is reused unchanged and the delivery is a truthful Asset Pack + Edit Map (`剪辑表.md/.csv`, `edit-map.json`, `visual-asset-manifest.json`) with token-level real timecodes copied from the actual audio.
- **Fail-closed audio QA**: the formal QA reuses the root/transcript/alignment/placement re-derivation groups and adds `audio_delivery` checks — media must be truly audio-only, no Preview/mux artifact may exist, every `AUDIO_ONLY` row must be asset-less, non-QA-ready and `requires_human_review`, and the Asset Pack must re-derive from canonical roots (temp-root replay, no side effects). Video's 5-group canonical QA (including Preview) is unchanged.
- **No fake human frame**: audio-only deliveries never produce `KEEP_A_ROLL` or “回到人物” wording; unmapped/multi-cue/multi-candidate/unranged-video spans become explicit `VISUAL_GAP` rows that require manual frame-filling. Delivered material files and outputs are tamper-rejected.
- New files: `src/deeptalk_studio/audio_delivery.py` (projection layer: approved-facts binding, span↔cue mapping, material candidates, delivery chain), `tests/test_audio_only_delivery.py` (unit + E2E WAV/MP3/video-reject/tamper). Evidence: `evaluations/issue30_cli_e2e/` (real CLI run with local whisper.cpp large-v3 on synthesized Mandarin speech).
- Scope unchanged: no narration-schema change (source attribution stays as Episode-level metadata), no embedded TTS, no B站 module changes, no new UI, no release/tag change, no auto-editing/publishing.

---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2967233a-71a6-4026-9693-1257295a39b8'
  PropagateID: '2967233a-71a6-4026-9693-1257295a39b8'
  ReservedCode1: '24477860-1bf3-4205-b42f-1fc1cde0d02a'
  ReservedCode2: '24477860-1bf3-4205-b42f-1fc1cde0d02a'
---

# Changelog

## Unreleased — 2026-10-20 — Issue #26 — Nexus CHANGES_REQUIRED fixes for PR #27 (loopback HTTP hardening)

- **Blocking 1 (CSRF / DNS-rebinding):** all requests now pass loopback boundary checks before any body read or discovery invocation — a narrow `Host` allowlist matching the actually listened port (`127.0.0.1:<port>` / `localhost:<port>`; anything else 403), same-origin `Origin` when present (cross-site and `null` origins 403), and JSON-only `Content-Type: application/json` for the API (415). `OPTIONS` is not implemented, so cross-origin browser JSON posts fail before delivery. Rejection errors never echo request headers or URLs. The existing same-origin frontend fetch keeps working (re-verified in a real browser).
- **Blocking 2 (unbounded read via negative Content-Length):** framing headers are validated before reading — unsupported `Transfer-Encoding` → 411 + close, missing/duplicate/non-numeric `Content-Length` → 411 + close, negative → 400 + close, over-cap → 413 + close; the handler enforces a socket timeout, so no request can block a thread waiting for EOF. Raw-socket regressions cover each case with hard deadlines proving no hang.
- **Blocking 3 (artifact overwrite):** artifacts are persisted with exclusive-create (`open('x'`) — a conflicting `candidate_set_id` raises `ArtifactWriteConflict`, the existing file is never overwritten, and the caller receives a safe 500 error. Deterministic regression forces the same id across two runs; helper-level test asserts a pre-existing file stays byte-identical.
- Offline suite grew to 44 tests (18 new across `HttpBoundaryTests`, `ContentLengthHardeningTests`, `ArtifactExclusivityTests`, all on an ephemeral loopback server with injected FakeProvider and raw-socket helpers). Process-level verification on a live 8321 server: same-origin browser search OK (5 candidates, verified live views), `data:`-origin attack blocked with zero new artifacts, curl/json (no Origin) OK 200, `Origin: null` 403, evil Host 403, negative/missing/oversized Content-Length 400/411/413. Scope unchanged: no modifications to the accepted #24 discovery service, visitor/risk-control logic, downloads, or model settings.

## Unreleased — 2026-10-20 — Issue #26 — Mac-local Web UI for reference discovery (Creater Workbench Phase 1B)

- Delivered the first working Mac-local Web UI: `./scripts/deeptalk ui` starts a dependency-free, loopback-only (127.0.0.1) server (`src/deeptalk_studio/webui.py`, Python stdlib `ThreadingHTTPServer`) serving the Chinese creator page (`webui_static/index.html`, native DOM via `textContent`, no `innerHTML`, no CDN/framework/build). Provider mode: anonymous visitor default with `--no-visitor-identity` opt-out.
- `POST /api/discover` (the only business endpoint) calls the accepted `build_reference_candidate_set` + `BilibiliReferenceProvider` directly — each request is a fresh bounded run with the #24 run-level risk-control latch preserved; zero business logic duplicated in JS, no CLI-log parsing. `GET /` + `GET /healthz` only otherwise; unknown paths 404 including any `/api/proxy`-style attempt.
- Results present user references first with “用户链接/搜索发现” badges + merge provenance, verified views (or honest unknown/unavailable states), uploader, publish/fetch timestamps, canonical outbound links, coverage caveat with query plan, typed rejection reasons (e.g. b23.tv short links) and limitations; empty-topic validation is client-side with zero network activity.
- Hard boundaries: request body cap (8KB → 413), topic ≤200 chars, urls 0–5 × ≤300 chars (400 with typed errors), JSON-only responses with `X-Content-Type-Options: nosniff`, discovery runs serialized by lock (no concurrent runs; repeated clicks queue as new bounded runs), artifacts persisted under a fixed output dir with unique `REF-*` names (never overwritten), access logs record method/path/status only (query strings stripped, bodies never logged).
- New offline suite `tests/test_webui.py` (26 tests, injected FakeProvider, ephemeral loopback port): payload validation matrix, static-page hardening (loopback-only, nosniff, no innerHTML, 404s, no proxy endpoint), end-to-end discover (ok/user-first/blocked-degraded/XSS-topic-as-JSON/provider-crash-recovers-to-500-then-alive), persistence uniqueness. Real-browser smoke evidence (5 screenshots incl. 390px narrow screen) in `evaluations/issue26_webui_smoke/`. Full local regression 991 tests OK. No new dependencies, no downloads, no login/cookies, no model-settings UI (separate follow-up issue), no release/tag claim.

## Unreleased — 2026-10-20 — Issue #24 — Nexus Round 3 / Owner directive: visitor bootstrap latches on risk control (PR #25 round 4)

- Closed the last gap in the run-level risk-control latch: the default anonymous visitor-initialization request (`_ensure_visitor_identity`, `use_visitor_identity=True`) now participates in the circuit. When the bootstrap call itself answers with HTTP 403/412/429, a non-JSON HTML challenge page, or API risk code `-412`, the provider latches immediately and `_request_json` returns `blocked` right after the bootstrap — the run stops before any search or per-video request is issued (exactly one network call in total; artifact `blocked`, or `degraded` with user references kept).
- Benign bootstrap failures (transport errors, HTTP 5xx, unexpected-but-non-risk JSON) do not latch and the run continues without a visitor identity, preserving fail-open-free-but-safe degradation; ordinary timeouts/5xx were never risk-control signals and still are not. No bypass mechanism added.
- New regressions (6) at the `use_visitor_identity=True` entry point: provider-level SPI HTTP 412 latch, SPI API `-412` latch, SPI HTML challenge latch (each asserts exactly one total transport call and zero search/view requests), benign SPI 503 and SPI transport-error non-latch; service-level end-to-end — SPI 412 with no user URLs → zero search/view requests and an honest `blocked` artifact with manual-URL guidance; SPI 412 with a user URL → `degraded` artifact keeping the reference honestly unverified after a single bootstrap call. The previous "SPI failure degrades silently" test was rewritten to a genuine benign failure (503) since a JSON endpoint answering with HTML is now correctly classified as a challenge. Owner decision (synced in #24): anonymous visitor mode stays default-ON with the opt-out switch; no login integration this round; no Chrome cookies.

## Unreleased — 2026-10-20 — Issue #24 — Nexus Round 2 fix: risk-control circuit latch (PR #25 round 3)

- Implemented the run-level risk-control latch required by the Round 2 review: the first genuine platform block observed in a discovery run (HTTP 403/412/429, HTML interception page, or API-level risk code `-412`) sets a provider-level latch; every subsequent `search_videos` / `fetch_video_metadata` call in the same run returns `blocked` **without issuing any further network request** — no next query, no remaining per-video verifications, no remaining user-BV checks. Artifact status degrades honestly (`degraded`/`blocked`, never `ok`).
- Ordinary transient failures (timeouts, 5xx) do not latch and remain retryable `failed`; no bypass mechanism added. API `-412` now latches uniformly inside `_request_json`; `fetch_video_metadata` blocked outcomes carry `api_code`.
- New regressions (8): provider-level latch (412 latch, API-412 latch, HTML interception latch, transient-failure non-latch) plus service-level end-to-end latch tests (① first blocked query stops the remaining query plan; ② blocked per-video verification stops all remaining verifications; ③ partially verified candidates survive with honest `degraded` status; ④ multiple user BVIDs: first blocked check stops later user-BV requests and search, references kept honestly unverified). Contract updated with the run-level latch semantics.

## Unreleased — 2026-10-20 — Issue #24 — Nexus CHANGES_REQUIRED fixes (PR #25 round 2)

- **Blocking A:** a user-supplied BVID rejected for invalid/unavailable/restricted metadata and re-appearing in search results no longer crashes with `StopIteration`; it is now deterministically excluded (`excluded_preview` reason `invalid/unavailable/restricted_video`) without a second metadata fetch or re-entering the auto path. Merge logic operates only on actually-retained user candidates.
- **Blocking B:** with `--print-json`, stdout now contains exactly one machine-parseable JSON artifact; the human summary moved to stderr (stdout summary unchanged without the flag). CLI tests now `json.loads` the captured stdout.
- **Blocking C:** the known Bilibili API-level risk-control code (`-412`, returned with HTTP 200) is classified as `blocked` (also for per-video metadata); unknown non-zero API codes stay `failed` — no guessed classification, no bypass.
- **Contract/privacy:** candidate ceiling aligned to #24 (user 0–5, total ≤5; `--max-candidates>5` fails closed); artifact `user_supplied_urls` persists only parameter-free canonical URLs and `rejected_user_urls[].input` only sanitized echoes (URL → host+path, capped; truncation for free text) — tracking tokens (`spm_id_from`, `vd_source`, …) never persisted or echoed; validator rejects non-canonical stored URLs.
- Offline suite grew to 56 tests (new: rejected-user-BVID-in-search regression ×2, API risk-code mapping ×3, `--print-json` purity ×2 + no-flag human-summary behavior, max-candidates cap at service+CLI, artifact privacy/no-tracking-token, sanitization rules, non-canonical URL validation). Visitor bootstrap default (anonymous, opt-out) confirmed by Nexus review.

## Unreleased — 2026-10-20 — Issue #24 — Bilibili reference discovery provider (Creater Workbench Phase 1)

- Implemented the smallest UI-ready B站 reference-video discovery capability: topic + 0–5 user URLs → URL canonicalization/metadata validation (user references kept first, typed rejection reasons) → bounded anonymous multi-query search → deterministic anchor/trigram relevance filtering → BVID dedup → bounded per-video view-count verification → up to 5 machine-readable candidates in a fail-closed validated `reference-candidate-set/1` artifact written to gitignored `discoveries/`.
- Added `BilibiliReferenceProvider` (injectable transport, optional anonymous visitor bootstrap kept in memory only, `--no-visitor-identity` opt-out; HTTP 412/403/429 and interception pages fail to `blocked`/`degraded` and degrade to manual references — no circumvention, no cookies/credentials) and the `discover-references` CLI subcommand with `--print-json` for the future local Web UI. Search-snippet view counts are never presented as verified; sorting coverage is recorded as “检索范围内最高播放量”, never site-wide ranking.
- Deterministic offline tests in `tests/test_reference_discovery.py` (46 tests, injected fake transport/provider) plus an explicit opt-in live smoke `tests/test_reference_discovery_live.py` (`DEEPTALK_LIVE_BILI_SMOKE=1`), no CI dependence on Bilibili. Contract documented in `docs/REFERENCE_DISCOVERY_CONTRACT.md`, listed in `docs/INDEX.md`. No video downloads, no UI build, no release/tag, no canonical-contract change; awaiting [Issue #24](https://github.com/HWang0310/deep-talk-studio/issues/24) Nexus review.

## Unreleased — 2026-10-20 — Issue #21 — Script V1 content-driven duration

- Replaced the new V1 script path's fixed 5–6 minute editorial gate with content-driven length and optional soft duration preferences; actual estimates and deviations remain transparent. No replacement minute quota.
- Preserved historical V1/0.4 readability, Research/Thesis approval, 15 existing plus 17 V1 review checks, grounding, review integrity and immutable revisions. Added a 100,000-character spoken-text processing budget and invalid-preference checks.
- Added synthetic regression coverage; no private creator artifacts were used or changed. Nexus reviewed exact PR head `5812473ca6784c84ee767304304b91e5872ca106` and accepted; [PR #22](https://github.com/HWang0310/deep-talk-studio/pull/22) was merged at `9ac3ff47df927fc843adff9b7eda79004c91c34c`, Issue #21 closed completed. Post-v1.0 `main` improvement; no new formal release/tag, plugin or production change.

## Unreleased — 2026-10-20 — Owner quick-start documentation (docs-only)

- Added [START_HERE.md](START_HERE.md) as the single Chinese entry for creator use versus Nexus PM project maintenance, including ordinary-language prompts, actual v1.0 prerequisite gates, animation-plugin local setup caveats, and troubleshooting.
- Linked the entry from `README.md` and `docs/INDEX.md`. No runtime, skill, plugin, architecture, release/tag, roster, `PROJECT_STATE.md`, or current control-plane behavior changed; no new development was authorized.


## v1.0.0 — 2026-09-10 — DT-V1-REL-001 — FORMAL RELEASE

> Published as tag `v1.0.0`; GitHub Release: <https://github.com/HWang0310/deep-talk-studio/releases/tag/v1.0.0>. The release candidate entry below records its preparation and remains historical.

- **Integration:** `main` fast-forwarded from `65566f348e7f21f5fec32f5f23652973c5229211` to the Nexus-approved release candidate `c7ff6972d0813d8d3a332ad1de1d1a6b35939240` (PR #17, MERGED). No squash, no rebase, no force push; the reviewed lineage is preserved.
- **Release-state reconciliation (docs-only):** `PROJECT_STATE.md`, `README.md`, `AGENTS.md`, `ROADMAP.md`, `PRD.md`, `docs/INDEX.md`, `docs/releases/v1.0.0.md`, this changelog, and `HANDOFF.md` updated from "RC pending / unreleased" to the formal `v1.0.0` release state. No runtime, product behavior, plugin pin, plugin runner/timeout, default-enabled setting, roster, or dependency change.
- **Released product definition:** one main + four auxiliaries — writing / Reviewed Script; source-backed insert materials; explicit MG; explicit Illustrated Metaphor / 小黑漫画; explicit Hand-drawn Animation.
- **Unchanged release invariants:** plugin pins MG `7ae59f1115da8a011113c81f31d320783b0ce8a4`, Illustrated Metaphor `48848affe018fc2cff8ee15bad7a09bb002776e4`, Hand-drawn `624526f4dce0ba9794c1a717fa397eb3c7a1baad`; committed plugin configuration remains disabled by default; creator authority and all fail-closed boundaries preserved.
- **Verification carried forward:** Issue #15 five-capability smoke PASS, Issue #16 RC gate PASS, and the RC full Core regression (879 tests, six expected opt-in skips) remain valid because the only post-RC change is proven docs/release-state only.

## v1.0.0 release candidate — 2026-09-10 — DT-V1-RC-001 — prepared, then approved and released

- Prepared `v1.0.0` from remote `main` `65566f348e7f21f5fec32f5f23652973c5229211` by a normal merge of canonical development `788ed3806c145189a51427f71a65013c050c5f48` on `release/v1.0.0-rc`. The sole content conflict was `AGENTS.md`; it was resolved deliberately to preserve main's canonical Nexus / Atlas / Forge / Scribe / Orion roster and development's current operating rules.
- Defines v1.0 as **one main + four auxiliaries**: researched/fact-checked/thesis-approved/reviewed writing; source-backed insert materials; explicit MG; explicit Illustrated Metaphor / 小黑漫画; and explicit Hand-drawn Animation.
- Keeps creator authority and all fail-closed source, rights, factual, timing, lineage, artifact, and QA boundaries. The three generated families remain invocation-scoped and disabled by default; there is no automatic family choice, winner ranking, overlap resolution, NLE generation, final editing, or publishing.
- Preserves the accepted plugin pins without changing identity, version, runner, timeout, or default-enabled semantics: MG `7ae59f1115da8a011113c81f31d320783b0ce8a4`; Illustrated Metaphor `48848affe018fc2cff8ee15bad7a09bb002776e4`; Hand-drawn `624526f4dce0ba9794c1a717fa397eb3c7a1baad`.
- Reconciles current documentation with accepted Product Architecture V2 Phase A/B/C integration while keeping Phase D generated-provider migration, Phase E REAL_MATERIAL migration, and Phase F production adoption outside v1.0 and not started.
- Reuses Issue #15's Nexus-PASS five-capability smoke at development SHA `788ed3806c145189a51427f71a65013c050c5f48` only if final diff/tree proof confirms no capability runtime, Skill, or plugin configuration change beyond package version metadata and release/governance documentation.
- Adds ordinary-user-facing [v1.0.0 release-note source](docs/releases/v1.0.0.md) and changes the existing Python distribution/public module and private renderer-template package metadata from `0.6.1` to `1.0.0`. This preparation creates no tag, GitHub Release, published package, production-default change, or merged PR.
- Release-grade validation passed before commit: 879 Core tests with six expected opt-in skips, the complete audio-alignment repeat eval, CLI sample/validate/prepare-draft checks, six Skill validations, exact plugin config assertions, five-role roster verification, runtime/source tree proof for smoke reuse, and whitespace/secret/private-artifact/restricted-content gates.
- Known limitations remain: no automatic selection/edit/publish path; MG Quality V2 remains future work; Phase 6 remains held for Owner review. Current locked local renderer toolchains report npm advisories (no critical findings); affected URL/config/archive/HEIF paths are outside the repository-controlled fixed-input v1.0 flow, HEIF is not an allowed material type, and no dependency drift is introduced in this release-preparation task. Nexus must independently review the final exact SHA and PR before any release action.

## Unreleased — 2026-09-07 — DT-ARCH-V2-001 state reconciliation & subsequent acceptance record (docs-only)

> Time-ordered addendum. Records facts that became true **after** the 2026-09-02 entry below. That entry is not rewritten; historical status is preserved as produced at its own date. Canonical current truth remains `PROJECT_STATE.md`.

- **Subsequent Nexus acceptance of Phase 5.** Nexus completed independent GitHub exact-SHA review and issued PASS / ACCEPTED for Core Phase 5 real three-plugin synthetic integration at `db172cecc60ca6b0c276ec42010b113a767bc7b3`. Phase 5 is **ACCEPTED / IMPLEMENTED_UNRELEASED** as of this later acceptance. The 2026-09-02 entry below and `evaluations/visual_asset_engine/phase5_*` evidence keep their original `IMPLEMENTED_UNRELEASED / AWAITING NEXUS ACCEPTANCE` wording because that was the true state when produced.
- **Phase 6 (《牛来》 Owner-visible Micro Demo).** **TECHNICAL_DEMO_COMPLETED / HOLD_FOR_OWNER_REVIEW** on branch `agent/phase6-niulai-owner-demo` at `b72b7c232d24f4b1e1ac531f6f6ef0396e001c0b`. Not PASS, ACCEPTED, MERGED, PRODUCTION, or RELEASED.
- **Production state.** No V2 production migration started; no production default enabled; static plugin config entries remain `enabled: false`. Latest Formal Release remains `v0.6.1`.
- **Product Architecture V2.** Owner-approved product direction; specific architecture design **AWAITING_NEXUS_ARCH_REVIEW**. Owner direction approval is not Nexus engineering acceptance of the design.
- **Docs reconciliation.** Corrected stale `PRD.md` Part D Multi-Asset state, `ROADMAP.md` Phase 5 heading/body contradiction, and `docs/plans/2026-09-07-product-architecture-v2.md` §0.8. No runtime/source/plugin/Phase 6 implementation, `main`, release, or tag change.

## Unreleased — 2026-09-02 — Core Phase 5 real three-plugin synthetic integration — IMPLEMENTED_UNRELEASED / AWAITING NEXUS ACCEPTANCE (at time of writing)

- **DT-CORE-5-001.** Starting from accepted Phase 4 SHA `817ca8b424f18714e4280d3990c1bc4221ec8dbe`, connected the exact-pinned MG, Illustrated Metaphor, and Hand-drawn Contract V1 runners to one deterministic synthetic Candidate Portfolio → Candidate Asset Pack → `candidate-edit-map/1` path.
- Repinned Hand-drawn only, from `67698fd8ea09109ff91c912f51e4c2d4f0b8482f` to the independently accepted correction `853618bdf19ae66ec393211b77d970911f53f4bc`. MG remains `7ae59f1115da8a011113c81f31d320783b0ce8a4`; Illustrated remains `48848affe018fc2cff8ee15bad7a09bb002776e4`. Contract V1 and all runner semantics are unchanged.
- Added caller-bound deterministic request identities, canonical non-semantic plugin/config ordering, independent concurrent runs, mixed-outcome retention, scheduling/order regressions, and real failure-isolation evidence. No failed plugin can erase successful peers or fabricate a response.
- Added sanitized real-runner evaluation proving three distinct creator-usable families, normal all-plugin ABSTAIN on an unsuitable numeric opportunity, Core-owned SHA/duration/provenance QA, and creator-facing none/one/multiple guidance with no automatic winner or edit.
- Full Core, runner-host preflight, and native MG/Illustrated/Hand-drawn validations passed. Phase 5 is **IMPLEMENTED_UNRELEASED / AWAITING NEXUS ACCEPTANCE**. Static production config remains disabled; no real Episode, V2 migration, production default, plugin source change, Phase 6, merge, tag, or GitHub Release is included. Status was recorded as awaiting acceptance at the time of writing; see the 2026-09-07 entry above for the later Nexus acceptance.

## Unreleased — 2026-09-01 — Core Phase 3A-2 & Phase 3B acceptance record — ACCEPTED / IMPLEMENTED_UNRELEASED

- **DT-CORE-3B-ACCEPT-001 (docs-only).** Nexus completed independent GitHub exact-SHA review. **DT-CORE-3A2-001** is **ACCEPTED / IMPLEMENTED_UNRELEASED** at accepted Core SHA `990fc03922e527bef64b819cf898e4266d5669c1`; **DT-CORE-3B-001** is **ACCEPTED / IMPLEMENTED_UNRELEASED** at accepted implementation SHA `ec595587a378d54bd2a18270ded504707b04ddea`.
- MG remains **ACCEPTED / PINNED / IMPLEMENTED_UNRELEASED** at `7ae59f1115da8a011113c81f31d320783b0ce8a4`. Illustrated readiness exact revision `48848affe018fc2cff8ee15bad7a09bb002776e4` and Hand-drawn readiness exact revision `67698fd8ea09109ff91c912f51e4c2d4f0b8482f` are preserved unchanged.
- All three Core config entries remain `enabled: false`. Phase 3B acceptance **≠** Phase 5 three-plugin integration: no three-plugin generation, Candidate Asset Pack, Multi-option Edit Map, production enablement, real Episode, or release exists.
- This acceptance record updates canonical current truth only; no `.py`, `.js`, `.json` config, test, plugin repository, runtime, or Contract was modified.

## Unreleased — 2026-09-01 — Core Phase 3B remaining runner readiness — AWAITING_NEXUS_REVIEW

- Replaced the placeholder Illustrated Metaphor record with the independently reviewed Contract V1 runner identity `org.deeptalk.illustrated-metaphor`, version `0.2.0-contract-runner`, command `python3 scripts/contract_runner.py`, and exact SHA `48848affe018fc2cff8ee15bad7a09bb002776e4`.
- Replaced the placeholder Hand-drawn record with the independently reviewed Contract V1 runner identity `org.deeptalk.handdrawn-animation`, version `handdrawn-animation-contract/0.1.0`, command `node src/contract-runner.js`, and exact SHA `67698fd8ea09109ff91c912f51e4c2d4f0b8482f`.
- Added static, relocation-portable, fail-closed readiness regressions for exact records, disabled state, wrong revision, dirty checkout, reported-version mismatch, and opt-in real checkout preflight/version verification. MG remains exactly unchanged at `7ae59f1115da8a011113c81f31d320783b0ce8a4`.
- Status is **IMPLEMENTED_UNRELEASED / AWAITING_NEXUS_REVIEW**. All three records remain disabled. No plugin repository, Contract, generation orchestration, real Episode, Candidate Pack, Edit Map, `main`, tag, or Release was modified.

## Unreleased — 2026-09-01 — Core Phase 3A-2 real MG integration — AWAITING_CHATGPT_REVIEW

- CORRECTION-1: Core now performs lexical `lstat` checks before path resolution and rejects a symlink output root, any existing symlink ancestor below that root, and a symlink artifact even when its resolved target remains inside the output root. Traversal, containment, existence, SHA-256, and duration checks are unchanged.
- Connected the existing Contract V1 subprocess adapter and Candidate Portfolio orchestration to MG `org.deeptalk.mg` version `1.0.0-contract-v1`, exact-pinned at `7ae59f1115da8a011113c81f31d320783b0ce8a4`, through `node scripts/contract-runner.js` and request/result/artifact files only.
- Added fail-closed plugin-root, full-HEAD, clean-worktree, reported-version, response identity, Contract version, canonical argv, environment/config digest, request/result identity, and task evidence. No revision bypass remains for synthetic runners.
- Added deterministic timeout evidence and controlled regressions proving SIGTERM escalation to SIGKILL both when the direct child ignores termination and when a wrapper exits while a same-group descendant survives; Core reaps its direct child, verifies group termination, and emits no raw result or Candidate. Runner launch `OSError` failures are isolated fail-closed.
- Kept `visual-asset-plugin-config/1` and historical execution evidence readable while requiring enabled pinned entries and all newly completed evidence to bind version, exact revision, resolved argv, request/result identity, and identical proposal/generation-to-audit execution copies.
- Proved one synthetic causal opportunity through real MG suitability (`SUITABLE`), policy-requested generation, READY/PASSED primary media, Core SHA/ffprobe/artifact-boundary acceptance, and immutable portfolio reload. The MG entry uses a 180-second budget because measured local generation completed in about 125 seconds; the previous 120-second placeholder failed closed before normal completion.
- Status is **IMPLEMENTED_UNRELEASED / AWAITING_CHATGPT_REVIEW**, not ACCEPTED or RELEASED. No MG source, Illustrated, Hand-drawn, real Episode, Candidate Pack, Edit Map, V1 writer, `main`, tag, or Release was modified.

## Unreleased — 2026-08-30 — Relocation-safe Core artifact semantics — ACCEPTED / IMPLEMENTED_UNRELEASED

- Added a strict machine-local runtime resolver for digest-covered Motion Manifest, reviewed Material Package, and Material Capture paths after a canonical workspace move. Historical artifacts and digests remain unchanged; only separately verified runtime observations use the new canonical location.
- Core now rejects unknown roots, arbitrary prefix replacement, traversal, identity mismatch, symlink escape, missing/non-file targets, byte-size/SHA mismatch, and outer-manifest tampering across Motion validation, Material replay, Edit Bridge QA, production planning, and renderer staging.
- `align-video` may select an exact configured current Production and no longer uses filesystem mtime. Its compatibility fallback uses artifact-owned time/revision/identity fields; a formal immutable current-production index remains deferred.
- Machine-specific canonical repository root belongs to gitignored local config; the architecture remains portable. No user-specific absolute paths are committed as product invariants.
- **ChatGPT independently reviewed and accepted the implementation** at SHA `e4dbbd089d6253cf053e55f0b2a1ae1c38a58bc1` on branch `agent/relocation-safe-artifact-resolution`. The accepted implementation was fast-forwarded to canonical branch `agent/multi-asset-studio` without merge commit, rebase, or force push. This acceptance commit is docs-only; no implementation source code was modified during acceptance.
- This is ACCEPTED / IMPLEMENTED_UNRELEASED — not RELEASED. No historical JSON, private Episode fixture, visual plugin, `main`, tag, or Release was changed. Phase 3A remains IN PROGRESS: the first MG Contract V1 runner has an implementation on its plugin review branch but is NOT yet accepted/pinned. Core real-plugin Phase 3A-2 integration has NOT started.

## Unreleased — 2026-08-29 — Multi-Asset Phase 2 portfolio Core QA

- Review correction: completed real fake-subprocess multi-plugin orchestration, runtime-version and bounded execution evidence, declarative policy loading, canonical `opportunities[]` portfolio/audit shape, verified Reviewed Script directive binding, and Core-owned request factual lineage.

- ChatGPT formally accepted Phase 2 as ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation. It remains fake-only and synthetic; Phase 3A is the separate next gate for one independently reviewed and pinned real-plugin runner plus one synthetic Core integration.

- Added production-safe `visual-opportunity-directives/1` authoring from verified synthetic timeline, reviewed-script digest, and approved factual bindings; only clock-free `visual_intent` / `why_visual` semantics cross the authoring boundary.
- Added deterministic no-quota LEAN/STANDARD/RICH generation policy, fake-only multi-plugin `candidate-portfolio/1` histories, no-call evidence, audit records, and raw READY plus separate Core acceptance projection.
- Added Core-owned local-runner artifact resolution, SHA-256, ffprobe duration, placement, lineage, provenance, duplicate-ID, and generated-as-real rejection checks, plus structural fail-closed reload validation for portfolios and opportunity plans.
- This is sanitized synthetic fake-runner implementation only. It does not integrate a real plugin, create a Candidate Asset Pack or `candidate-edit-map/1`, alter V1 writers, migrate production schemas, or release a product version.

## Unreleased — 2026-08-28 — Multi-Asset Phase 0 contract baseline

- Multi-Asset Phase 1 review-branch implementation: added clock-free directives, Visual Opportunity artifacts and storage, fake-only subprocess configuration/protocol, and the minimal raw-plugin/Core-acceptance Candidate Portfolio slice. No real plugin, Episode, Candidate Pack, release, or V1 writer change is included.
- Phase 1 review correction: verified canonical Semantic Timeline lineage, made raw Contract cross-stage evidence and Core acceptance explicit, preserved adapter execution locators in portfolios, and made storage reload checks recompute artifact digests.
- ChatGPT formally accepted Phase 1 as ACCEPTED / IMPLEMENTED_UNRELEASED canonical implementation. Phase 2 remains a separate future gate; no real-plugin integration or release is implied.

- Added strict `visual-asset-plugin-contract/1` request/response validators with frozen enum, identifier, failure-envelope, artifact, raw candidate-status, READY/QA_REJECTED, duration, and real A-roll placement invariants.
- Added a sanitized synthetic Contract V1 corpus, a clock-free `visual-opportunity-directives/1` fixture, a deterministic test-only fake fixture emitter, and disabled placeholder plugin/policy configuration examples.
- Phase 0 review correction: removed the non-contract artifact uniqueness restriction. `QA_REJECTED` candidates still do not require READY delivery fields, but now validate duration, suggested placement, artifacts, and provenance structurally whenever those optional fields are present.
- Preserved all V1 writers/readers: no Visual Opportunity runtime, subprocess adapter, Candidate Portfolio, Candidate Pack, real plugin invocation, Episode work, merge, tag, Release, or `main` change is included. ChatGPT formally accepted Phase 0 as ACCEPTED / IMPLEMENTED_UNRELEASED; the next gate is Phase 1's Visual Opportunity + fake subprocess vertical slice.

## Unreleased — 2026-08-28 — Accepted Multi-Asset Implementation Plan

- Added and formally accepted an implementation-only plan for the accepted Visual Asset Plugin Contract V1. It records the inspected Core and three-plugin runtime baseline, a local subprocess plus Core-owned request/result-file protocol, static local plugin configuration, Core-side acceptance/lineage QA, opaque local artifact locators, deterministic LEAN/STANDARD/RICH policy, non-exclusive portfolios, Candidate Asset Pack, and `candidate-edit-map/1`.
- Sequenced additive contract fixtures, fake-runner vertical slice, Core portfolio/QA, separately pinned real plugin runners, creator pack/map, three-plugin synthetic integration, and a distinct real-episode gate. It preserves V1 readers/artifacts and defers REAL retrieval, automatic editing, registry/cloud work, and a new Finished Cut Review contract.
- Clarified that Phase 0 — Contract fixtures + frozen V1 compatibility baseline — is the next gate and requires a separate implementation session, branch, and review. This documentation-only acceptance does not start Phase 0 or implement a schema, runtime, adapter, portfolio, plugin runner, episode output, tag, Release, merge, or `main` change.

## Unreleased — 2026-08-28 — Visual Asset Plugin Contract V1 design

- Recorded the accepted multi-repo, plugin-first Visual Asset Ecosystem principle in canonical product and architecture documents.
- Added an evidence-derived Contract V1 design from read-only MG, Illustrated Metaphor, and Hand-drawn Common Brief trials: two-stage suitability/generation, normal ABSTAIN, eligible BORDERLINE, non-exclusive candidates, role-based artifacts, separate operation/candidate state, independent versioning, and opaque plugin metadata.
- Clarified Contract V1 lineage and boundaries after Architecture Review: per-call request IDs, stable opportunity/proposal/candidate IDs, Generation Result proposal linkage, bounded placement, opaque artifact URI locators, and operation states separate from candidate asset states.
- ChatGPT Architecture Review formally accepted Contract V1 as ACCEPTED_UNRELEASED architecture. The next gate is Multi-Asset Implementation Planning; no runtime implementation, schema adoption, tag, Release, or `main` change has begun.
- Kept `REAL_MATERIAL` outside generated-plugin V1 pending a dedicated evidence/retrieval adapter design. No production code, registry, runtime integration, migration, tag, release, or `main` change was made.

## Unreleased — 2026-08-27 — Project Memory Consolidation

- Added `PROJECT_STATE.md` as the concise canonical current-state owner and `docs/INDEX.md` as the documentation reading map.
- Reclassified the accepted Multi-Asset Studio Product Review outcome as accepted/unreleased with implementation not started; no production contract, schema, or code changed.
- Reconciled README, PRD, ROADMAP, ARCHITECTURE, AGENTS, and historical entry points so `v0.6.1` remains the latest formal release and V1 Candidate remains unreleased.
- Preserved plans, specs, release notes, evaluations, and the chronological HANDOFF log. They remain historical evidence rather than competing current-state sources.

## Unreleased — 2026-08-27 — Multi-Asset Studio research

- Added Product / Technical Reconnaissance for Multi-Asset Studio repositioning. Its research/proposal material remains preserved; the 2026-08-27 Product Review subsequently accepted the core direction, while implementation has not started.

## Unreleased — 2026-08-25 — Finished Cut Review + Production Feedback Loop

- 新增 `finished-cut-review/1` 与 `production-feedback/1`：在用户手工完成 NLE 成片后，只读比较 Edit Map、Asset Manifest 与 Finished Cut 的实际素材使用；计划偏差记录为 `USER_EDIT_OBSERVATION`，不是剪辑错误。
- 新增保守的媒体探测与全画幅素材匹配。无法以可区分画面安全确认的素材一律保持 `UNKNOWN`；不会因为相同深色背景或相近静帧而误报已采用。
- 新增本地 JSON/Markdown 复盘写入器，只会写入 episode 的 `_DeepTalk记录/` 与 `10_成片/`，绝不生成视频、NLE 工程或自动二剪。
- 单期复盘只能生成需要人工或多期验证的 `CANDIDATE_PRODUCT_RULE`，没有自动升级为全局策略、创作者评分或爆款预测的接口。
- 以《牛来》用户手工完成的第一版成片完成真实只读验证；本期媒体和复盘工件保持 Git 外本地保存，未创建 tag、Release，未改动 `main` 或 `v0.6.1`。

## Unreleased — 2026-08-25 — Asset Pack + Edit Map production boundary

- 将 V1 Candidate 的默认后半段交付正式改为 `Final Clean A-roll → Semantic Timeline → QA-ready Asset Pack + Edit Map → 用户手工 NLE 剪辑`；历史全片 Remotion Preview 保留为兼容、预览和 QA，不再是默认产品成功标准。
- 新增 immutable Clean A-roll Gate、真实语义时间轴、`FACT_CONFLICT` display blocker、actual-span-only Motion timing、Asset Pack workflow 与 machine `edit-map/1`。系统不选择 take、不自动删停顿/重录/废段、不裁剪或拼接 A-roll、不生成 NLE 工程或最终成片。
- 普通 `KEEP_A_ROLL`、`REAL_MATERIAL`、`MG_MOTION` 决策不再需要逐条人工批准；`ADVANCED_MOTION` 继续要求独立 Review。未 READY 素材按 `ADVANCED → MG → REAL → KEEP_A_ROLL` 安全降级，禁止 broken Edit Map。
- 增加 22 项定向 regression，覆盖无真实对齐拒绝、真实时间映射、KEEP、非 KEEP 的 READY/SHA 绑定、失败回退、无默认 final video/NLE project、事实冲突阻断、MG real-span timing、无自动 take 选择/剪辑和 Advanced Review。
- 已用《牛来》的最终真人 Clean A-roll 完成一次真实验证：本地 `whisper.cpp large-v3` 转写、25/25 Script Beat 的真实时间对齐、Semantic Timeline、Visual Director、3 条 QA-ready MG 动画、Asset Manifest 和 25 行 Edit Map 均通过。交付是可直接导入剪映的 A-roll + 素材包 + 剪辑表，不是自动生成的完整成片或 NLE 工程；episode 私有素材始终未进入 Git。

## [Unreleased] - 2026-08-24

### Local real-episode Script V1 acceptance run

- Ran one user-owned real episode through the already-implemented Content Director + Script Agent V1 path using its explicitly approved local Markdown fact pool and SHA source-lock. Its first draft was held for four content-quality failures, then revised once and passed the evidence, counterevidence, duration, originality and 17-item quality review.
- No episode thesis, research, draft, reviewed script, source text, media, hash or private creative artifact was added to Git. No product code, main branch, tag or Release changed in this run.

### Local real-episode Creator Polish

- Performed one permitted Creator Polish revision on the same user-owned real episode. The pass retained all evidence and thesis constraints, reduced repeated explanation and article-like phrasing, strengthened the second hook and Creator Listen Test, and produced a final reviewed local script.
- No product code or episode creative content was committed. The final real-episode boundary remains: user reads the script and decides whether to record; no A-roll or visual stage begins.

### Content Director + Script Agent V1

- Added Content Thesis Card 1, controlled Thesis Review Artifact, immutable local storage and ordinary-language review pages. A Thesis Card is bound to exact approved Research content, verified confirmed facts and counterevidence; a passing machine review still cannot start writing until an explicit human confirmation is recorded.
- Added Script Profile 1 and Script Draft/Review compatibility for V1 while preserving the 0.4 path. V1 requires an approved Thesis binding and enforces an actual 5–6 minute spoken-duration range.
- Added 17 blocking Script Quality Gate checks on top of the legacy fact-safety review, including hook, conflict, cognitive turns, propulsion, re-hooks, counterevidence, audience value, audio-only interest, originality and a non-summary ending. A failed audio-only check cannot become advisory.
- Added no-search Writer/Reviewer prompt boundaries: competitive references can inform high-level content mechanisms only and cannot supply facts or expressions.
- Added real 《牛来》 Content Thesis Card, human-readable Thesis Review and source-lock manifest outside Git. The thesis passes the preparation review but is deliberately **pending human confirmation**; no final Script, A-roll or visual work was generated.

### Visual Asset Engine Chinese Display Text renderer hardening

- Replaced the Visual Asset Engine's no-text ffmpeg fallback with the repository's installed Remotion/Chrome browser route. A visual asset is now ready only when its browser-rendered MP4 and deterministic PNG text reference frame both exist.
- Added one binding-preserving, bounded Chinese text primitive with title, heading/node, body and pure-numeric emphasis roles. It uses an available macOS Chinese system font, retains the exact approved text, wraps only within explicit capacity, and fails rather than paraphrasing, clipping or silently shrinking unsafe text.
- Regenerated the five synthetic grammar fixtures plus a Chinese stress fixture covering Chinese labels, punctuation, dates, numbers and `B站 / AI`; added evidence sidecars that bind the visible text, reference frame, source range and Motion Spec digest.
- Added regressions for Chinese layout preservation, overflow failure, safe-area placement and final render evidence. No real episode, reviewed Script, approved Research, reviewed Material Package, main branch, tag or Release was changed.

### Visual Asset Engine MVP foundation

- Added alignment-bound `visual-director-plan/1` decisions with `KEEP_A_ROLL` as the default and explicit MG/Advanced review requirements; proposal-supplied A-roll clocks are rejected.
- Added binding-first `motion-spec/1`, common primitive payloads, a local deterministic five-asset fixture route, `visual-asset-manifest/1`, creator folders and Markdown/CSV Edit Map. The fixture produces three MG clips, a path clip and a controlled metaphor clip without external API keys.
- The installed local ffmpeg lacks SVG decoding and `drawtext`; the fixture renderer therefore proves deterministic 1920×1080 MP4/path reveal and asset QA, but does not yet provide final Chinese text typography. This is a production gap, not a real-episode pass.

### Visual Asset Engine MVP design

- Recorded the non-implementation MVP contract for a Visual Director that makes one of four explicit decisions per safe A-roll opportunity: keep the speaker, show reviewed real material, use parameterized MG, or reserve a small number of advanced motion moments.
- Defined the proposed MG grammar, Advanced Motion Spec, asset-manifest/Edit-Map, human review, Gate and fallback contracts. No renderer, production logic, formal artifact, media output, tag, release, or main branch was changed.

### Real-user visual presentation and output-truth hardening

- Corrected the aligned Preview presentation contract: approved full-screen material and Motion placements now occupy the primary canvas; the A-roll returns outside those placement windows, while the subtitle layer remains above both.
- Added controlled `primary_visual`, `primary_visual_with_pip`, and `supporting_overlay` modes. The renderer never derives display semantics from new editorial text; picture-in-picture has an explicit A-roll inset implementation.
- Added persisted final-MP4 Output-Truth evidence and a blocking canonical QA check for formal Full Visual previews. Evidence binds the final output SHA and records saved pre/in/post frames for sampled ready placements.
- Generated the real-user r0003 preview without changing reviewed Script, approved Research, Transcript, Alignment, approved Material, Visual Plan, or A-roll. Canonical QA completed with the existing expected B011 `partial_placement_unready` warning only.

## [Unreleased] - 2026-08-22

### Post-alignment full visual planning

- Added episode-only visual preferences, an immutable alignment-derived 18-beat visual plan, reviewed evidence-bound original visuals, and typed safe handling for unplaced opportunities.
- Real-user preview r0002 passed all six canonical checks with the expected B011 `partial_placement_unready` warning; no release, tag, Script, Research, Transcript, or Alignment change.

本项目使用日期和版本记录实际完成的修改。规划中的功能只写入 ROADMAP，不写入已完成记录。

## [Unreleased] - 2026-08-21

### SAFE-CUE REAL MATERIAL COMPLETION + REAL USER VISUAL PREVIEW

- 针对当前 approved Alignment 仅补齐 VC003/B006 与 VC007/B016 的真实页面/法条截图；没有修改 reviewed Script、
  approved Research、Transcript、Alignment、Basic Subtitle 或既有 Motion。
- 新建不可变 Material Package `MAT-20260821-safe-cue-completion-01` r1 → reviewed r2，Material Review Gate `PASS`；
  新 capture manifest 绑定两张实际打开并保存的 PNG，保留 source URL、capture region、文件大小和 SHA-256。历史 rights
  继续保守记录为 `editorial_reference_only/reference_only`，没有声称取得版权许可，且不让 rights 冒充 Production Gate。
- 从新的 Material lineage 建立 `PROD-20260821T170000-safe-cue-completion-01`、Motion Manifest 和 Production QA；逐项核对
  旧 approved Motion 的 scene/payload/文件 SHA 后只做 canonical rebind，没有重新渲染 Motion，也没有让 Motion 进入新 Preview。
- 复用已有真实 whisper.cpp Transcript、Alignment `ALIGNMENT-96854be79b9048a2b6800e1313efb2a6` 和 Basic Subtitle，生成新的
  620.533333 秒全长 Remotion Preview。新 Edit Bridge/Preview/Manifest/Canonical QA 均保存为新的 immutable session；QA 为
  6 项通过、0 blocking、1 个预期 `partial_placement_unready` warning。新 Preview 当前停在人工作看 Gate，未创建 V1 Release、tag 或修改 main。

### Global Monotonic Alignment Projection + Real User E2E Resume

- 将 Script Alignment 升级为 `script-alignment/2`：完整 reviewed Script 与完整 Timed Transcript 只运行一次
  确定性、顺序保持的 evidence pass，再投影 Beat/Cue；不再让单个 Beat 回退扫描整条真人录音。
- 新增版本化 global correspondence：每个 Script lexical unit 保留 match/numeric/substitution/deletion 与真实
  Transcript index/unit/time；Transcript-only token 保留 leading、Beat-local、Beat-boundary 或 trailing ownership。
  不改写原始文字、时间戳或既有 Profile threshold。
- Beat status 以本地 evidence 重算：普通替换、小缺词、filler 不再自动污染全片；真实长缺口、边界风险与实际
  ambiguity 继续 fail closed。Cue 直接消费自身 global mapping，因此不因父 Beat 的无关 review 自动失去时间。
- 重放用户的既有 immutable Transcript，没有重新运行 Whisper：由 `18/18 needs_review`、213 gaps、8/8 unplaced
  变为 `17 aligned / 1 needs_review / 0 unmatched`、117 global gaps、`2 aligned / 6 unplaced` Cues。B011 保留为
  13-unit 真实文本缺口（需要听音确认）；B018 的约 154-unit Script 外结尾保存为 trailing ad-lib，不进入前段。
- 新增匿名 global-localization、long omission、tail、Cue substitution 18/20、Cue deletion 与 parent-review
  decoupling regressions。真实安全 Cue 为 VC003、VC007，但它们在当前 reviewed Material/Production 中没有可用
  real image 或 Original Motion；因此没有伪造 placement、没有重渲染新 Preview，Human Preview Gate 未达到。

### REAL USER ALIGNMENT BLOCKER DIAGNOSIS

- 对第一次真人 Clean A-roll E2E 的 `18/18 needs_review`、`213 gaps`、`8/8 Cue unplaced` 完成只读诊断；
  未重转写、重渲染、改 Script/Transcript、改 Alignment/Gate/阈值或开发新功能。诊断 JSON 与 Markdown 只保存在
  Git 外的 real-user E2E artifact `diagnostics/` 目录。
- 所有 Script r2、真人 Transcript、Media SHA、Timestamp Mapping、Material r2、Production Plan 与 8 个 Cue
  binding 均重算通过；没有误用 synthetic Transcript、旧 Script revision 或错误 production lineage。
- 根因确认为 mixed：**CASE D 为主因**。当前 per-Beat fallback 在没有整段逐字命中时把单个 Beat 与整条
  Transcript 比较，其他 17 Beat 必然成为 `transcript_insertion/ad_lib`；任何 deviation 又阻止 `aligned/high`，
  因而即使 17/18 Beat 已满足 accepted lexical floors，仍会系统性全部 `needs_review`。B001 的 1,289 candidate
  windows 覆盖几乎全片，是缺少定位的算法歧义，不是 1,289 次真人复读。
- **CASE B 为次因**：全片顺序诊断得到 Script→Transcript exact/numeric lexical coverage `94.8232%`、
  Transcript→Script `90.1872%`，Beat 边界顺序违例为 0；但 B011 有 13-unit 缺口、B018 有 154-unit Script 外
  尾段，需要未来听音频/人工 review 确认。其余主要是专有名词与单字 ASR 噪声或正常口语变化。
- 当前 fail-closed 生产 Gate 保持正确；建议下一步仅由 ChatGPT 决定是否设计“全局单调、顺序感知”的证据
  pass，再投影 Beat/Cue，同时保留 B011/B018 人工 review 与所有安全边界。本轮不实施。

## [Unreleased] - 2026-08-21

### REAL USER CLEAN A-ROLL E2E

- 使用用户提供的真实无烧录字幕 Clean A-roll `/Users/hwang/Movies/口播/AI事故8月21日.mp4` 完成正式本地
  large-v3 生产路径：immutable media → 24 kHz mono audio → whisper.cpp v1.9.2 full multilingual
  `large-v3` + `--dtw large.v3` → Timed Transcript → Script Alignment → Edit Bridge → 完整 Remotion Preview
  → canonical QA。原始媒体 SHA-256 为 `39d08733447f78c60b5cc0f737781c8fc3a9d95629d7f92a04902bbe0f8e57ec`，
  时长 `620.530068` 秒；输入文件未移动、覆盖或改写。
- 真实 Transcript 生成 2,646 个 token/unit，raw token overlap `0`，未使用 fixture、synthetic timing、
  cloud ASR、second ASR、forced aligner 或 Script 覆盖 Transcript。Timed Transcript digest 为
  `85154b27fed6b9871c4975692b37410d5d79526caa7128cb3d0ccc2d525b92f7`。
- 18/18 Beat 为 `needs_review`（13 medium、5 low），存在 213 个 alignment gaps；8/8 Cue 为 `unplaced`，
  因此所有真实截图/文件与 Original Motion 均保持未落位，没有猜时间或伪造素材位置。产品 Alignment、
  Material Placement、Motion Placement Gate 阻塞；不得把技术 QA warning 误写成完整 E2E 通过。
- 生成完整 Preview `ALIGNED_PREVIEW.mp4`，1920×1080、30fps、H.264/AAC、`620.533333` 秒，SHA-256
  `36d29165238bd1a2dcb05060be067aee05eedfe44f0898ce0b3858e589d71bf9`；当前路径仍烧录 Basic Subtitle，
  没有无字幕 visual master。Canonical QA 6 项通过、0 blocking failure，唯一 issue 是预期的
  `EBI0001 partial_placement_unready` warning。
- 本次 production session 没有持久化 whisper 单阶段 runtime/RTF，已在 HANDOFF 标为 observability gap，
  未从文件时间伪造精确数值。完整代码回归 `454 passed, 3 skipped`；本轮未修改 Script、Research、Material、
  main、v0.6.1 tag 或 GitHub Release，V1 仍为 `Candidate — Unreleased`。

## [Unreleased] - 2026-08-14

### Quality-first large-v3 long-form production validation

- 按用户明确的 quality-first 决策，将 V1 唯一生产默认从 historical medium 升级为官方完整精度 `ggml-large-v3.bin`，固定 `whisper.cpp v1.9.2`、source commit `306c88f4d1286aec1bf96e544632897886af5501` 和正确的 `--dtw large.v3`；medium Selection Gate 工件与缓存保留，不被改写或删除。
- Bootstrap 现在核验 full large-v3 的官方 URL、`3,095,033,483` bytes 和 SHA-256 `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`，并记录 DTW provenance。桌面环境未继承 shell proxy 时会读取已启用的 macOS HTTPS 系统代理，仅用于官方模型下载。
- 新增 raw overlap audit：任何相邻 token overlap 仍 fail closed，但会输出包含 chunk、segment、raw token/provider order、raw 起止时间、控制 token、边界、runtime/model/DTW 和 raw JSON digest 的版本化证据；没有引入 canonicalization、segment fallback、LLM/dictionary/second ASR 或 cloud fallback。
- 新增外部证据 runner 与 render liveness monitor。真实 no-key 272 秒 smoke：large-v3 在 Apple M4 Metal 上 87.210505 秒、RTF 0.320194、1,167 token、overlap 0，且 `ProviderTranscript → Timed Transcript → Script Alignment` 通过。相同音频上 large-v3 保留 OpenAI、DeepSeek、AI Agent、GPU；`昇腾` 仍未精确命中，原始文本未被人工修正。
- 真实非私人 274.267 秒 synthetic Clean A-roll 已跑完完整 production E2E，生成 1920×1080/30fps H.264/AAC、274.3 秒 Aligned Preview，SHA-256 `2377c5459c5bd31894ece27c105ec7305f03269f215732c41efea619df773c81`；完整 session 665.763 秒，canonical QA 0 blocking failure，保留 1 个预期 `partial_placement_unready` warning。
- 本轮未修改 reviewed Script、approved Research、reviewed Material Package 或历史 Production 工件；未创建 tag、Release 或修改 main。真实用户 Clean A-roll Gate 仍需要下一轮真人试用与人工 Review。

### V1 Local Transcription Production Integration

- 将已通过 Selection Gate 的 `whisper.cpp multilingual medium` 变成正式 `LocalWhisperCppTranscriptionProvider`，接入现有 `TranscriptionProvider → ProviderTranscript → Timed Transcript` 契约和唯一 `run_real_edit_bridge_session` 入口；未修改 reviewed Script、approved Research 或 reviewed Material Package。
- 新增 repository-owned bootstrap：锁定 whisper.cpp v1.9.2/source commit `306c88f4d1286aec1bf96e544632897886af5501`，Apple Silicon 启用 Metal，自动准备 runtime 与 1,533,763,059-byte medium 模型，SHA-256 固定为 `6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208`；runtime、model、provenance 只进入外部 `~/.cache/deep-talk-studio/transcription/`，不进 Git。
- 默认路径不查看或要求 `OPENAI_API_KEY`；OpenAI adapter 保留为未来可选能力。Provider 只接受 whisper.cpp full JSON 的真实 token offsets，缺失、越界或重叠时 fail closed，禁止插值、LLM 伪造和 silent cloud fallback。
- 新增本地长音频 `transcription-chunk-profile/local-whisper-cpp/1`，继续复用现有 PCM natural-pause `TranscriptionChunkPlan` 与 local→global mapping；ProviderTranscript 绑定 runtime/model/audio/chunk/raw-response provenance。
- 无 API Key 的真实非私人音频 smoke 通过：1,136 token units、token granularity、runtime 42.780224 秒、RTF 0.157068，transcript digest `153374e56a30e2f29a6ac923008dbc510db8b202539734f0445a97c82926e5dd`。
- 正式短版 production E2E 通过：真实 whisper.cpp → Timed Transcript → Alignment → Material → Motion → Basic Subtitle → Edit Bridge → Remotion Aligned Preview → canonical QA，输出 20 秒、1920×1080、30fps、H.264/AAC 的 preview，QA 无 blocking failure，只有预期 `EBI0001 partial_placement_unready` warning；Preview 保留原 Clean A-roll 音频。
- 长版合成验证如实记录为 gap：标准 24 MiB profile 的尾 chunk 曾出现越界，已用版本化本地 long-form profile 修复；完整 272 秒验证又发现 5 处 runtime token overlap，按 fail-closed 停止；约 272 秒 Remotion render 在本机环境耗时过长而停止。真实用户 Clean A-roll 尚未提供，因此 `REAL USER CLEAN A-ROLL GATE` 仍为 `BLOCKED/PENDING`。
- 本轮保持 `V1.0 Candidate — Unreleased`；没有新 tag、Release 或 main 修改，selection history `evaluations/local_asr_selection/` 保留。

## [Unreleased] - 2026-08-14

### Local ASR Selection Gate

- 按 ChatGPT 最终产品原则完成真实本地 ASR 选择 Gate；没有执行旧的“直接采用 whisper.cpp”方案，没有修改 reviewed Script、approved Research、reviewed Material 或正式 Production 工件。
- 用同一份非私人 272.367 秒、24 kHz 单声道中文评测音频比较官方 `whisper.cpp v1.9.2` multilingual medium 与 Microsoft `VibeASR.cpp` / `VibeVoice-ASR-BitNet@66e7802`；模型、音频和原始长日志均放在项目外部缓存。
- `whisper.cpp` 在 Apple M4 Metal 上真实 wall runtime 44.37 秒、RTF 0.1630，输出直接 token offsets，并完成 `ProviderTranscript → Timed Transcript → Script Alignment`；新增 evaluation-only parser 与最小 adapter regression。
- VibeASR 在同音频真实运行 JSON/text 两种模式，RTF 1.2109/1.0402；没有 machine-owned media timestamps，且输出重复文本并耗尽 max tokens，按时间戳 Gate fail closed，不生成 Timed Transcript 或 Alignment。
- 选择结论：推荐 `whisper.cpp multilingual medium` 作为 V1 默认本地 Provider 候选；正式默认接入与自动 bootstrap 仍为 `PENDING_CHATGPT_REVIEW`，本轮不创建 V1.0、tag 或 Release。
- main、正式 `v0.6.1` tag 与 GitHub Release 保持不变；V1 仍不依赖任何 API Key，现有 OpenAI Provider 只保留为后续可选能力。

## [Unreleased] - 2026-08-13

### REAL USER E2E Preflight unblock - 2026-08-14

- 安装并验证项目专用 OpenAI Python SDK `2.54.0`；未记录或输出任何 Key。`OPENAI_API_KEY` 缺失，真实 OpenAI smoke 尚未运行，也没有 deterministic fallback。
- 新增不可变 `material-capture-manifest/1` 和 Material Production View 重放：已检查素材只有在 exact package/material/source/capture/Cue binding、静态 MIME、允许目录、size 和 SHA-256 都通过时，才可成为 `ready`；rights/reuse 仍只作历史元数据。
- 已实际打开当前 M001 OpenAI 官方页，将真实页面截图登记为 VC001 生产素材（PNG、127,433 bytes、SHA-256 `d3305a0d3b9c58c950aa75421c05effb27013d581916a9e0156026106788b3e1`）；Material r2 和 reviewed 历史保持不变。

### REAL USER CLEAN A-ROLL E2E Preflight

- ChatGPT 已批准进入真人 E2E Gate；本轮完成只读 Preflight，未新增产品功能、未修改历史工件。
- 分支 `agent/audio-alignment-edit-bridge` 的 reviewed HEAD `5ff947c`、workspace、ffmpeg 8.1.1、ffprobe 8.1.1 与实际 Remotion exact-entrypoint render 均正常；当前 approved Research r3、reviewed Script r2、reviewed Material r2、Production Plan、Motion Manifest 与 Production QA 精确绑定，Production QA 为 pass。
- 真实 OpenAI transcription Preflight 判定为 blocked：当前运行环境没有 `OPENAI_API_KEY` 和 OpenAI Python SDK。adapter 单元测试通过，真实 smoke 诚实跳过；不允许用 deterministic provider 代替真人转写。
- 本期 Real Material Preflight 判定为 missing_asset：外部网页/官方文件仍未取得本地 capture，未被升格为 ready；现有原创 Motion 输出可用。真人 E2E 因转写与真实素材两项 blocker 暂不开始。
- main、`v0.6.1` tag 和 GitHub Release 均未改变。

### V1 scope reconciliation + Basic Subtitle V1

- “全面冻结功能”临时边界已撤销，恢复 `reviewed Script + Clean A-roll + Real Material + Original Motion + Basic Subtitle → 完整可观看粗剪` 的 V1 产品目标；仍不扩展 A-roll cleanup、BGM/SFX、标题封面、发布或 NLE 专属导出。
- Hook-aware Script 复用现有 `audience_promise`、有序 Beats 与 `closing`，不升级 Script Draft schema；新 Review consistency mapping `0.4.2` 将缺失 opening hook、value promise、必要 re-hook / information turn 或 conclusion payoff 记录为 blocking `hook_structure`，旧 `0.4.1` Review Artifact 保持可读。
- 新增 `subtitle-profile/1`、`subtitle-artifact/1`、不可覆盖 JSON/SRT 存储和确定性显示 normalization。word/token 只组合真实 unit boundaries；segment-only 一段一 cue 并保持 coarse，不伪造 word/karaoke precision。
- Subtitle digest/Profile digest 进入 Edit Bridge root bindings；Remotion 在 A-roll、图片、视频与 Original Motion 全部时段烧录两行基础字幕，并为视觉 overlay 统一保留字幕安全区。
- 唯一正式 production entrypoint、自然语言 Bridge revision、Aligned Preview Manifest 与 repository-owned canonical QA 均绑定同一 Subtitle/Transcript/Profile；Transcript revision 改变、字幕篡改或 renderer 未启用字幕都会 fail closed。
- 完整 unittest 为 436 项，433 pass、3 environment/explicit-render skip；字幕定向 26 项通过，renderer lint/typecheck 通过。exact-entrypoint 真实 synthetic Remotion E2E 同时生成初版与自然语言修订版：H.264、1920×1080、30fps、2 秒、单一 Clean A-roll AAC 音轨，SHA-256 分别为 `283b2bace94f3853745f4740fcdfc33b6bb5595b2d3a96def2748f005be19919` 与 `cf13a810249dc897556592cfec7ba47f9ed5b692ee48d50c1b71693a07460b2a`，两版 canonical QA 均为 warnings（预期未选视频缺口，无 blocking failure）。
- 本阶段继续 Unreleased；没有修改 reviewed Script、approved Research、reviewed Material 历史、main、v0.6.1 tag 或 Release。真实 provider 与真实用户 Clean A-roll E2E 仍 pending。

### Audio Alignment + Visual Edit Bridge implementation

- 完成 Implementation Review 后的 Integration Hardening：新增唯一具体生产入口，自动解析最新匹配的 approved Research、reviewed Script、reviewed Material 与已通过 Production roots，并按固定顺序运行 Media → Mapping → Chunk → Transcript → Alignment → Placement → Bridge → Remotion → audio mux → canonical QA；旧 stage-lambda harness 不再是正式路径。
- Material Production View 现在保留 `asset_type`、`capture` 与 `video_reference`，真实图片、有范围视频、无范围视频分别确定性进入 `real_image`、ready `real_video`、`clip_selection_needed`；未经选择的公开视频不会自动猜选段。
- Cue OUT 从短 anchor 扩展到下一 Cue anchor 或 Beat 结束的完整语义范围；Alignment 总时长改为绑定 Clean A-roll presentation duration，不能再由最后一个 spoken unit 截短。
- OpenAI adapter 保持 real word timestamps 优先；只有 real segment timestamps 时明确标记 `segment/coarse`，两者都没有则 capability fail，不做插值。
- 正式 QA 改为 repository-owned canonical factory，自行重探测 Media、重建 Mapping/Chunk/Alignment/Material/Placement/Bridge，并核验 Preview Manifest、SHA 和音频 presentation；调用方不能再传自定义 lambda 充当正式 QA。
- 自然语言“短一点/长一点/早一点/晚一点/一直留真人”会真正改变 Preview effective timing 或 overlay suppression，并创建不可覆盖的 Bridge/Preview/Manifest/QA revision；reviewed Script、approved Research 和 canonical semantic window 不变。
- 真实 Remotion exact-entrypoint E2E 同时覆盖可用图片、已选范围视频、未选范围视频、QA-ready Motion 与带内部静音的 Clean A-roll；生成 1920×1080/30fps H.264 + 单一 Clean A-roll audio 的 `ALIGNED_PREVIEW.mp4`，SHA-256 `029e5211071126bc0183eb2dc354b24ebff5089d9d80a8ff724ff7e7ba38b58f`，595,390 bytes，canonical QA `warnings`（未选视频保持 `clip_selection_needed` 且未入画，无 blocking failure）。
- 完成批准计划 Task 0 与 Task 1–29：稳定 Discovery 冻结时间基线，并实现不可变 Clean A-roll 导入、媒体 presentation 证据、lossless transcription audio、可重推导 Timestamp Mapping、确定性自然停顿 Chunk Plan 与 boundary-risk 全链路保存。
- 新增 provider-neutral Transcript、当前 OpenAI `whisper-1` word timestamp adapter、可逆中英文 normalization、确定性 Script/Transcript 对齐、校准 Profile、Beat/Cue timeline 与不可覆盖 Alignment revision。
- 新增 reviewed Material production projection、图片/视频/Motion 统一 Placement、frame-rate-neutral IN/OUT/duration、冲突与 7 秒 long-still Preview safeguard，以及 Edit Bridge JSON/Markdown/CSV/revision。
- 新增 1920×1080/30fps Remotion Aligned Preview：Clean A-roll 为 layer 0，仅 ready 画面进入；纯视觉中间片无音轨，最终只混入原 Clean A-roll 主音轨。AAC/MP3 优先 copy，PCM 等不兼容 codec 转 AAC，正 presentation offset 与内部静音均重新 probe 并验证。
- 新增五组 QA/Gate、普通用户 `align-video` Skill/CLI、A–AI、CB1–CB7、PA1–PA7 与 property/invariant 评测。合成真实 Remotion/ffmpeg Preview 已通过；真实 OpenAI provider smoke 因本机没有授权环境而诚实跳过。
- 本阶段保持 Unreleased；没有修改 reviewed Script、approved Research 或 reviewed Material 历史，没有创建 V1.0、tag 或 Release。下一步停在真实用户 Clean A-roll E2E Gate。

### Audio Alignment + Visual Edit Bridge design

- 根据 Implementation Plan Conditional Pass 加固两个 blocker：新增 `transcription-chunk-profile/1` 独立 Task 7，并将 Provider protocol 顺延为 Task 8，以确定性 PCM RMS natural-pause 搜索取代任意按大小硬切，让 fallback boundary risk 贯穿 Provider、Timed Transcript、Alignment、Bridge 和 QA。
- Preview audio mux 计划新增 presentation timing 等价契约与真实媒体回归：正 audio offset、normalized raw PTS、internal gap、AAC copy/convert 和“总时长正确但声音被提前”均须由 QA 重新探测；总任务数由 28 调整为 29。
- ChatGPT 最终 Design Review 已通过；新增 `docs/superpowers/plans/2026-08-13-audio-alignment-edit-bridge.md`，将 approved contract 拆为 28 个有明确文件、接口、红/绿测试命令和 commit boundary 的 TDD Tasks。
- Plan 单独规划真实 ffmpeg/ffprobe 媒体 fixtures、可重算 Timestamp Mapping、provider-neutral/OpenAI transcription、span-preserving normalization、等价全局 DP、Profile calibration、Material production projection、统一 Visual Placement、duration/conflict policy、Remotion Aligned Preview、Clean A-roll audio mux、QA/Gate、CLI/Skill、A–AI eval、real provider smoke 与 real-user E2E Gate。
- Planning 阶段只查询 OpenAI 官方 Speech-to-Text/API 文档并固化当前 capability boundary；没有调用转录 API、没有上传媒体、没有修改产品代码、没有 render 或创建 Release。
- 根据 ChatGPT Conditional Pass 完成 Design Contract Hardening：将 container/stream PTS、Clean A-roll presentation timeline 与 extracted-audio timeline 分离，新增可验证的 affine Timestamp Mapping；正常 AAC priming/padding、edit list 和非零/负 PTS 不再因非 identity offset 被误伤。
- canonical Edit Bridge 时间统一为 decimal seconds 与 `HH:MM:SS.mmm`；30fps frame/timecode 只保留为 Aligned Preview 派生字段。
- 将 placement uncertainty 与 timing conflict 拆成正交状态：可靠 placement 可携带 duration/overlap warning 并进入 Rough Cut；same-start selection ambiguity 才阻止自动 Preview。
- 长静态画面新增版本化 7 秒 Preview exposure safeguard，继承 Material Profile 0.5 的已有默认 Cue 时长；canonical semantic OUT 保留，调整与 warning 全部可审计。
- 完成 repository inspection 与 Design Review Candidate：把 immutable Clean A-roll 定义为 canonical timeline，设计 Narration Media、Extracted Audio、Timed Transcript、Script Alignment、Visual Placement、Edit Bridge 和 Aligned Preview 契约。
- 设计 provider-neutral Speech-to-Text boundary、保留原文 span 的中英文 normalization、确定性序列对齐、版本化 threshold/Profile、Beat/Cue anchor 映射和可重推导 Gate；LLM 与 provider 均不能自报 canonical timecode 或 pass。
- 将真实图片、截图、真实视频、现有 Motion 与 A-roll 纳入同一 placement model，定义真实 IN/OUT/duration、layout、source clip 双时间轴、timing conflict 和 preview-only adjustment。
- 明确历史 rights/reuse 字段继续兼容读取但不再成为新制作 Gate；文件存在、SHA、MIME/codec、path、grounding、binding 与 Production QA 保持严格。
- 设计 26 个指定 adversarial cases、不可覆盖 revision、partial recovery 和真实 Clean A-roll E2E 边界；本轮没有 implementation、implementation plan、真实转录、渲染或新 Release。

### Real user trial

- 第一轮真实用户链路已从 Topic Discovery 继续跑通到 reviewed Research、reviewed Script、reviewed Material Package 和 Production QA；全程未使用 fixture，也未改写已审核稿件。
- Material Review 通过：8 个画面提示、7 个仅供编辑核对的公开来源、3 个基于已批准 Research 的原创画面；没有明确复用依据的网页和文件未进入渲染。
- Remotion 实际生成 8 个场景片段、1 个 rough visual preview 和 1 张 hero still；Production QA 通过，所有 10 个工件均为 ready。
- 真实来源仍保留 5 个 reference-only 画面缺口，真人录音尚未提供，因此另保留 1 个语音时间码缺口；系统没有用伪造截图或自动改稿掩盖缺口。

### Fixed during manual visual review

- 修复 Remotion timeline 两端日期和事件文字贴近画布边缘的问题，增加左右安全区并扩大事件文字容器。
- 新增 timeline safe-area 回归测试；首次存在问题的 Production 输出保持不可覆盖，修复后创建新的 Production 工件并重新通过 QA。
- 修复真实 Trial diagram 中文长 node label 与 node box、edge label 与连接线的可读性问题；两个 renderer 统一使用可换行 node 容器和独立背景 label plate，超过确定性容量时在 Renderer 前失败。
- comparison 不再由 Planner 无条件生成“两个解释”，改用版本化中性标题“要点对照”；每个 mechanism 只显示一次并在独立 card 内保留两条 grounded facts，Remotion / HyperFrames 共用同一 payload 语义。
- 新增真实中文长 Diagram、三项 Comparison、单次 mechanism label、fact binding 与 machine-editorial allowlist 回归；任意事实文字仍不能伪装成机器标题。
- 使用原 reviewed Script、approved Research 与 reviewed Material Package 生成新 Production `PROD-20260813T133848055707`；10 个真实工件 ready、QA pass，旧输出未覆盖。
- Git canonical lineage 修复：保留无共同祖先的旧审计分支，从远端 canonical main 新建 `agent/real-e2e-preview-hardening-mainline` 并迁移完全相同的 hardening tree；不触碰 main、v0.6.1 tag 或 Release。

## [0.6.1] - 2026-08-11

### Added

- Production Scene 新增严格 `scene_payload`，统一保存 timeline、bar、comparison、diagram 的元素、顺序、文字和 binding。
- Remotion 与 HyperFrames 新增四类逐元素 motion semantics；公开三柱虚构动效生成器可产出双引擎 MP4、contact sheet、ffprobe、SHA 和 QA 证据。
- Display Text 新增 `machine_editorial`、`research_fact`、`research_attribution`、`material_caption`、`visual_label` 来源。
- renderer 命令新增结构化 check：name、renderer、exit code、outcome、category、安全摘要。

### Changed

- V0.5 SVG 不再作为四类 Motion 动画主体；两套 renderer 只消费同一 Python Core payload。
- HyperFrames rough preview 改为新场景覆盖式入场，不再提前淡出旧场景。
- rough preview 仅在 MAPREVIEW 真正进入 Manifest 且 ready 时宣称成功。

### Security

- 无数字事实文字、无关 Claim、无依据因果 edge 和虚假素材 caption 均在项目生成前失败或安全降级。
- raw PDF 永不 stage/render；无已审 capture 时生成固定缺口。
- fail check 确定性生成 blocking issue，Production QA 无法同时保存失败检查和通过 Gate；公开命令摘要会脱敏本机路径和局域网地址。

### Verification

- unittest 共 **267 项**（266 项执行通过、1 项真实渲染集成测试默认跳过）；V0.6.0 的 255 项基线全部保留。
- 双引擎真实渲染同一份 3 元素 synthetic bar Plan，Remotion 4.0.507 与 HyperFrames 0.7.106 均通过完整 validation/preview/render/ffprobe/QA。

## [0.6.0] - 2026-08-11

### Added：Motion Production Layer

- 新增 Production Profile、Production Plan 0.6、Motion Asset Manifest 与 Production QA 严格契约。
- 新增 V0.5.1 canonical input Gate、render-time path/MIME/size/SHA/eligibility Gate 和 Display Text Grounding Gate。
- 新增共用同一计划与 QA 的 Remotion / HyperFrames adapters；锁定依赖，普通流程只运行一个 renderer。
- 新增 timeline/bar/comparison/diagram、document/screenshot、static image、A-roll placeholder 映射、Production gaps、rough visual preview 和 immutable storage。
- 新增 `produce-assets` CLI 和 `.agents/skills/produce-video-assets`。

### Fixed during real rendering

- Remotion 复用本机 Chrome、固定单并发渲染并显式绑定 project `public/`，避免慢速浏览器下载、多标签失败和 asset 404。
- HyperFrames 修正 `.clip` timing 标记和 root-relative asset path，并通过官方环境变量复用本机 Chrome。
- 原创完整 SVG 不再叠加重复标题；Timeline 文本保留 safe area。含数字标题与 Research Timeline 日期在精确绑定后可通过，新数字仍失败关闭。

### Validation

- 完整 unittest 共 **255 项**（254 项执行通过、1 项真实渲染集成测试默认跳过），原 219 项全部保留。
- 显式启用真实渲染测试：同一 tiny Plan 在 Remotion 和 HyperFrames 均完成 validation、preview、MP4/PNG render 与 QA pass。
- Apple 财报 bar 完成 Remotion 全链路真实 MP4 并 QA pass；欧盟 AI Act 和 rights-sparse 验证 reference-only 隔离、原创 timeline/diagram 与 A-roll fallback。
- blocked Material Package 在 renderer 前拒绝；asset tampering 在 SHA/size Gate 失败关闭。

## [0.5.1] - 2026-08-11

### Fixed：Material Gate Hardening

- Rights manifest 新增 `rights_evidence_url`；safe reuse 必须同时有素材页和权利页 actual-open，权利工具引用必须匹配，license URL 必须为可审计的同一权利页。模型权利自称、伪造链接和只有素材页的情形均不能进入 `ready_to_use`。
- 补齐 timeline、bar、comparison、diagram 的 nested Claim/Evidence grounding；timeline 精确匹配 Research date/Claim/Evidence/label，bar 使用数字边界并验证 value label，diagram node 必须有合法 Research basis。
- 新增 r1 Material Input / Inspection / Rights provenance artifacts。reviewed r2 在 loader 中重新生成 r1、验证精确 Review Artifact，再确定性导出 r2；篡改 eligibility、rights、provenance、ranking、status 或 review linkage 即使重算 digest 也失败关闭。
- SVG sanitizer 改为 XML 结构检查，允许标准 namespace，仍拒绝 script、event handler、foreignObject、外部 href 和危险 CSS URL。截图强制 1-based 页码与图片 magic/扩展名一致。

### Validation

- 原 205 项测试继续通过；新增 rights actual-open、nested Visual、canonical loader、SVG 与 capture 边界测试后，完整 suite 为 **219 项通过**。
- 重跑 A Stable Business、B Contested Public、C Rights / Sparse 评测，并新增 D 未打开权利页、E comparison C404/E404、F 手改 reviewed r2 三个 fail-closed 场景；公开汇总为 `evaluations/v0.5.1-summary.json`。

## [0.5.0] - 2026-08-11

### Added：Material Search & Visual Assistance

- 新增 Material Package / Visual Spec / Material Review 0.5 完整 JSON 契约，以及 B 站 1920×1080 Material Profile。
- 新增 reviewed Script 输入 Gate：复验 V0.4.1 Review Artifact、Review ID、被审 revision、内容 SHA-256 和精确 Research revision；draft、伪造状态、缺 Artifact 或错版底稿在搜索前失败关闭。
- 新增 Cue Sheet、素材类型、Evidence/Context/Illustration/Transition 边界、Claim/Evidence binding、URL 规范化去重和透明五维排序。
- 新增 actual-open inspection manifest 与独立 Rights manifest；API Web Search 结果只标 discovered，未知权利和普通新闻不会成为 ready-to-use。
- 新增安全静态文件获取和网页/PDF capture 登记：公开 URL、MIME、大小、SVG 脚本、路径、覆盖、SHA-256 与证明边界均受控。
- 新增 Research update escalation；素材搜索发现冲突或更新时不静默改稿、Research 或 Visual。
- 新增 timeline、bar、comparison、diagram Visual Spec grounding 和实际 1920×1080 SVG renderer；保留 Remotion/HyperFrames future hints，但不创建视频工程。
- 新增 10 项独立 Material Review、typed blocking issues、item isolation、package Gate、不可覆盖 Package/Review/Asset 存储和普通用户简明 Markdown。
- 新增 `prepare-materials` Skill、`search_materials/review_materials` Provider boundary、OpenAI API 和 `prepare-materials` / `review-materials` / `materials` CLI。
- 新增三类真实世界编辑评测和隔离安全下载评测；完整真实工件与资产保持 gitignored，公开仓库只提交去内容化汇总。

### Validation

- 原 165 项测试全部继续通过；新增 40 项后完整 suite 为 **205 项通过**。
- 新测试覆盖 input gate、provenance、rights、binding、dedupe、research update、下载、截图、四类 Visual、Review、存储、Provider、CLI 和 Skill。
- 三类评测分别证明：官方页无复用依据时保持 reference-only；EU CC 页面可 ready 而普通新闻仍 unknown；rights 稀缺时优先原创 SVG，不伪装许可。

## [0.4.1] - 2026-08-10

### 修复：Script Gate Hardening

- 增加版本化、确定性的 Script Review check → issue mapping。15 项检查任一 `fail` 都必须有对应 issue；八项事实安全检查必须有对应 blocking issue，否则直接拒绝 Review Artifact，不能错误产生 `reviewed`。
- 收紧 `not_applicable`：事实安全检查不可跳过，仅 `counterargument_fairness` 可在明确无可审反方时使用。
- 新增 machine-owned `review_state`、Review Artifact 内容 SHA-256 和 consistency mapping 版本。`reviewed` Script 在读取时复验真实通过的 r1 Review Artifact、Report/Script binding、Gate 和内容指纹；手改状态或伪造 Review 字段失败关闭。
- 旧 V0.4.0 `reviewed` JSON 如没有 linkage 不再被静默信任，必须重新执行 Review；旧 draft 仍可读取并在下一修订建立新的 identity state。
- 增加稳定 Beat identity：保留或移动的段落保持 ID，新增段落取得单调递增 ID，删除 ID 退休且永不复用；比较结果不再把中间插入误报为整篇修改。
- 更新 Writer/Reviewer prompt、仓库 Skill、Script Contract、架构、PRD、ROADMAP、AGENTS、README 和交接文档；V0.5 未开始。

### 验证

- 原 151 项测试继续通过；新增 Review 一致性、provenance、存储加载、修订 identity 与比较回归后，完整 suite 为 165 项通过。
- 重新执行 A/B/C 受控工作流评测并加入 `factual_grounding=fail + issues=[]` synthetic 场景；完整真实稿件继续保持 gitignore，公开仓库仅提交去内容化汇总。

## [0.4.0] - 2026-08-10

### Added

- 新增不可覆盖的 Approval Revision：只有完成独立 Fact Check、通过 Quality Gate 且处于 `reviewed` 的 Research Report 才能记录用户原始确认并进入 `ready_for_script`。
- 新增 Script Profile 0.4、Script Draft Artifact 0.4、独立 Script Review Artifact 0.4，以及 Editor / Teleprompter 双输出。
- 新增 `write-script` Codex Skill，普通用户可直接说“根据这份研究写稿”“做成 8 分钟”或“第二段更紧凑”；不需要修改 JSON 或执行命令。
- 新增稿件 grounding：Beat 级 Claim / Evidence 回链、Fact / Attribution / Analysis 边界、已核查高风险事实检查、`avoid_claims` 硬阻止和 must-keep coverage。
- 新增独立 Writer / Reviewer 工作流；Reviewer 必须完成 15 个必检维度，阻断问题由程序计算 Gate，模型不能自报通过。
- 新增不可覆盖的 Script revision、版本比较、自然语言时长解析，以及 `approve-report`、`prepare-script`、`review-script`、`revise-script`、`compare-script`、`write-script` CLI。
- 新增 `docs/SCRIPT_CONTRACT.md`、`docs/SCRIPT_EVALS.md` 和去内容化 `evaluations/v0.4.0-summary.json`。

### Validation

- 原 113 项测试全部继续通过；V0.4 新增 Approval、Script Artifact、grounding、审稿 Gate、存储、修订、CLI 和无 Web Search 边界测试。
- 稳定商业报告和争议公共议题报告均经过正式 Approval Revision、完整写稿和独立 15 项复核，最终成为 `reviewed` 稿件；实际阅读两份 Teleprompter 后分别完成 10 维人工编辑评分。
- 未获用户批准的 `reviewed` Research Report 被拒绝写稿，退出码为 2，且没有创建任何稿件文件。

### Security

- Script Writer 与 Reviewer 均只读已批准 Research Report，不启用 Web Search；API 请求载荷不包含搜索工具，带搜索 provenance 的结果会被拒绝。
- 真实完整稿件继续保存在 gitignored `script_drafts/`；公开仓库只提交去内容化评测指标。
- V0.4 不实现素材搜索、视觉生成、剪辑或自动发布，V0.5 仍未开始。

## [0.3.1] - 2026-08-10

### Fixed

- Codex Discovery 不再因为运行模式自动把 Source Seed 视为已打开；只有后台 inspection manifest 中实际检查的规范化 URL 才会成为 `manual_open`，其余保持 `unmatched`。
- 新增纯确定性 Candidate derivation；读取 Candidate Set 时重新推导资格、理由、推荐、总分、展示顺序、首选和 watch/reject 统计，任何篡改均 fail closed。
- Preflight 现在只计入 provenance 已匹配、来源类型合格且 URL / publisher / host 不重复的研究方向；social / creator Seed 与重复链接不能凑足门槛。
- 新增开始/更新时间顺序和最多 5 分钟未来容差；未来时间不再获得 freshness。
- 类别展示改为先多样后补位，同事件仍只出现一次；移除了没有实际作用的 `discover --count` 参数。
- 原始候选池少于 7 项时明确拒绝生成 Candidate Set，不再把 1–2 个候选误称为完整 Discovery。

### Validation

- 自动测试由 101 项增加至 113 项，覆盖 inspection manifest（含无工具引用的实际打开记录）、机器字段篡改、来源方向去重、时间、类别补位、Raw Candidate 最小池、CLI 与旧 Research / FactCheck / Quality Gate 回归。
- 三类真实 Discovery 评测已重新执行；公开汇总使用 `pass`、`fail` 和 `not_applicable`，不会在候选不足时宣称已经验证 Top 5。

### Compatibility

- Candidate Artifact 继续为 `0.3`，Research Report 和 FactCheck Artifact 继续为 `0.2`；旧的 Candidate Set 仍可按其保存的 legacy provenance 状态读取，但不会被提升为新检查过的来源。

## [0.3.0] - 2026-08-10

### Added

- 新增模式 B Topic Discovery：用户可直接说“今天讲什么？”“帮我找几个选题”或指定科技、商业、社会等方向；默认展示最多 5 个候选和一个首选。
- 新增版本化 `config/channel-profile.json`、独立 `Topic Candidate Set 0.3`、`Research Handoff Brief 0.3`、Discovery 历史和 latest 指针；不改变 Research Report / FactCheck Artifact `0.2`。
- 新增轻量 Source Seed Preflight、72 小时与持续事件时间规则、五维透明评分、机器总分、Eligibility Gate、事件聚类、类别多样性、watch/reject 状态和简短 Markdown 选题卡。
- 新增 `discover-topics` Codex Skill；用户只回复 `1` 或 `研究 1` 就能把候选的研究问题、核心张力、风险和 Seeds 交给已有 `research-topic` Skill。
- 新增 OpenAI Discovery API 调用、`discover` / `prepare-discovery` / `select-topic` / `research-selected` CLI 入口，以及 Topic Discovery 契约和三类真实评测方法。

### Changed

- `research-topic` 支持接收结构化 Research Handoff，不再要求用户把已选标题复制一遍。
- README、PRD、ROADMAP、AGENTS、架构、评测、CHANGELOG 和 HANDOFF 同步 V0.3；V0.4 Script Agent 仍未开始。

### Validation

- 自动测试由 85 项增加至 101 项，覆盖 Candidate Schema、评分权重与总分所有权、Eligibility Gate、72 小时/持续事件、陈旧事件、Seed URL、去重、多样性、watch、历史、编号交接、Codex/API、CLI 和模式 A 回归。
- 三类真实公开 Discovery 场景完成并只提交去内容化汇总；快速高风险且资料薄弱的线索保持 `watch` / `rejected`，没有为增加候选数量而降低门槛。

### Security

- Creator signal 为可选辅助信号，不能作为事实证据；不抓取稿件、字幕或独特表达，也不伪造播放量或热度。
- 真实 Candidate Set 继续保存在 gitignored `discoveries/`；API 模式无法匹配真实 Web Search provenance 的 Seed 不会装作已打开。

## [0.2.1] - 2026-08-10

### Fixed

- confirmed fact 独立确认现在只接受 `supports + matched + independent + 不同 independence_group`；`unknown`、`related`、`duplicate`、`syndicated` 均不能贡献独立确认。
- context-only 与未匹配来源不再抬高 claim source coverage；未匹配 attribution 不再解除无来源归属；duplicate / syndicated 不再抬高来源类型或 provenance 指标。
- Fact Check 新来源与 Research Draft 来源统一执行 URL 规范化、追踪参数去除、重复、同发布者、转载和 independence grouping；保存的 Artifact 与 reviewed report 使用相同确定性结果。
- 重复 URL 的判断优先于显式转载提示，使来源规范化可重复执行且结果稳定。

### Changed

- 新增内部 `API_RESEARCH_DRAFT_JSON_SCHEMA`；OpenAI Research Pass 只生成研究内容，身份、revision、时间、状态、Fact Check、provenance、quality 和审批字段由程序生成。
- 保持 Research Report / FactCheck Artifact Schema `0.2` 和全部质量阈值不变。
- `research-topic` Skill、报告契约、示例和架构文档同步 hardened 规则。

### Validation

- 85 项自动测试全部通过，原 68 项继续通过，新增独立来源、API 字段所有权、质量指标和 Fact Check 归组回归测试。
- 三类真实公开题材重新运行：稳定商业与争议公共政策进入 `reviewed`；快速公共安全热点因未解决高风险信息保持 `draft`。
- sample、validate、prepare-draft、review-report、迁移、修订防覆盖、Skill、Python 3.9、干净安装和密钥扫描完成验证。

### Security

- 模型无法通过 API Research payload 伪造 quality summary 或 approval 状态。
- 完整真实评测报告继续只保存在 gitignored `reports/`，公开仓库仅保存去内容化汇总。

## [0.2.0] - 2026-08-10

### Added

- 新增 Research Report 0.2：稳定 `report_id`、修订号、生成元数据、研究模式、更正历史、风险字段、质量摘要和人工确认 Gate。
- 新增正式 Evidence Ledger，区分来源对主张的支持、反驳、归属和背景关系。
- 新增 OpenAI Responses API 搜索调用、完整 action sources 与 URL citation provenance 提取和来源匹配。
- 新增独立版本化 FactCheck Artifact、第二次搜索、反证记录和高风险主张自动队列。
- 新增来源 URL 规范化、追踪参数清理、重复页面、同发布者和疑似转载分组。
- 新增透明质量指标和 Gate，包括来源覆盖、独立来源、高风险核查、来源类型、重复转载、无来源归属和 provenance 匹配。
- 新增不可覆盖的 r1/r2 报告历史、独立核查工件保存和更正记录。
- 新增 Research Report 0.1 → 0.2 确定性迁移与兼容读取。
- 新增 V0.2 Codex Draft 示例、真实编辑评测方法和三类题材的去内容化汇总。

### Changed

- `research-topic` Skill 改为 Research Draft → 新检索 Fact Check → Quality Gate 的两阶段流程。
- 所有构建、API、Skill、迁移和复核入口统一执行完整嵌套 Schema 与业务规则校验。
- 报告输出路径加入主题、报告 ID 和修订号，避免同名报告静默覆盖。
- OpenAI API 自动研究改为两个独立调用，并请求完整搜索来源元数据。
- 示例报告、README、PRD、ROADMAP、AGENTS、架构和 HANDOFF 同步到 V0.2。

### Validation

- 68 项自动测试全部通过，覆盖完整 Schema、错误输入、API Schema 兼容、provenance、Fact Check、人工确认 Gate、来源去重、修订和迁移。
- 三类真实公开题材完成端到端评测：两份通过并停在 `reviewed`，一份高风险动态热点按预期被 Gate 拦在 `draft`。
- 官方 Skill Creator 校验通过；离线示例、迁移、修订安全和干净虚拟环境安装检查通过。

### Security

- 完整真实 Research Report 和 FactCheck Artifact 继续只保存在被 Git 忽略的 `reports/`。
- 无法对应真实工具 provenance 的来源会降级，不能默认为已检查或支撑 confirmed fact。
- 任何报告都不会自动进入未来 Script Agent；通过质量 Gate 后仍需用户明确确认。

## [0.1.0] - 2026-08-10

### Changed

- GitHub 仓库 `HWang0310/deep-talk-studio` 已改为公有，便于 ChatGPT 直接进行产品与架构 Review。
- 新增正式版本的 GitHub Release 与未来软件包发布规则。
- 已发布首个正式版本：[DeepTalk Studio V0.1.0](https://github.com/HWang0310/deep-talk-studio/releases/tag/v0.1.0)。

### Added

- 初始化 DeepTalk Studio 独立 Git 项目。
- 新增仓库级 `research-topic` Codex Skill 和报告契约参考。
- 新增 Research Report 0.1 数据模型、JSON Schema 和交叉引用校验。
- 新增事实、报道、当事方说法、评论和未证实信息的分类。
- 新增时间线、多方观点、冲突、未决问题、内容角度和 Script Agent 交接结构。
- 新增 Markdown 渲染与按日期保存的 Markdown/JSON 双格式报告。
- 新增不依赖安装的 `scripts/deeptalk` 命令行入口。
- 新增 OpenAI Responses API `web_search` 可选提供器，支持结构化输出且不保存密钥。
- 新增虚构示例报告和 15 项自动测试。
- 新增 README、PRD、ROADMAP、AGENTS、HANDOFF、架构、设计和实施计划文档。

### Security

- 默认忽略真实研究报告、环境变量文件、缓存和本地虚拟环境。
- API 错误对外只显示状态与可操作信息，不回显密钥。
