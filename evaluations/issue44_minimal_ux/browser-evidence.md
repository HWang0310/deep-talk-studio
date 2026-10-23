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
