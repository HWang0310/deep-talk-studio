# Issue #44 / PR #45 — 极简创作页与独立模型设置页

> **状态：READY_FOR_NEXUS_UX_REREVIEW（第二轮：DeepSeek 设置体验）。** 本分支保留 PR #45 的工作流和后端门禁，完成参考截图导向的首页 / 设置页重设计与 Nexus Review B1/B2/B3 修复；第二轮按 Owner 六点要求完成「DeepSeek 默认只需填 API Key」的设置体验与视觉打磨。PR 保持打开，未合并。

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

完整的 B1/B2 断言、设置体验流与浏览器输出见 [browser-evidence.md](browser-evidence.md)。

## 测试结果

- 'PYTHONPATH=src .venv/bin/python -m pytest tests/test_webui.py tests/test_workbench.py -q' → **112 passed**（本轮新增 DeepSeek 只需填 Key、无机器码文案、开发测试环境 3 组断言）
- 'PYTHONPATH=src .venv/bin/python -m pytest tests -q' → **1092 passed, 7 skipped**
- 内联 JavaScript：'node --check /tmp/deeptalk-webui.js' → **通过**
- 'git diff --check' → **通过**
- 未修改无关后端、模型门禁、SSRF 防护或生产工作流；未提交本地密钥、模型输出、缓存或临时会话。

## 截图与凭据说明

截图是真实浏览器输出，存放在 'screenshots/'（桌面元素宽 961px、手机 375px 视口元素宽 328px）。设置页使用仅用于验收的假 Key，截图只显示 `sk-t…cdef` 等掩码；本地连接图使用 '127.0.0.1:8931' 的 loopback fixture，不代表真实模型质量。真实 DeepSeek 创作仍保持 'WAITING_FOR_OWNER_API_KEY'（机器状态仅在 payload），等待 Nexus 审核，不自行合并。

已知限制（如实声明）：

- 真实 DeepSeek 连接质量未验证，等待 Owner 填入自己的 Key 自测。
- 375px 手机端输入框内宽 168px 放不下完整占位符「粘贴你的 DeepSeek API Key」（canvas 实测 190px），按设计自动降级为「粘贴你的 API Key」。
- 图像模型评审曾三次误报（保存按钮换行、deepseek-flash 断行、桌面占位符截断），均已用逐字符 Range / canvas 测量实测推翻；「模型」标签断词与手机占位符截断两项为真实问题并已修复。
