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

> 取证勘误：截图 12–15 首次拍摄时 Playwright 会话视口残留上一轮的 375px，被误标为桌面截图（328×1068）；已全部在 1280×800 桌面视口重拍（961px 宽）并覆盖。
