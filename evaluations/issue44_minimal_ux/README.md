# Issue #44 / PR #45 — 极简创作页与独立模型设置页

> **状态：READY_FOR_NEXUS_MULTI_CHAT_UX_REVIEW（第八轮：多会话 UX）。** 前七轮完成两页极简 UX、DeepSeek 设置体验、paste→Test 修复、Chat-first MVP、B1–B4/B2-P0 阻断修复、一体化对话工作区 + 限额真实模型端到端（Nexus 已确认真实 E2E）、U1/U2 收尾修复 + Key 跨工作树用户级持久化 + 双 runner 凭据隔离（P0）；本轮按 issuecomment-6366157284 完成：左侧历史会话 sidebar（桌面 244px 可收起 / 375px 抽屉，标题取首条用户消息零付费调用、按最近更新倒序、选中高亮）、＋新建对话（零服务端调用，首发送才建持久化会话 ID）、所有聊天/草稿操作显式携带 session_id 绝不静默回落 latest、刷新/进程重启选择保持、流式中切换守卫（确定性验证）、草稿收起为小入口+点击展开抽屉（生成后自动展开、返回默认收起、v1/v2/v3 不删）、聊天历史升级为用户级 `~/.deeptalk/chat/`（0600 + 一次性迁移：同 ID 不覆盖/原文件保留/幂等，8321 真实迁移实测）。PR 保持打开，未合并。

## 视觉与交互交付

### 创作首页 /

- 全视口奶白背景、居中衬线标题、独立珊瑚色抽象标记和轻柔阴影。
- 宽大的多行创作框带内置工具栏、参考链接入口、圆形开始按钮和少量提示胶囊；输入框支持多行，'⌘/Ctrl + Enter' 开始创作。
- 右上角保留唯一设置入口；首页没有侧边栏、调试面板或卡片墙。
- 开始创作后保留原有视频搜索、授权下载、转写、叙事分析、研究、选题卡、审核和写稿功能。阶段条只显示当前阶段，已完成阶段仍可回看。

### 独立设置页 /settings（第二轮：DeepSeek 设置体验）

- **DeepSeek 默认极简**：普通用户只需填写 API Key。模型与官方 API 地址自动配置，页内说明「模型与官方 API 地址已自动配置（deepseek-flash），只需填写 API Key」；模型名称与 API 地址字段仅在切换到其他服务商时出现（`syncManualFields` 显隐切换）。
- **掩码 Key 生命周期**：保存后仅显示掩码（如 `sk-a…99zz`），支持留空保持不变、粘贴新 Key 替换、一键清除；服务重启后掩码与状态完整恢复（真实浏览器实测）。
- **测试连接结果友好化**：未填 Key 时提示「设置尚未完成：请填写API Key后保存，再点「测试连接」」，不再向用户暴露 `WAITING_FOR_OWNER_API_KEY` 等机器码（机器状态仍保留在 API payload 中，不影响既有契约）。
- **开发夹具诚实标注**：指向本地测试服务的连接显示独立的「开发测试环境」琥珀徽章与「开发测试连接通过：这是本地测试服务，不代表真实的 DeepSeek 连接。」文案，绝不冒充「已连接」；页内不再出现「（本地服务）」「（模拟服务）」后缀。
- **视觉打磨（评审反馈逐项落地）**：未配置徽章改琥珀警示色；徽章提示与自动配置说明去重；说明行括号内只保留模型名；按钮行重排为「取消 / 测试连接 / 清除 API Key 靠左，保存设置靠右」；状态文字与保存按钮间距加大；连接状态行 `word-break: keep-all` 防止「模型」等中文标签被拆到两行。
- **占位符窄屏自适应**：Key 占位符桌面为「粘贴你的 DeepSeek API Key」；窄屏放不下时（canvas 实测完整版 190px > 输入框内宽 168px）自动降级为「粘贴你的 API Key」，避免占位符被截断，窗口 resize 时双向切换。
- **配置隔离**：真实仓库 `config/workbench.local.json` 保持 DeepSeek 官方默认（无 Key）；mock / 本地端点配置只存在于 8322 隔离演示环境的独立根目录。

### 第五轮：Nexus B1–B4 阻断修复（MVP delta review #5626927896）

**B1 旧集工作流与聊天首页明确分离（P0）**：
- hero 永远是首页主体；存在历史 canonical 会话时，其 stage-bar/参考/授权表单/候选默认隐藏，只显示 `<details id="legacy-workbench-entry">` 折叠入口（「查看既有正式工作流（与聊天相互独立）· 本集：<主题>」）。
- 折叠入口显式展开才渲染旧集 stages（toggle 监听），收起即彻底隐藏；无会话/新一集模式下折叠入口也隐藏；legacy sessions 一律保留不删除。
- 8322 隔离夹具（旭日旗旧集 + 图书馆聊天共存）浏览器验证：默认态文本节点级零泄漏（TreeWalker 实测 leakCount=0），展开渲染 / 收起隐藏双向正确。

**B2 陈旧快照写入防护（P0）**：
- `CreativeChatStore` 全部跨请求持久化改为存储锁内 re-load 最新会话后追加（`start_user_turn` / `retry_user_turn` / `append_assistant_turn` / `append_draft_latest` / `latest_session_id`），绝不把内存旧快照整体写回。
- webui 层同会话单飞（`chat_in_flight` + `chat_flight_lock`）：重叠发送返回 400「上一条回复还在进行中，请先停止或等待完成后再发送」，任何退出路径 finally 释放；等待模型期间不持有全局锁。
- 交错场景（A、B 两个流式任意顺序完成）与「流式中并发草稿编辑」均验证零丢失。

**B3 重发幂等 + 计费诚实（P1）**：
- 停止后「重发上一条」携带服务器持久化的 `retry_turn_id`；后端验证目标仍是「最后一条且无回复」的 user turn 后原样复用，绝不追加重复用户消息；前端不再本地重复渲染 user 气泡，并清除停止遗留的半截 streaming 气泡。
- 已有回复 / ID 不匹配一律拒绝且零模型调用；重发按钮只在「上一条未完成」（停止/失败/中断）时出现（`updateRetryBtn`）。
- 停止文案改为诚实表述「已停止显示并尝试中断模型请求；已产生的费用可能仍会计入账单。」（`llm.py` 注释同步），删除不可能的「不会继续计费」承诺。
- 8322 实测停止→重发：消息数 12→13 只增加 assistant 气泡、存储中该 user 消息仅一条（t12）、mock 调用恰两次显式流式零隐藏。

**B4 草稿来源标注持久化（P1）**：
- `provider_kind` 在 `append_draft` 的 revision JSON 内原子持久化（此前只在内存 `draft["provider_kind"]` 赋值、重载即丢）；8322 新生成 v4 重载后 `provider_kind="fixture"` 保留；历史草稿不做迁移。

### 第四轮：Chat-first Creative Draft MVP（Owner 批准 Option A，issuecomment-6361415259）

**P0 前置（先行落地并测试，才允许任何聊天模型调用）**：
- 服务端强制：`provider_mode=deepseek` 时无条件锁定官方端点 `https://api.deepseek.com` 与官方模型 `deepseek-flash`；从自定义 Chat 切换后，残留的隐藏 model/URL 被丢弃，新粘贴的 DeepSeek Key 绝不路由到旧自定义端点。官方文档实现时确认：`deepseek-flash` + `stream: true` SSE on `/chat/completions`。
- 前端切换无条件重置隐藏字段；「测试连接」在飞防抖（连点只发一对保存+测试）；paste→Test 自动保存、掩码、夹具诚实标注全部保留。
- Playwright 合成 Key 验证：custom chat → 切 DeepSeek → 请求 payload 全部为官方值；4 次同步连点仅 1 次 test 请求。

**聊天与草稿（Nexus 派工 1–6 点逐项）**：
- `creative-chat/1` 会话 + 不可变 turn：`workbench/chat/*.json`（0600 权限，无任何秘密）；user turn 在流式开始前持久化，assistant turn 只在流完成后写入——停止/断开不写半截回复，重连不重复调用模型，重试永远是显式动作。
- 真实 provider 流式（非打字机）：上游 `stream:true` SSE，浏览器 `fetch` + `ReadableStream` 增量渲染（实测 30→42→66→90→107→131 字符逐步到达）；AbortController 停止；输入/刷新零隐式请求。
- 只有两个顶级页面：Chat-first 创作 UI（单一自然语言 composer：选题/观点/请求/粘贴 URL → link chips 如实标注「未读取」）+ 独立 `/settings`；旧 canonical 阶段工作流对既有会话仍可达（门禁不变），不再是首页入口。
- `creative-draft/1` 草稿：`status: unreviewed`，生成/自由编辑/修改（不可变 revisions v1/v2/v3）/复制/导出 .md；**永不写** `research.approved_path`、`thesis.approved_path`、`script.reviewed_path` 或任何质量门禁字段，不解锁正式生产；测试证明 canonical 门禁保持 fail-closed。
- 「进入正式审核」说明卡解释现有门禁路径，无自动转换/晋级；无自动 Search/Fetch、视频获取、rights bypass、fact-check 执行、外部发布。
- 诚实标注：注入夹具或 loopback 端点（如 127.0.0.1:8931）一律标「本地夹具回复（非真实模型）」，绝不冒充真实连接；发送前一次性说明计费（hero 常驻文案），不逐轮打断。

### 第三轮：粘贴 Key →「测试连接」旅程（Nexus delta，issuecomment-6358124584）

- 「测试连接」点击后**先安全持久化当前表单**（含刚粘贴的 Key，POST JSON body 走本机 loopback），保存成功后才对**刚保存的配置**执行连接测试；保存失败立即停止并显示中文错误（含「未连接测试」），不发出测试请求。保存与测试共用 `settingsFormPayload()` / `persistSettings()`。
- **已输入 vs 已持久化**：粘贴新 Key 时徽章即时「已输入未保存」（琥珀色），不再误导显示「未配置」；清空输入恢复持久化徽章。保留「空 Key 保持已存 Key」与显式「清除 API Key」语义。
- 仅显式点击才发起连接测试，绝不因输入/变更/保存静默请求；夹具仍显示「开发测试环境」徽章；零付费调用。

## Nexus Review 修复

### B1：新一集状态隔离

点击 '＋ 新一集' 后只显示新的创作首页，阶段条和旧阶段全部隐藏；上一集会话保留在内存中。点击 '取消' 恢复上一集的主题、当前阶段和文稿。真实浏览器断言：

~~~json
{
  "heroVisible": true,
  "stageBarVisible": false,
  "visibleStages": [],
  "noteVisible": true,
  "oldBodyText": 582,
  "oldSummaryText": 94
}
~~~

### B2：旧文稿与异步结果隔离

进入新会话时清空旧文稿正文、摘要、审核状态和复制/归档动作。定稿异步加载同时绑定 'session_id'、'script_id' 和 'revision'；旧会话请求返回后不会写入新会话 DOM。真实浏览器延迟返回回归结果：

~~~json
{
  "beforeRelease": {
    "topic": "本集：第二集：城市夜间空间",
    "bodyHidden": true,
    "bodyText": "",
    "summaryText": ""
  },
  "afterRelease": {
    "topic": "本集：第二集：城市夜间空间",
    "bodyHidden": true,
    "bodyText": "",
    "summaryText": ""
  }
}
~~~

### B3：研究夹具不再混入错误主题

本轮浏览器验收使用莫斯科大学旭日旗事件主题的五条本地离线演示材料，全部标题带 '【离线演示夹具】' 前缀。研究页显示固定免责声明：

> 离线演示夹具：仅用于验证页面流程，不代表真实独立研究来源。

截图中不再出现图书馆、预算等无关虚构来源；实际研究来源仍需用户提供并经过现有门禁。

## 真实浏览器证据

使用 Playwright Chromium，在本机 loopback UI 上反复检查桌面（元素宽 961px）与手机 375px：

| 验收 | 结果 | 证据 |
| --- | --- | --- |
| 空白首页与参考图层级 | 通过；无滚动条，首页只有创作入口 | [01-desktop-home-empty-hero.png](screenshots/01-desktop-home-empty-hero.png) |
| DeepSeek 模式保存后掩码 Key（模型/地址字段自动隐藏） | 通过；只显示 `sk-t…cdef` 掩码与自动配置说明 | [03-desktop-settings-deepseek-masked-key.png](screenshots/03-desktop-settings-deepseek-masked-key.png) |
| 隔离环境本地夹具测试连接 | 通过；真实调用本地 fixture，显示「开发测试环境」徽章，不冒充「已连接」 | [04-desktop-settings-connected-local-fixture.png](screenshots/04-desktop-settings-connected-local-fixture.png) |
| 五条视频参考、逐条已分析 | 通过；保留视频搜索、转写和叙事分析 | [05-desktop-stage1-references-analyzed.png](screenshots/05-desktop-stage1-references-analyzed.png) |
| 五方研究与主题一致的离线来源 | 通过；5/5、免责声明和五条主题一致材料可见 | [06-desktop-stage2-research-five-way.png](screenshots/06-desktop-stage2-research-five-way.png) |
| 审核通过的中文口播稿 | 通过；正文、复制、存档和音频/素材入口均保留 | [07-desktop-script-manuscript-delivered.png](screenshots/07-script-manuscript-delivered.png) |
| B1 新一集隔离态 | 通过；新首页单独显示，取消可恢复上一集 | [11-desktop-new-episode-only.png](screenshots/11-desktop-new-episode-only.png) |
| 375px 手机首页、设置、文稿 | 通过；三页无横向溢出 | [08](screenshots/08-mobile-375-home.png) / [09](screenshots/09-mobile-375-settings.png) / [10](screenshots/10-mobile-375-manuscript.png) |
| DeepSeek 只需填 Key 视图 | 通过；琥珀「未配置」徽章、提示去重、自动配置说明、按钮行重排 | [12-desktop-settings-deepseek-key-only.png](screenshots/12-desktop-settings-deepseek-key-only.png) |
| 无 Key 点测试连接 | 通过；友好中文提示，无机器码 | [13-desktop-settings-test-without-key.png](screenshots/13-desktop-settings-test-without-key.png) |
| 保存后掩码与「已保存未验证」 | 通过；掩码显示、按钮行右对齐主按钮 | [14-desktop-settings-saved-masked-key.png](screenshots/14-desktop-settings-saved-masked-key.png) |
| 隔离环境「开发测试环境」标注 | 通过；夹具连接显示独立徽章与诚实文案，非「已连接」 | [15-desktop-settings-dev-test-not-real-success.png](screenshots/15-desktop-settings-dev-test-not-real-success.png) |
| 375px 手机设置页 | 通过；无横向溢出、状态行在「·」处换行、占位符自适应降级 | [16-mobile-375-settings-deepseek.png](screenshots/16-mobile-375-settings-deepseek.png) |
| Chat-first 首页（对话 + 夹具诚实标注 + 草稿区） | 通过；计费说明常驻、停止/重发可用 | [19-desktop-chat-first-home.png](screenshots/19-desktop-chat-first-home.png) |
| 真实流式输出中（streaming 光标） | 通过；SSE 增量实测 30→42→66→90→107→131 字符逐步到达 | [20-desktop-chat-streaming.png](screenshots/20-desktop-chat-streaming.png) |
| 草稿 v1/v2/v3 不可变版本链 + 正式审核说明卡 | 通过；用户编辑产生新版本，v1 可回看不可改 | [21-desktop-draft-revisions.png](screenshots/21-desktop-draft-revisions.png) |
| 375px 手机聊天页 | 通过；无横向溢出，composer/对话/草稿均可用 | [22-mobile-375-chat.png](screenshots/22-mobile-375-chat.png) |
| 已输入 vs 已持久化 | 通过；粘贴 Key 后徽章「已输入未保存」，不再误导显示「未配置」 | [17-desktop-settings-typed-key-unsaved.png](screenshots/17-desktop-settings-typed-key-unsaved.png) |
| 粘贴 Key 直接「测试连接」 | 通过；先自动保存再测试（请求顺序实测），夹具诚实标注，掩码持久化 | [18-desktop-settings-paste-key-direct-test.png](screenshots/18-desktop-settings-paste-key-direct-test.png) |
| B1 默认态：聊天首页不混入旧集工作流 | 通过；折叠入口显示旧集主题，stage-bar/候选/授权表单全隐藏（文本节点级 leakCount=0） | [19-desktop-chat-first-home.png](screenshots/19-desktop-chat-first-home.png) |
| B1 展开态：旧集工作流只在显式展开后渲染 | 通过；展开后 stage-bar/主题行/阶段渲染，收起即隐藏 | [23-desktop-legacy-entry-expanded.png](screenshots/23-desktop-legacy-entry-expanded.png) |
| B3 停止态：计费诚实文案 | 通过；「已停止显示并尝试中断模型请求；已产生的费用可能仍会计入账单」，半截气泡已清除，重发按钮可见 | [24-desktop-chat-stopped-retry.png](screenshots/24-desktop-chat-stopped-retry.png) |
| B3 重发后：零重复 user 消息 | 通过；12→13 只增加 assistant 气泡，存储中 user 消息仅一条，mock 恰两次显式流式调用 | [20-desktop-chat-streaming.png](screenshots/20-desktop-chat-streaming.png) |
| B4 草稿来源标注重载保留 | 通过；新草稿 v4 重载后 provider_kind=fixture 仍在（21 内可见「本地夹具回复（非真实模型）」） | [21-desktop-draft-revisions.png](screenshots/21-desktop-draft-revisions.png) |
| 375px 手机聊天页（B1 后重拍） | 通过；无横向溢出，折叠入口/草稿版本按钮完整显示 | [22-mobile-375-chat.png](screenshots/22-mobile-375-chat.png) |
| Owner UX：一体化空态（居中欢迎 + 贴底 composer） | 通过；无巨型 hero/对话面板，与 19 旧布局形成新旧对比 | [25-unified-empty-state.png](screenshots/25-unified-empty-state.png) |
| Owner UX：对话全页单一流（turns+草稿+贴底输入） | 通过；composer 始终贴底，最后 turn 不遮挡 | [26-unified-conversation-full.png](screenshots/26-unified-conversation-full.png) |
| Owner UX：流式与停止态（夹具诚实标注/计费诚实文案） | 通过；滚动跟随不强制（上翻保持 scrollY 37） | [27](screenshots/27-unified-streaming.png) / [28](screenshots/28-unified-stopped-retry.png) |
| Owner UX：375px 一体化 | 通过；溢出 0px，safe-area 适配 | [29-unified-mobile-375.png](screenshots/29-unified-mobile-375.png) |
| 真实 DeepSeek：停止态 + 完整对话（产品内 Owner Key，共 5 次 ≤8） | 通过；真实回复诚实标注、v1/v2/v3、无明文 Key | [30](screenshots/30-real-deepseek-stopped.png) / [31](screenshots/31-real-deepseek-conversation-full.png) / [32](screenshots/32-real-deepseek-mobile-375.png) |
| 多会话：初始态（既有会话列在 sidebar + 草稿仅小入口） | 通过；巨型草稿编辑器不再常驻，会话元数据「13 条消息 · 草稿 v3」 | [38-desktop-initial-sidebar.png](screenshots/38-desktop-initial-sidebar.png) |
| 多会话：＋新建对话零调用空态 | 通过；performance 资源计数 delta=0、旧会话保留 | [39-new-chat-empty-state.png](screenshots/39-new-chat-empty-state.png) |
| 多会话：话题甲首发送创建会话 A | 通过；侧栏新增条目标题=首条用户消息、localStorage 记录新 id | [40-session-a-created.png](screenshots/40-session-a-created.png) |
| 多会话：草稿 v1 生成后抽屉自动展开 | 通过；生成前入口行显示小「把对话整理为草稿（调用模型，可能计费）」 | [41-draft-v1-drawer-autoopen.png](screenshots/41-draft-v1-drawer-autoopen.png) |
| 多会话：v1/v2/v3 保存后收起 | 通过；入口「草稿 v3 · 未审核」 | [42-draft-v3-collapsed-entry.png](screenshots/42-draft-v3-collapsed-entry.png) |
| 多会话：新建 B（3 会话倒序） | 通过；B 与 A 完全隔离（A 内容零出现） | [43-session-b-created-3-sessions.png](screenshots/43-session-b-created-3-sessions.png) |
| 多会话：选中 A 精确恢复 | 通过；仅 A 内容、v1/v2/v3 版本链齐全、抽屉默认收起 | [44-session-a-recovery-drafts.png](screenshots/44-session-a-recovery-drafts.png) |
| 多会话：刷新保持选择 | 通过；localStorage 非机密 id、内容/草稿恢复 | [45-refresh-persist-selection.png](screenshots/45-refresh-persist-selection.png) |
| 多会话：8322 进程重启后仍精确恢复 | 通过；A 仍选中、3 会话齐全 | [46-restart-persist-selection.png](screenshots/46-restart-persist-selection.png) |
| 多会话：流式切换守卫（确定性同步验证） | 通过；守卫文案出现、localStorage 不动、会话不切换 | [47-streaming-guard-blocked.png](screenshots/47-streaming-guard-blocked.png) |
| 多会话：375px 初始（sidebar 移出屏幕 + ☰ 按钮） | 通过；横向溢出 0 | [48-mobile-375-initial.png](screenshots/48-mobile-375-initial.png) |
| 多会话：375px 抽屉打开 | 通过；遮罩可见、会话可达 | [49-mobile-drawer-open.png](screenshots/49-mobile-drawer-open.png) |
| 多会话：375px 选择会话后自动关闭 | 通过；抽屉滑出、溢出 0、内容渲染 | [50-mobile-after-select-closed.png](screenshots/50-mobile-after-select-closed.png) |

完整的 B1/B2 断言、设置体验流与浏览器输出见 [browser-evidence.md](browser-evidence.md)。

## 测试结果

- 'PYTHONPATH=src .venv/bin/python -m pytest tests/test_webui.py tests/test_workbench.py -q' → **141 passed**（第八轮新增：多会话完全隔离 + 聊天历史用户级迁移 + HTTP 作用域操作 3 项；前七轮累计 138 项保持全过）
- 'PYTHONPATH=src .venv/bin/python -m pytest tests -q' → **1121 passed, 7 skipped**（第八轮全量，退出码 0；1118+3 精确衔接）
- 'HOME=<sentinel> PYTHONPATH=src python3 -m unittest discover -s tests'（裸文档命令） → **Ran 1128 tests … OK (skipped=7)**，退出码 0；sentinel `.deeptalk` 文件列表与 marker sha256 前后一致（双 runner 均不触碰真实用户级配置与聊天历史）
- 真实 `~/.deeptalk` 全文件 sha256 快照在 focused 套件运行前后完全一致（聊天目录隔离确定性证明）
- 内联 JavaScript：'node --check'（提取 `<script>` 块）→ **通过**
- 'git diff --check' → **通过**
- 未修改无关后端、模型门禁、SSRF 防护或生产工作流；未提交本地密钥、模型输出、缓存或临时会话。

## 截图与凭据说明

截图是真实浏览器输出，存放在 'screenshots/'（桌面元素宽 961px、手机 375px 视口元素宽 328px）。设置页使用仅用于验收的假 Key，截图只显示 `sk-t…cdef` 等掩码；本地连接图使用 '127.0.0.1:8931' 的 loopback fixture，不代表真实模型质量。真实 DeepSeek 创作仍保持 'WAITING_FOR_OWNER_API_KEY'（机器状态仅在 payload），等待 Nexus 审核，不自行合并。

已知限制（如实声明）：

- 真实 DeepSeek 连接质量未验证，等待 Owner 填入自己的 Key 自测。
- 375px 手机端输入框内宽 168px 放不下完整占位符「粘贴你的 DeepSeek API Key」（canvas 实测 190px），按设计自动降级为「粘贴你的 API Key」。
- 图像模型评审曾三次误报（保存按钮换行、deepseek-flash 断行、桌面占位符截断），均已用逐字符 Range / canvas 测量实测推翻；「模型」标签断词与手机占位符截断两项为真实问题并已修复。
