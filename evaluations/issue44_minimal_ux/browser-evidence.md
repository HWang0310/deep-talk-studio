# Issue #44 浏览器复测记录

日期：2026-10-22（第一轮）/ 2026-10-23（设置体验轮）
浏览器：Playwright Chromium（headed）
UI：127.0.0.1 loopback，真实页面脚本和后端流程
服务：8321 = 真实仓库工作树（LaunchAgent `com.hwang.deeptalk-studio.pr45-ui` 守护，干净 DeepSeek 配置）；8322 = 隔离全新环境（`.temp/issue44-demo-root`，mock chat 配置指向 127.0.0.1:8931）

## B1 新一集

从已有审核通过会话进入创作页，点击 '＋ 新一集'：

~~~json
{
  "heroVisible": true,
  "stageBarVisible": false,
  "visibleStages": [],
  "noteVisible": true
}
~~~

旧会话的主题和正文仍在内存中，但不再可见；点击 '取消' 后恢复原主题、当前阶段和正文。

## B2 延迟定稿返回

浏览器路由延迟旧会话 /api/workbench/script/final，然后启动第二集并在旧请求释放前检查：

~~~json
{
  "beforeRelease": {
    "topic": "本集：第二集：城市夜间空间",
    "heroHidden": true,
    "stageScriptHidden": false,
    "scriptControlsHidden": false,
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

这证明旧请求返回后没有把上一集的正文或摘要写入第二集。

## B3 研究来源一致性

研究页使用同一主题的五条 loopback 离线演示来源：

1. '【离线演示夹具】示例新闻社：莫斯科大学留学生披旭日旗事件报道'
2. '【离线演示夹具】示例大学校务处：涉事留学生处理通报'
3. '【离线演示夹具】公开档案：涉事学生道歉视频说明'
4. '【离线演示夹具】学生代表联名信（演示材料）'
5. '【离线演示夹具】校方程序说明（演示材料）'

页面同时显示“离线演示夹具：仅用于验证页面流程，不代表真实独立研究来源。”，没有图书馆或预算类无关来源。

## 响应式与设置

- 首页桌面：1440 × 900，scrollHeight === 900。
- 首页手机：375px，scrollWidth === 360（滚动条占用 15px，页面内容没有横向溢出）。
- 设置页手机：innerWidth === 375、scrollWidth === 375，取消按钮存在且高级选项可折叠。
- 设置页桌面：两列主表单；DeepSeek 模式下模型名称与 API 地址字段自动隐藏，仅显示自动配置说明行。
- 本地连接测试：chat / fixture-model 状态显示独立的「开发测试环境」徽章与「开发测试连接通过」文案，端点为 127.0.0.1:8931；没有调用真实 DeepSeek，也不显示「已连接」。

## 设置体验轮（2026-10-23，Owner 六点要求）

### 8321 真实环境干净流

1. DeepSeek 默认视图：琥珀色「未配置」徽章 + 提示「粘贴你的 DeepSeek API Key 并保存，然后点「测试连接」验证服务。」；模型/地址字段隐藏，自动配置说明「模型与官方 API 地址已自动配置（deepseek-flash），只需填写 API Key」；Key 占位符「粘贴你的 DeepSeek API Key」。
2. 不填 Key 点「测试连接」：状态行显示「设置尚未完成：请填写API Key后保存，再点「测试连接」」，连接状态行显示「还没有填写 API Key」；无任何机器码。
3. 填假 Key 保存：徽章变「已保存未验证」，Key 标签显示掩码「当前：sk-t…cdef（留空保持不变；粘贴新 Key 可替换）」，状态「已保存（Key 仅存本机）」。
4. 粘贴新 Key `sk-another-fake-key-9999zz` 再保存：掩码变为「sk-a…99zz」，替换生效。
5. `launchctl kickstart` 重启 8321 服务后刷新页面：掩码「sk-a…99zz」与「已保存未验证」状态完整恢复，DeepSeek 模式字段显隐与 auto-note 正常。
6. 清除 API Key：回到「未配置」，`config/workbench.local.json` 确认 `api_key: ""`、`deepseek`、`not_tested`（交付 Owner 试用时的最终状态）。

### 8322 隔离环境开发夹具流

- chat 模式显示模型名称与 API 地址字段（`mock-e2e-model` / `http://127.0.0.1:8931/v1`）。
- 点「测试连接」：徽章为「开发测试环境」（state-warn），不是「已连接」；状态文字「开发测试连接通过：这是本地测试服务，不代表真实的 DeepSeek 连接。」。
- 全页检索无「（本地服务）」「（模拟服务）」后缀，无 `WAITING_FOR_OWNER_API_KEY` 字样（HTTP 400 响应体同样无机器码，pytest 断言覆盖）。

### 375px 手机端

- 无横向溢出（scrollWidth === clientWidth）。
- 连接状态行两行显示，换行发生在「·」分隔符处：「模型：deepseek-flash」整段完整出现在第二行（`word-break: keep-all` 修复；修复前实测换行点在第 29 字符「型」前，「模型」被拆开）。
- Key 占位符自动降级为「粘贴你的 API Key」：canvas 实测完整版「粘贴你的 DeepSeek API Key」宽 190px > 输入框内宽 168px（截断真实存在）；降级后 116px ≤ 168px。
- 桌面（1280px）占位符恢复完整版 190px ≤ 294px，resize 监听双向切换实测通过。

### 评审误报的实测推翻（确定性测量）

- 「保存设置按钮换到下一行」：五元素 getBoundingClientRect 实测全部 y=530 同一行，spacer 推挤后 保存设置 x=642、状态 x=738。
- 「deepseek-flash 被连字符拆成两行」：#st-auto-model span 逐字符 Range 测量单行（top=490 一个行框），段落实际两行「模型与官方 API 地址已自动配置」/「（deepseek-flash），只需填写 API Key。」。
- 「桌面占位符截断」：桌面输入框内宽 294px > 占位符 190px，无截断（手机端截断为真，已用降级修复）。
- 备注：`<input>` 的 `scrollWidth` 不反映内容溢出（恒等于 clientWidth），占位符宽度核验须用 canvas measureText。

## 生成的截图

- screenshots/01-desktop-home-empty-hero.png
- screenshots/03-desktop-settings-deepseek-masked-key.png（设置体验轮重拍：DeepSeek 模式隐藏模型/地址字段）
- screenshots/04-desktop-settings-connected-local-fixture.png（设置体验轮重拍：「开发测试环境」徽章，不再显示「已连接（本地服务）」）
- screenshots/05-desktop-stage1-references-analyzed.png
- screenshots/06-desktop-stage2-research-five-way.png
- screenshots/07-desktop-script-manuscript-delivered.png
- screenshots/08-mobile-375-home.png
- screenshots/09-mobile-375-settings.png
- screenshots/10-mobile-375-manuscript.png
- screenshots/11-desktop-new-episode-only.png
- screenshots/12-desktop-settings-deepseek-key-only.png（961px 宽桌面视口）
- screenshots/13-desktop-settings-test-without-key.png（961px 宽桌面视口）
- screenshots/14-desktop-settings-saved-masked-key.png（961px 宽桌面视口）
- screenshots/15-desktop-settings-dev-test-not-real-success.png（961px 宽桌面视口）
- screenshots/16-mobile-375-settings-deepseek.png（328px 宽手机视口）
- screenshots/17-desktop-settings-typed-key-unsaved.png（961px 宽桌面；「已输入未保存」徽章）
- screenshots/18-desktop-settings-paste-key-direct-test.png（961px 宽桌面；粘贴 Key 直接测试 → 自动保存 + 夹具测试通过）

> 取证勘误：截图 12–15 首次拍摄时 Playwright 会话视口残留上一轮的 375px，被误标为桌面截图（328×1068）；已全部在 1280×800 桌面视口重拍（961px 宽）并覆盖。

## Nexus delta 轮（2026-10-23，issuecomment-6358124584）

### 修复内容

「测试连接」点击后：先安全持久化当前表单（含刚粘贴的 Key，POST JSON body 走本机 loopback），成功后才对**刚保存的配置**执行连接测试；保存失败立即停止并显示中文错误（含「未连接测试」），不发测试请求。保存与测试共用 `settingsFormPayload()` / `persistSettings()`。输入框有新 Key 时徽章显示「已输入未保存」（区分 typed 与 persisted），不再误导显示「未配置」；空 Key = 保留已存 Key、显式清除不变；夹具仍显示「开发测试环境」徽章。

### 8322 粘贴 Key → 直接测试（隔离夹具，未先保存）

Playwright 网络请求顺序实测：

```json
[
  "POST /api/workbench/settings {\"provider_mode\":\"chat\",\"chat_base_url\":\"http://127.0.0.1:8931/v1\",\"model\":\"mock-e2e-model\",\"api_key\":\"sk-paste-test-key-2\"}",
  "POST /api/workbench/settings/test {}"
]
```

先自动保存（含新 Key）→ 再测试；结果徽章「开发测试环境」、掩码 `sk-p…ey-2`、状态「开发测试连接通过：这是本地测试服务，不代表真实的 DeepSeek 连接。」（截图 18）。

### 8321 真实配置（clean DeepSeek，零真实外部调用）

- 粘贴 `sk-real-test-key-7` 直接点测试 + 拦截**中止** `/settings/test`（确保不向 api.deepseek.com 发起任何请求）：请求顺序为 先 `POST /api/workbench/settings`（payload 含 `provider_mode:deepseek` + 新 Key）→ 再 `POST /api/workbench/settings/test`（被中止）；状态「网络错误」；**重载后**掩码 `sk-…-…` 与「已保存未验证」持久化。
- 保存失败路径（`/api/workbench/settings` 路由返回 500）：点击测试后**只出现保存请求**，测试请求从未发出；状态「保存失败：…，未连接测试。」；徽章保持「已输入未保存」。
- 已输入 vs 已持久化：输入 Key 后徽章即时「已输入未保存」（截图 17）；清空输入恢复持久化徽章；最终交付状态恢复 clean DeepSeek（`api_key: ''`、`not_tested`）。

## Chat-first Creative Draft MVP 轮（2026-10-23，issuecomment-6361415259）

### P0 Playwright（合成 Key，零外部调用）

- custom chat（`127.0.0.1:8931/v1` + `stale-custom-model` + 合成 Key）保存后切回 DeepSeek：前端立即把隐藏字段重置为官方值（实测 `st-model=deepseek-flash`、`st-chat=https://api.deepseek.com`），保存 payload 全部为官方值；`/state` 不再出现旧端点。
- 「测试连接」防抖：`dispatchEvent` 同步连点 4 次仅发出 1 对保存+测试请求（`testHits=1`），期间按钮 disabled，完成后恢复。

### 8322 隔离环境聊天全流程（8931 真实 SSE 流式夹具）

- **增量流实测**：每 200ms 采样助手气泡长度 → 30→42→66→90→107→131 字符逐步增长（SSE `text/event-stream`，非一次性渲染）；截图 20 含 streaming 光标。
- **多轮**：第二条消息后 4 turns；夹具标注「mock-e2e-model · 本地夹具回复（非真实模型）」（loopback 端点判定，与设置页测试连接逻辑一致）。
- **草稿**：对话后「把对话整理为草稿」→ v1（模型整理 + 未审核 + 夹具标注）；自由编辑保存 → v2、v3（你的修改）；切回 v1 内容与保存时逐字符一致（不可变回看）；「进入正式审核」说明卡存在；截图 21。
- **刷新恢复**：重载后 4 turns + 3 revisions + v3 内容精确一致；截图 19/22。
- **停止/重发**：流式中点「停止」→ 状态「已停止：未完成的回复不会保存，也不会继续计费」；半截 assistant（42 字符）不写入 turn（turn 计数只含 user）；「重发上一条」显式点击 → 完整回复（121 字符）；`/chat/stream` 请求计数恰好 2（无隐藏重复计费）。
- **375px**：横向溢出 0px；composer/对话/草稿全部可见；截图 22。
- **无泄漏**：`/state` 响应中唯一 `sk-` 出现是掩码字段 `api_key_masked: "sk-p…ey-2"`；正则无真实密钥匹配；聊天存储文件 0600 权限且无 Key 内容（pytest 断言覆盖）。

### 已知边界（如实声明）

- 8322 演示回复由本地夹具生成（诚实标注「非真实模型」），不代表真实 DeepSeek 质量；真实质量仍为 `WAITING_FOR_OWNER_API_KEY`，等 Owner 填 Key 自测。
- 旧 canonical 阶段工作流对既有会话仍可达（如 8321 上的历史会话），不再是聊天首页入口；门禁代码与 HTTP 端点全部保留不变。
- 截图 19–22；聊天验收在全新干净聊天会话上执行（`.temp/issue44-demo-root/workbench/chat` 验收前清空）。

## Nexus B1–B4 修复轮（2026-10-23，MVP delta review #5626927896）

环境：8322 隔离夹具（`.temp/issue44-demo-root`：旭日旗 canonical 会话 B 与图书馆聊天 A 共存——B1 的天然测试床）；8931 流式 mock 放慢至 0.5s/块保证停止操作窗口；服务重启加载本轮新代码（creative_chat 锁 / webui 单飞 / index.html B1+B3）。

### B1：默认聊天首页不混入旧集工作流（TreeWalker 文本节点级验证）

~~~json
{
  "stageBarVisible": false,
  "visibleSections": [],
  "legacyEntryExists": true,
  "legacyEntryHidden": false,
  "legacyEntryOpen": false,
  "legacyTopicText": "本集：莫斯科大学留学生旭日旗事件",
  "chatCardVisible": true,
  "chatTurns": 9,
  "leakCount": 0
}
~~~

`leakCount=0`：全文档 TreeWalker 遍历所有可见文本节点，旧集关键词（莫斯科大学/旭日旗/授权/BV1hi）在折叠入口之外零出现（一次祖先容器误报已用文本节点级检查排除）。展开 `<details>`（toggle 事件）→ `stageBarVisible: true`、`sessionTopic: 本集：莫斯科大学留学生旭日旗事件`、`stage-references` 渲染（截图 23）；收起 → stageBar 与全部 stage 重新隐藏。

### B3：停止 → 重发（实测请求/存储/调用三重验证）

发送「停止测试：这条消息会被中途停止然后重发」→ 流式中（streaming 气泡 ×1、停止按钮可见）点「停止」：

~~~json
{
  "after_stop": {
    "total": 12, "roles": "uauauuauau",
    "streamingLeft": 0,
    "status": "已停止显示并尝试中断模型请求；已产生的费用可能仍会计入账单。可点「重发上一条」。",
    "retryVisible": true, "stopVisible": false, "lastIsUser": true
  },
  "after_retry": {
    "total": 13, "roles": "uauauuauaua",
    "status": "回复完成，已保存到本机。",
    "retryVisible": false
  }
}
~~~

- 停止态：半截 streaming 气泡已从 UI 清除；计费诚实文案（不再有「不会继续计费」）；重发按钮可见（截图 24）。
- 重发：12→13 只增加 1 条 assistant 气泡，**零新增 user 气泡**；`/api/workbench/state` 存储：该 user 消息仅一条（`t12`），一问一答（13 turns）；done 后重发按钮正确隐藏。
- 8931 mock 调用日志（重启后）：`stream=False`（健康检查）+ `stream=True` ×2（首次 + 重发）——**恰两次显式流式调用，零隐藏第三次**。

### B4：草稿来源标注重载保留

对话后生成新草稿 v4 → `/api/workbench/state`（磁盘重载视角）：

~~~json
[
  {"revision": 1, "origin": "model", "provider_kind": "<<MISSING>>"},
  {"revision": 2, "origin": "user_edit", "provider_kind": "<<MISSING>>"},
  {"revision": 3, "origin": "user_edit", "provider_kind": "<<MISSING>>"},
  {"revision": 4, "origin": "model", "provider_kind": "fixture"}
]
~~~

v4（新代码生成）`provider_kind="fixture"` 持久化保留；v1–v3 为修复前历史数据、无该字段属预期（不做迁移）。UI meta 显示「v4 · 模型整理 · 状态：未审核 · 本地夹具回复（非真实模型）」（截图 21）。

### B2：并发防护（pytest 覆盖 + HTTP 单飞实测）

- flow 级：交错完成（B 先 A 后）→ 4 turns 顺序完整 `["user","user","assistant","assistant"]`；流式中并发 `chat_draft_save` → 两个 draft revisions 均保留。
- HTTP 级：20 段慢流进行中第二条发送 → 400「上一条回复还在进行中，请先停止或等待完成后再发送」，第一条流照常完成、恰一次模型调用。
- 本轮取证勘误：8322 验收前曾因批量编辑误删 webui 服务器 `__init__` 的 `output_dir`/`provider_factory`/`discovery_lock`/`workbench_lock` 四行导致 12 个既有测试 500（`discovery run failed: provider/IO` 兜底掩盖 AttributeError），focused 全量复跑发现并已恢复；修复后 135/135。

### 本轮截图

- screenshots/19-desktop-chat-first-home.png（全页重拍：hero + 13 turns 聊天 + 折叠入口「本集：莫斯科大学留学生旭日旗事件」+ v4 草稿；零阶段标签/候选/授权表单）
- screenshots/20-desktop-chat-streaming.png（重拍：流式中 + 诚实夹具标注）
- screenshots/21-desktop-draft-revisions.png（重拍：v1–v4 版本链 + 「本地夹具回复（非真实模型）」来源标注）
- screenshots/22-mobile-375-chat.png（重拍：375px 全页，折叠入口/版本按钮无截断无溢出）
- screenshots/23-desktop-legacy-entry-expanded.png（新增：B1 展开态——旧集 stages 只在显式展开后渲染）
- screenshots/24-desktop-chat-stopped-retry.png（新增：B3 停止态——计费诚实文案 + 重发按钮可见）

## B2/P0 修正轮：拒绝先于持久化（2026-10-23，exact-head review #5627594838）

Nexus 在 2597fc7 上确认 B1/B3/B4 通过，B2 遗留 P0：`_handle_chat_stream` 先调 `chat_send_start`（持久化 user turn）再查 `chat_in_flight`，重叠的 B 消息被 400 拒绝前已进入聊天记录。

### 修复（webui.py，最小改动）

准入预约（检查+注册，`chat_flight_lock` 内原子）前移到任何存储变更之前；flight key 改为固定 `"chat"`（聊天单会话设计，首次发送尚无会话也可检查）；从预约成功起整段逻辑（含 `chat_send_start` 失败路径）由 finally 释放预约；等待模型不持锁；retry/Key 防护不变。

### 8322 真实 HTTP 实测（8931 慢速流式夹具 0.5s/块）

~~~json
{
  "baseline_turns": 15,
  "B_overlap_send": {
    "status": 400,
    "error": "上一条回复还在进行中，请先停止或等待完成后再发送"
  },
  "mid_storage_while_A_running": {
    "turns": 16, "tail_roles": "uau",
    "B_content_in_storage": false
  },
  "final_storage_after_A_done": {
    "new_turns": [
      ["user", "B2 修复实测：A 流慢速进行中的消息"],
      ["assistant", "收到。围绕「B2 修复实测：A 流慢速进行中的消…"]
    ],
    "B_content_in_storage": false,
    "baseline_15_turns_preserved": true
  },
  "mock_calls_since_marker": ["stage=chat stream=True chars=100"]
}
~~~

被拒的 B 消息在 A 运行中与 A 完成后**双检零出现**；mock 调用恰 +1（B 零调用、零隐藏计费）；基线 15 turns 逐条保留。

### 回归测试

- `test_second_stream_while_first_in_flight_returns_400` 按 review 四步增强：②B 400 + 存储恰 `[user A]` + B 零出现 + 零额外调用 → ③A 完成恰 `[user A, assistant A]` + B 仍零出现 → ④预约释放后 C 正常发送（A+C 各一次显式调用，最终四 turns）。
- 新增 `test_concurrent_first_sends_admit_exactly_one`：Barrier 对齐两线程并发首次发送（尚无会话）→ 恰 `[200, 400]`，存储只有被放行方一问一答，被拒方不创建会话不写 turn，模型恰一次调用。
- focused 136 passed；全量见提交记录。

## Owner UX 一体化对话工作区轮（2026-10-23，issuecomment-6364369899）

### 8321 运行时 404 修复（same-process 路由验证先行）

- 现象复现：重启前 `POST /api/workbench/chat/stream` → `{"error": "路径不存在"}`（404）；服务器日志含 Owner 尝试的 4 次 404。
- 根因：LaunchAgent 进程（pid 19938，17:28 启动）早于 chat MVP 代码落地（18:00 后），一直未重启；`scripts/deeptalk` 的 `PYTHONPATH=$REPO/src` 模块解析本身正确。
- 修复：`launchctl kickstart -k gui/$(id -u)/com.hwang.deeptalk-studio.pr45-ui`（新 pid 37066）；同进程验证 `{"message":"   "}` → 400「消息内容不能为空」（路由存在，零模型调用）。未在路由验证前做任何模型失败诊断。

### Owner Key 持久化（零重新输入）

- `config/workbench.local.json` 由仓库 `.gitignore:43` 覆盖：git 操作/分支切换/升级不触碰该文件；
- 重启后 `/api/workbench/state`：`api_key_masked: "sk-f…8d17"`、`connection_kind: "real"`、官方端点 `https://api.deepseek.com/chat/completions`、模型 `deepseek-flash`；响应中无明文 Key（`api_key` 字段不存在，仅掩码）；
- 设置页徽章「已连接」；截图/日志/提交零密钥（diff 扫描过）。

### 一体化工作区验收（8322 夹具 + 8321 真实，Playwright Chromium）

| 契约 | 实测 |
| --- | --- |
| 1 空态安静居中 + 单 composer + 设置角落 | welcome 居中、无巨型 hero、无「对话」面板；dock 贴底 gap 0；旧集折叠入口空态也可见且在 dock 上方 |
| 2 首次发送转对话态、composer 贴底 | 发送即 welcome 消失、turns 流渲染；流式中/4 turns/6 turns 下 dock 均在视口底（gap 0–14px 含 smooth 滚动进行时），最后 turn 不被遮挡 |
| 3 历史/重载 + 滚动不强制跳 | 重载后 4→6 turns 与 v1/v2/v3 精确恢复；流式中上翻 4 个 delta 后 scrollY=37 保持顶部，回到底部恢复跟随（nearBottom 90px 阈值） |
| 4 草稿集成 + 旧集微妙入口 | 草稿卡在对话流内、gate-note 收进默认收起 details；v1→v2→v3 不可变链 + 复制/导出/未审核标注保留；旧集折叠入口独立于对话流，B1 防护不变 |
| 5 移动 + 失败不丢输入 | 375px 溢出 0px、safe-area padding 12px、composer 无需回顶可达；retry 撞上未释放预约被 400 → 状态如实「上一条回复还在进行中…输入已恢复」+ 输入框内容完整恢复 + localStorage 回写；404 场景提示「本机服务可能是旧版本，请重启本地服务后刷新页面」 |
| 6 单列干净工作区 | 全页截图（26/31）：对话→草稿→贴底输入一个纵向流，无侧边栏/仪表盘/巨型 landing |

### 限额真实模型端到端（8321，Owner Key，产品内）

| 步骤 | 真实调用 | 结果 |
| --- | --- | --- |
| ① 真实流式聊天 | #1 | 2.6s 完成；标注「deepseek-flash · 真实模型回复」 |
| ② follow-up（带完整上下文） | #2 | 2.4s；钩子「深夜自习室的灯，没人敢先关。」+ 标题《谁都不肯先关的那盏灯》 |
| ③ 草稿生成 | #3 | 3.9s；meta「真实模型回复」；v1 |
| ④ 本地编辑 ×2 | 0 | v2/v3（零调用） |
| ⑤ 重载恢复 | 0 | 6 turns + v1/v2/v3 + 编辑内容逐字符一致 |
| ⑥ 真实 stop | #4（尽力中断） | 计费诚实文案、半截气泡清除、turns=5（uauau） |
| ⑦ 幂等 retry | #5 | 5.8s 完整 60 秒口播稿；turns 5→6 只增 assistant（uauaua） |
| ⑧ 设置往返 | 0 | 徽章「已连接」；返回创作 6 turns + 3 revisions 零丢失 |

服务器日志精确计数（/tmp/deeptalk-studio-pr45-ui.log）：`chat/stream 200` ×4 + `chat/draft 200` ×1 = **5 次真实模型调用（≤ 8 上限）**；`chat/stream 404` ×4（Owner 旧进程故障，零调用）、`chat/stream 400` ×1（空消息路由验证，零调用）、`draft/edit 200` ×2（本地，零调用）。夹具回归不作为真实模型 PASS 依据。

### 本轮截图（evaluations/issue44_minimal_ux/screenshots/）

- 25-unified-empty-state.png（新一体化空态；与 19 旧「hero + 双区」布局形成新旧对比）
- 26-unified-conversation-full.png（8322 对话全页：turns + 草稿 + 贴底 composer 单一流）
- 27-unified-streaming.png（流式中 + 诚实夹具标注）
- 28-unified-stopped-retry.png（停止态：计费诚实文案 + 重发按钮）
- 29-unified-mobile-375.png（375px 全页：零溢出）
- 30-real-deepseek-stopped.png（8321 真实停止态）
- 31-real-deepseek-conversation-full.png（8321 真实模型对话全页：真实回复标注 + v1/v2/v3 + 无明文 Key）
- 32-real-deepseek-mobile-375.png（真实数据 375px）

## Nexus 收尾修复轮：U1 + U2 + Key 跨工作树（2026-10-23，review #5628192126）

### U1/P0：失败请求事务性 —— 假「已发送」气泡零残留

`sendChatMessage` 引入 `accepted` 前哨（SSE start = 服务器已持久化）。三种失败路径各自正确：

| 场景 | UI 气泡 | 输入框 | 「重发上一条」 | 磁盘 turns | 模型调用 |
| --- | --- | --- | --- | --- | --- |
| 404 拦截（模拟旧版本服务） | 乐观气泡**已移除**（10→10） | 恢复原文 | **不显示** | 10 不变、消息零出现 | 0 |
| 400 在飞拒绝（B2 单飞语义） | **已移除**（10→10） | 恢复原文 | **不显示** | 10 不变、零污染 | 0 |
| 新消息网络未达 | 同 404 路径 | 恢复 + localStorage 回写 | 不显示 | 零污染 | 0 |
| SSE 开始后中断（accepted） | 保留（已持久化） | — | 显示（幂等） | 已保存 | 已消耗 |
| stop → 对账 → retry | 半截 assistant 清除；refresh 对账后 lastTurn==message → 幂等 retry | — | 对账后显示 | 仅一条该 user turn | stop 尽力中断 + retry 各一次 |
| retry 撞上预约未释放 400 窗口 | 保留（消息已在记录中） | 不误恢复 | **保留按钮**（「消息已保存，稍候可再点」） | 已保存 | 0（被拒） |

完整链路实测（8322）：baseline 11 → 发送 → stop → 对账（12 turns，retry 可见）→ 立即 retry → 400「稍候可再点」+ 按钮保留 → 1.6s 后再点 → 回复完成 13 turns、roles `uauauauauauua`（一问一答，磁盘仅一条该消息）。绝不静默重发。

状态文案如实：404 →「发送失败：路径不存在；本机服务可能是旧版本，请重启本地服务后刷新页面；内容未发送，已恢复到输入框。」（截图 33）；停止对账 →「已停止显示并尝试中断模型请求；已产生的费用可能仍会计入账单。可点「重发上一条」。」（截图 34）。

### U2/P1：真实视口核验 —— fullPage「遮挡」确系截图伪影，零设计改动

| 视口位置 | 测量 | 结论 |
| --- | --- | --- |
| 桌面 1280×800 滚到底 | `lastTurnBottomAboveDockTop=true`；dock 贴底（gap 14px 含 smooth 滚动） | 最后一条 turn 完全可读，无遮挡（截图 35） |
| 桌面中段滚动 | `dockStickyAtViewportBottom=true`、宽度 760、背景渐变正常 | sticky 形态正常，无文字穿透（截图 36） |
| 375px 滚到底 | 横向溢出 0px、`lastTurnBottomAboveDockTop=true`、safe-area padding 12px | 无遮挡（截图 37） |

Review 所指 31/32 全页截图中输入框「盖住」长回复为 **Playwright fullPage 截图对 sticky 元素的渲染伪影**（sticky 元素被画在流内位置）——真实视口（普通截图 + bounding-rect）证明无任何用户可见遮挡；按「do not blindly redesign」要求设计零改动。

### Owner Key 跨工作树用户级持久化（一次保存，处处复用）

- 新解析顺序：`~/.deeptalk/workbench.local.json`（0600，用户级）优先 → 仓库级 `config/workbench.local.json` 仅作向后兼容 fallback，首次发现即一次性迁移到用户级（原文件保留）；保存只写用户级；显式清除 Key 同步清掉仓库级旧 Key（不复活、无明文残留）。
- **真实迁移实测（8321）**：重启后 `~/.deeptalk/workbench.local.json` 创建（权限 600，未打印任何内容）、`/state` 掩码 `sk-f…8d17` 不变、repo 原文件保留（600）。
- **跨工作树实测**：`/tmp/a-completely-different-worktree` 与 `/tmp/yet-another-root` 两个无关 root 的进程加载同一份已保存 Key（只输出模式与布尔，不打印值）；8322 演示环境注入独立用户目录（`.temp/issue44-demo-root/user-settings-home/`），fixture 配置 `sk-p…ey-2` 与 Owner 真实 Key 完全隔离互不污染。
- **pytest**：autouse fixture 按测试隔离用户目录（`~/.deeptalk` 全程零触碰，运行后确认 home clean）；新增 `test_saved_key_is_shared_across_worktrees_and_survives_updates`（两 root 共享 + 「产品更新」复用 + repo config 不再被写）与 `test_repo_settings_migrate_once_to_user_level_and_stay_0600`（一次性迁移 + 0600 + 原文件保留 + 清除同步清理）。

### 调用预算

本轮 U1/U2 全部经 8322 本地 mock（8931）与浏览器路由拦截完成——**零真实付费调用**；真实 DeepSeek 端到端已于上一轮以 5 次调用（≤8）完成并获 Nexus 确认，未重复。

## 测试凭据安全轮（2026-10-23，review #5628439637）

### P0 复现（代码级确定性，未对真实凭据运行）

`tests/conftest.py` 的 autouse fixture 仅 pytest 加载；AGENTS.md/README.md 文档命令 `PYTHONPATH=src python3 -m unittest discover -s tests -v` 不经 pytest → `USER_SETTINGS_DIR` 保持 None → `user_settings_path()` 解析真实 `~/.deeptalk/workbench.local.json` → 测试中的 `save_settings`（合成 Key、清除）将覆盖/清除 Owner 已保存的 DeepSeek Key。全仓库精确复核：仅 `test_workbench.py` 与 `test_webui.py` 触及 settings/flow（148 个测试文件中其余均不涉及用户级凭据）。

### 修复（runner 无关）

两个测试文件**模块加载时**（任何 runner 导入即先于任何 settings 读/写）：
- session 级安全网：`USER_SETTINGS_DIR` 为 None 时指向一次性 `mkdtemp` 目录（atexit 清理），绝不解析真实 `Path.home()`；
- 每测试隔离：内联 `_UserSettingsIsolatedTestCase` 基类为每个测试新建独立用户级目录并 cleanup 恢复；两文件全部测试类改继承；
- 删除 pytest-only 的 `tests/conftest.py`（基类对 pytest 与 unittest 双入口同样生效，统一机制）；
- 生产端零改动：settings.py 不变，8321 等生产进程不导入测试文件，用户级 `~/.deeptalk` 行为保持。

### 安全证明（Review 要求方式）

| 步骤 | 命令 | 结果 |
| --- | --- | --- |
| ① sentinel HOME + 裸文档命令 | `HOME=<sentinel-home> PYTHONPATH=src python3 -m unittest discover -s tests` | `Ran 1125 tests in 210.933s` → `OK (skipped=7)`，exit=0；sentinel `.deeptalk/workbench.local.json` sha256 **两次运行前后均完全不变**，目录内无新文件 |
| ② pytest 全量（真实 HOME） | `PYTHONPATH=src pytest tests/ -q` | 全量绿；真实 `~/.deeptalk/workbench.local.json` sha256/mtime/size 运行前后不变 |
| ③ 每测试隔离语义 | SettingsTests/CreativeChatTests 等 | 跨工作树共享测试（两 root 同一测试内共享同一隔离目录）与迁移/清除测试在双入口下行为一致 |

（完整 pytest 全量统计见对应轮提交记录；unittest 与 pytest 的 1125 = 1118 passed + 7 skipped 完全对应。）

## 多会话 UX 轮（2026-10-23，issuecomment-6366157284）

### 验收环境

- 8322 隔离夹具（`.temp/issue44_clean_ui.py`）：真实产品代码 + 一次性 demo root；本轮起新增**用户级聊天目录注入**（`user-chat-home`）——demo 会话与 Owner 真实 `~/.deeptalk/chat/` 完全隔离互不污染；mock LLM 8931（0.5s/块慢节奏），零真实付费调用。
- 8321 真实仓库（LaunchAgent）：重启加载多会话代码并完成**真实聊天历史用户级迁移**。

### 桌面全流程（1280×800，截图 38–47）

| 步骤 | 判定证据 | 结果 |
| --- | --- | --- |
| 初始加载（既有会话） | sidebar 列出既有会话（「13 条消息 · 草稿 v3」元数据行）、会话 turns 渲染、草稿仅小入口「📝 草稿 v3 · 未审核」 | 巨型草稿编辑器不再常驻（截图 38） |
| ＋ 新建对话 | `performance` 资源计数 delta=0（零服务端调用）、welcome 空态、线程 0 条、既有会话仍在列表 | 点击零调用，旧会话不抹除（截图 39） |
| 话题甲首发送（new_session=true） | mock 流式回复完整、侧栏新增条目标题=首条用户消息、localStorage 记录新会话 id、选中高亮 | 会话 A 创建（截图 40） |
| 草稿 v1 生成（显式动作） | 入口行先显示小「把对话整理为草稿（调用模型，可能计费）」、生成后**抽屉自动展开**、入口变「草稿 v1 · 未审核」、编辑器含夹具草稿文本 | 生成是显式计费动作+直接后果轻确认（截图 41） |
| 编辑保存 v2/v3 后收起 | 入口显示「草稿 v3 · 未审核」、抽屉收起 | 版本链 v1/v2/v3 全保留（截图 42） |
| 新建 B | welcome 空态、`话题甲`/`甲草稿` 零出现、草稿入口行整体隐藏 | B 与 A 完全隔离（截图 43） |
| 话题乙首发送 | B 会话创建、侧栏 3 会话按最近更新倒序、localStorage 切到 B | 会话 B 创建（截图 43） |
| 侧栏点击会话 A | 会话内容=仅 A（`话题乙` 零出现）、入口「草稿 v3」、抽屉**默认收起**、打开抽屉版本页签 v1/v2/v3（你的修改）齐全、状态行「版本 v3 · 你的修改」 | 精确恢复 turns+草稿+来源（截图 44） |
| 刷新页面 | localStorage（非机密 id）选中 A 保持、内容/草稿恢复、抽屉默认收起 | 刷新保持选择（截图 45） |
| **8322 进程重启后重载** | A 仍选中恢复、3 会话齐全 | 进程级持久化（截图 46） |
| **流式切换守卫（确定性）** | 单次同步 evaluate 内：发送 B 追问（chatInFlight=true）→ 立即点击 A → 守卫文案「当前回复还在进行中，请先停止或等待完成后再切换会话。」、localStorage 不动（仍 B）、会话不切换、无跨会话迟到 SSE | 不依赖时序的确定性验证（截图 47） |
| B 活动后回到 A | A 恰 4 轮（2+追问+回复）、B 内容（话题乙/地铁通勤）零出现、草稿 v3 保留 | B 回复不影响 A |
| /settings | Key 输入为空（无需重输）、掩码 `sk-p…ey-2`、夹具标注、DOM 无明文密钥 | 掩码持久化保持 |

### 375px 手机（截图 48–50）

| 步骤 | 判定证据 | 结果 |
| --- | --- | --- |
| 初始 | sidebar 移出屏幕（left=-315）、☰ 历史按钮可见、遮罩隐藏、**横向溢出 0**（scrollWidth=clientWidth=360） | 零溢出（截图 48） |
| ☰ 打开抽屉 | sidebar left=0 全入视野、遮罩可见、3 会话+新建按钮可达 | 抽屉形态正常（截图 49） |
| 选择会话 B | 抽屉滑出（left=-315）、遮罩隐藏、B 内容渲染、**横向溢出 0** | 选择后自动关闭（截图 50） |
| 键盘可达性 | 真实 Tab 键焦点链依次落于交互按钮、`document.activeElement.matches(':focus-visible')===true`；全局 CSS `button:focus-visible` 焦点环已定义 | 键盘/焦点可达 |

### 真实聊天历史用户级迁移（8321）

| 检查 | 结果 |
| --- | --- |
| 迁移件 | `~/.deeptalk/chat/20d07fad….json` 创建，0600，与仓库原件 **sha256 一致**，测试指纹 **0 处** |
| 仓库原件 | `workbench/chat/20d07fad….json` 保留不动（mtime/size 不变，gitignored） |
| sessions 端点 | 列出 Owner 真实会话（12 turns · 3 drafts · 标题=首条用户消息截断） |
| 精确恢复 | `?chat=<id>` 返回同一会话（12 turns/3 drafts） |
| Owner Key | `~/.deeptalk/workbench.local.json`（0600）不受影响 |

### 开发期污染事故与清理（诚实记录）

多会话代码落地与测试隔离块落地之间存在一次中间测试运行（21:39–21:41），当时 `USER_CHAT_DIR` 隔离尚未就位，把 2 个文件误写入真实 `~/.deeptalk/chat/`：1 个真实会话迁移副本被追加了 fixture 轮次（17,805 字节、测试指纹 5 处）、1 个纯 fixture 会话（6,703 字节、指纹 3 处）。两个文件**均非 Owner 真实数据形态**，已全部移入 `.temp/real-chat-pollution-quarantine/` 隔离保存（未销毁），随后 8321 重启以仓库原件（干净、指纹 0 处）为准重新完成迁移。仓库级真实会话文件全程未被测试触碰。隔离修复后的**确定性证明**：真实 `~/.deeptalk` 全文件 sha256 快照在 focused 套件（141 passed）运行前后完全一致。

### 调用预算

本轮全部浏览器验收经 8322 本地 mock（8931）完成——**零真实付费调用**（真实 DeepSeek 端到端已于 Owner UX 轮以 5 次调用完成并获 Nexus 确认，未重复）。

### 回归与双入口隔离证明

| 步骤 | 命令 | 结果 |
| --- | --- | --- |
| focused 套件 + 真实 ~/.deeptalk 快照对照 | `pytest tests/test_workbench.py tests/test_webui.py -q`（真实 HOME） | **141 passed**；真实 `~/.deeptalk` 全文件 sha256 快照运行前后完全一致（零触碰） |
| 全量 pytest | `PYTHONPATH=src .venv/bin/python -m pytest tests/ -q` | **1121 passed, 7 skipped**（退出码 0；上一轮 1118 passed + 本轮 3 新用例 = 精确衔接，1121+7=1128） |
| sentinel HOME + 裸文档命令（第一次） | `HOME=<sentinel> PYTHONPATH=src python3 -m unittest discover -s tests` | 退出码 0；sentinel `.deeptalk` 文件列表不变、marker 文件 sha256 不变 |
| sentinel HOME + 裸文档命令（第二次，完整汇总） | 同上 | **`Ran 1128 tests in 217.897s` → `OK (skipped=7)`**，退出码 0；sentinel `.deeptalk` 文件列表不变；marker 文件 sha256 `b848f27b…93` **前后一致**（含聊天目录在内，双 runner 零触碰真实用户级数据） |

（1125 = 第七轮基线 1118 passed + 7 skipped；本轮 +3 多会话用例 → 1128，与 pytest 1121 passed + 7 skipped 完全对应。）

## 多会话复审修复轮（2026-10-23，review #5629701467）

### 验收环境

8322 隔离夹具（用户级设置/聊天目录双注入）+ 8931 mock（0.5s/块）；**零真实付费调用**；桌面 1280×800 + 375px。守卫验证使用 Playwright `page.route()` 按住请求 + 确定性轮询/释放 —— 不依赖时序运气，迟到响应的送达以网络事件记录证明。

### P0 迟到草稿结果跨会话污染（截图 51–55）

| 步骤 | 判定证据 | 结果 |
| --- | --- | --- |
| 按住 D 的草稿生成请求（生成中切走） | `generateHeld=true`（route 按住）；A 的编辑器捕获 v3 全文 | 确定性可控（截图 51） |
| 释放迟到响应（~6.6s 后 mock 完成） | 网络事件确认响应送达；D 侧栏行出现「· 草稿 v1」（`refreshSessionsQuietly` 元数据更新，poll 6645ms） | 仅元数据，A 视图零触碰 |
| A 视图不受影响 | A 编辑器内容前后**逐字节一致**（`aUnchanged=true`）、入口仍「📝 草稿 v3 · 未审核」、状态文案清洁（无 D 的在飞提示残留） | 迟到结果不污染当前编辑器（截图 52） |
| 切到 D | D 自己的草稿 v1 渲染（内容围绕话题丁，零话题甲内容），入口「草稿 v1」 | 数据在服务端完好，选中即精确恢复（截图 53） |
| 保存污染检查 | D 编辑器加标记后保存，截获 payload：`session_id` === D、content 含 D 标记、**零 A 内容**；A 服务端草稿数仍 3 | A 内容绝不会被存为 B 的修订 |
| 切回发起会话分支 | D 保存在飞期间切 A 再切回 D：状态如实「该会话的草稿操作仍在进行中…」（截图 54）→ 释放后如实「已保存为版本 v3」并自动刷新当前会话（入口 v3、服务端 3 版本） | 不残留误导状态（截图 55） |

### P1 乱序 state 响应翻转选中（截图 56–58）

| 步骤 | 判定证据 | 结果 |
| --- | --- | --- |
| 点 A（state GET 被按住）→ 界面仍显示 D | `afterClickA_uiStillD=true` | A 响应未到，选中不变（截图 56） |
| 再点 D（快响应渲染） | D 选中且渲染 | 后发先至正常 |
| 释放 A 的迟到响应（用真实捕获的 A state fulfill） | **`staleResponseArrived=true`**（响应事件记录=确实送达）；此后 localStorage 仍 D、界面显示 D、零 A 内容 | 迟到响应被 refresh 代际丢弃（截图 57） |
| 下一条消息作用域 | 截获发送 payload `session_id` === D；流结束后选中仍 D | 绝不发错会话（截图 58） |

### 375px（截图 59–61）

侧栏抽屉打开（遮罩可见）→ 选择 A 后自动关闭 + 精确渲染 + **横向溢出 0** → 草稿入口「草稿 v3」展开抽屉零溢出。守卫逻辑为纯 JS 行为修复，与视口无关。

### 诚实披露：测试过程的两次自我纠错

- 首次浏览器验证的轮询条件写错（会话标题本身含「草稿」二字，轮询在响应到达前误判成功），断言全部落在未完成中间态；改为轮询「· 草稿 vN」元数据标记 + 响应送达网络事件记录后重验，全部通过。
- 调试中发现两个真实缺陷并修复：切换会话后状态文案残留上一会话的在飞提示（`syncDraftViewStatus` 如实重置）；用户切回发起会话时迟到结果既不显示也不清「仍在进行中」误导态（切回分支如实提示 + 刷新当前会话）。
- flight key 首版只做单 key 规范化，被既有 B2 回归测试（`test_second_stream_while_first_in_flight_returns_400`）捕获「首个 legacy 发送创建会话期间的 legacy 重叠」漏检，改为双 key + 锁内别名检查后全绿 —— 既有回归再次证明价值。

### 回归

| 项 | 结果 |
| --- | --- |
| focused（test_workbench + test_webui） | **144 passed**（+3：legacy/explicit 双向别名冲突 / 显式指向 legacy 刚创建会话 400 / 守卫结构静态断言） |
| 全量 pytest（真实 HOME） | **1124 passed, 7 skipped**，退出码 0（1121+3 精确衔接）；真实 `~/.deeptalk` 全文件 sha256 快照运行前后完全一致 |
| sentinel HOME + 裸文档命令 | **`Ran 1131 tests in 222.863s` → `OK (skipped=7)`**，退出码 0；sentinel `.deeptalk` 文件列表不变，marker sha256 `719f48ff…99` 前后一致（双 runner 均不触碰真实用户级配置与聊天历史） |
