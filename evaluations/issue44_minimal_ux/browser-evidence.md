# Issue #44 浏览器复测记录

日期：2026-10-22
浏览器：Playwright Chromium（headed）
UI：127.0.0.1 loopback，真实页面脚本和后端流程

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
- 设置页桌面：两列主表单，API 地址可见；DeepSeek Key 只显示 sk-E…ONLY。
- 本地连接测试：chat / fixture-model 返回“连接正常”，端点为 127.0.0.1:8931；没有调用真实 DeepSeek。

## 生成的截图

- screenshots/01-desktop-home-empty-hero.png
- screenshots/03-desktop-settings-deepseek-masked-key.png
- screenshots/04-desktop-settings-connected-local-fixture.png
- screenshots/05-desktop-stage1-references-analyzed.png
- screenshots/06-desktop-stage2-research-five-way.png
- screenshots/07-desktop-script-manuscript-delivered.png
- screenshots/08-mobile-375-home.png
- screenshots/09-mobile-375-settings.png
- screenshots/10-mobile-375-manuscript.png
- screenshots/11-desktop-new-episode-only.png
