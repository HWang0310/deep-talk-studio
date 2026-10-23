# Issue #44 / PR #45 — 极简创作页与独立模型设置页

> **状态：READY_FOR_NEXUS_MVP_REVIEW（第四轮：Chat-first Creative Draft MVP）。** 本分支保留 PR #45 的工作流和后端门禁，完成参考截图导向的首页 / 设置页重设计与 Nexus Review B1/B2/B3 修复；第二轮按 Owner 六点要求完成「DeepSeek 默认只需填 API Key」的设置体验；第三轮修复 paste→Test 旅程；第四轮按 Owner 批准的 Option A 实现 Chat-first Creative Draft MVP（真实流式、多轮恢复、可编辑草稿；正式审核与生产门禁保持不变）。PR 保持打开，未合并。

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

完整的 B1/B2 断言、设置体验流与浏览器输出见 [browser-evidence.md](browser-evidence.md)。

## 测试结果

- 'PYTHONPATH=src .venv/bin/python -m pytest tests/test_webui.py tests/test_workbench.py -q' → **127 passed**（新增：聊天/草稿 7 项 flow 测试、SSE HTTP 3 项、Chat-first 静态断言、P0 三项）
- 'PYTHONPATH=src .venv/bin/python -m pytest tests -q' → **1107 passed, 7 skipped**
- 内联 JavaScript：'node --check /tmp/deeptalk-webui.js' → **通过**
- 'git diff --check' → **通过**
- 未修改无关后端、模型门禁、SSRF 防护或生产工作流；未提交本地密钥、模型输出、缓存或临时会话。

## 截图与凭据说明

截图是真实浏览器输出，存放在 'screenshots/'（桌面元素宽 961px、手机 375px 视口元素宽 328px）。设置页使用仅用于验收的假 Key，截图只显示 `sk-t…cdef` 等掩码；本地连接图使用 '127.0.0.1:8931' 的 loopback fixture，不代表真实模型质量。真实 DeepSeek 创作仍保持 'WAITING_FOR_OWNER_API_KEY'（机器状态仅在 payload），等待 Nexus 审核，不自行合并。

已知限制（如实声明）：

- 真实 DeepSeek 连接质量未验证，等待 Owner 填入自己的 Key 自测。
- 375px 手机端输入框内宽 168px 放不下完整占位符「粘贴你的 DeepSeek API Key」（canvas 实测 190px），按设计自动降级为「粘贴你的 API Key」。
- 图像模型评审曾三次误报（保存按钮换行、deepseek-flash 断行、桌面占位符截断），均已用逐字符 Range / canvas 测量实测推翻；「模型」标签断词与手机占位符截断两项为真实问题并已修复。
