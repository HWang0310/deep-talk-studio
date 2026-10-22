# Issue #44 / PR #45 — 极简创作页与独立模型设置页

> **状态：READY_FOR_NEXUS_UX_REREVIEW。** 本分支保留 PR #45 的工作流和后端门禁，完成参考截图导向的首页 / 设置页重设计，并修复 Nexus Review B1、B2、B3。PR 保持打开，未合并。

## 视觉与交互交付

### 创作首页 /

- 全视口奶白背景、居中衬线标题、独立珊瑚色抽象标记和轻柔阴影。
- 宽大的多行创作框带内置工具栏、参考链接入口、圆形开始按钮和少量提示胶囊；输入框支持多行，'⌘/Ctrl + Enter' 开始创作。
- 右上角保留唯一设置入口；首页没有侧边栏、调试面板或卡片墙。
- 开始创作后保留原有视频搜索、授权下载、转写、叙事分析、研究、选题卡、审核和写稿功能。阶段条只显示当前阶段，已完成阶段仍可回看。

### 独立设置页 /settings

- 独立路由和返回创作入口；桌面双列、手机单列，表单留白和层级按参考图重排。
- 主字段：服务商（DeepSeek 默认）、模型名称、掩码 API Key、API 地址、测试连接、保存、取消。
- 高级端点和下载位置按需折叠；连接状态明确区分未配置、已保存未验证、已连接、失败和本地夹具。
- API Key 仍只由本地设置存储，页面只显示掩码；本轮没有调用真实 DeepSeek 或任何付费模型。

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

使用 Playwright Chromium，在本机 loopback UI 上反复检查桌面 1440px 与手机 375px：

| 验收 | 结果 | 证据 |
| --- | --- | --- |
| 空白首页与参考图层级 | 通过；无滚动条，首页只有创作入口 | [01-desktop-home-empty-hero.png](screenshots/01-desktop-home-empty-hero.png) |
| 设置页 DeepSeek 默认与掩码 Key | 通过；API 地址可见，Key 未回显明文 | [03-desktop-settings-deepseek-masked-key.png](screenshots/03-desktop-settings-deepseek-masked-key.png) |
| 设置页本地 Chat 连接测试 | 通过；真实调用本地 fixture，状态显示“已连接（本地服务）” | [04-desktop-settings-connected-local-fixture.png](screenshots/04-desktop-settings-connected-local-fixture.png) |
| 五条视频参考、逐条已分析 | 通过；保留视频搜索、转写和叙事分析 | [05-desktop-stage1-references-analyzed.png](screenshots/05-desktop-stage1-references-analyzed.png) |
| 五方研究与主题一致的离线来源 | 通过；5/5、免责声明和五条主题一致材料可见 | [06-desktop-stage2-research-five-way.png](screenshots/06-desktop-stage2-research-five-way.png) |
| 审核通过的中文口播稿 | 通过；正文、复制、存档和音频/素材入口均保留 | [07-desktop-script-manuscript-delivered.png](screenshots/07-desktop-script-manuscript-delivered.png) |
| B1 新一集隔离态 | 通过；新首页单独显示，取消可恢复上一集 | [11-desktop-new-episode-only.png](screenshots/11-desktop-new-episode-only.png) |
| 375px 手机首页、设置、文稿 | 通过；三页 'scrollWidth === 375'，无横向溢出 | [08](screenshots/08-mobile-375-home.png) / [09](screenshots/09-mobile-375-settings.png) / [10](screenshots/10-mobile-375-manuscript.png) |

完整的 B1/B2 断言和浏览器输出见 [browser-evidence.md](browser-evidence.md)。

## 测试结果

- 'PYTHONPATH=src .venv/bin/python -m pytest tests/test_webui.py tests/test_workbench.py -q' → **109 passed**
- 'PYTHONPATH=src .venv/bin/python -m pytest tests -q' → **1089 passed, 7 skipped**
- 内联 JavaScript：'node --check /tmp/deeptalk-webui.js' → **通过**
- 'git diff --check' → **通过**
- 未修改无关后端、模型门禁、SSRF 防护或生产工作流；未提交本地密钥、模型输出、缓存或临时会话。

## 截图与凭据说明

截图是本轮真实浏览器输出，存放在 'screenshots/'。设置页使用仅用于验收的假 Key，截图只显示 'sk-E…ONLY' 掩码；本地连接图使用 '127.0.0.1:8931' 的 loopback fixture，不代表真实模型质量。真实 DeepSeek 创作仍保持 'WAITING_FOR_OWNER_API_KEY'，等待 Nexus 审核，不自行合并。
