# Issue #38 — Creator Workbench 自主浏览器验收

状态：`READY_FOR_NEXUS_REVIEW`（离线 UI/编排证据）+ `WAITING_FOR_OWNER_API_KEY` + `WAITING_FOR_OWNER_REVIEW`。

这份证据把两类测试严格分开：

1. **离线夹具层**：只验证页面布局、键盘可达性、设置掩码、会话恢复、二进制导入、音频预览、时间轴/缺口显示和 typed failure。`fixture_server.py` 明确把 Workbench 连接标为 `fixture`，没有模型实现，不能证明 DeepSeek 创作质量。
2. **真实本地链层**：既有 `tests.test_audio_only_delivery` 使用真实音频交付/QA 核心和本机 ASR 夹具；本轮不上传私人音频、不调用 DeepSeek、不触发计费。真实模型与 Owner 的最终录音/版权决策仍待 Owner。

## 可重复命令

在仓库根目录执行：

```bash
# 1) 离线夹具服务（另一个终端保持运行）
TMP_ROOT="$(mktemp -d /tmp/deeptalk-issue38.XXXXXX)"
PYTHONPATH=src python3 evaluations/issue38_workbench/fixture_server.py \
  --root "$TMP_ROOT" --port 0

# 2) Playwright CLI（使用技能提供的 wrapper）
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export PWCLI="$CODEX_HOME/skills/playwright/scripts/playwright_cli.sh"
export PLAYWRIGHT_CLI_SESSION=deeptalk-issue38
"$PWCLI" open http://127.0.0.1:<printed-port>/ --headed
"$PWCLI" snapshot

# 或运行可重复的端到端离线 smoke（会生成 output/playwright/ 下的截图）
PYTHONPATH=src python3 evaluations/issue38_workbench/smoke_playwright.py \
  --url http://127.0.0.1:<printed-port>/ --session deeptalk-issue38-smoke --headed
```

浏览器检查清单：

- 桌面宽度（1440×1000）：打开设置，确认 API Key 为 `type=password`，保存后只显示掩码/fixture 状态；确认 `/healthz` 返回 `{"ok":true}`。
- 375px：`resize 375 900`，用 Tab 顺序经过主题、参考链接、设置和音频控件；六个步骤和音频卡片不横向溢出。
- 恢复/重试：开始离线会话，导入一个临时 WAV；刷新页面后仍显示来源、大小、SHA-256 和本地 `<audio>` 预览；点击交付后显示 `WAITING_FOR_OWNER_REVIEW`，再次刷新状态不丢失，也不会生成成片或假人物画面。
- 证据截图仅写入 `output/playwright/`（技能约定），不提交私人媒体、Key、Cookie 或会话目录。

本轮提交的脱敏 UI 证据副本：
`screenshots/desktop.png`、`screenshots/mobile-375px.png`。运行器报告包含健康检查、8
项断言和耗时；截图与报告均不含真实凭据或私人媒体。

## 本轮实际结果

| 检查 | 结果 |
|---|---|
| `tests.test_workbench` + `tests.test_webui` | 101/101 pass |
| `tests.test_audio_only_delivery` | 18/18 pass |
| `tests.test_deepseek_tools` | 4/4 pass |
| 全量 `unittest discover -s tests` | 1088 pass，7 skipped |
| 静态浏览器脚本 `node vm.Script` | pass |
| `py_compile` / `git diff --check` | pass |
| 离线 Playwright runner | 8/8 assertions pass；healthz 200；桌面/375px 截图 |
| 真实 DeepSeek Search/Fetch 或创作模型 | 未调用（无 Owner Key/预算授权） |
| Owner 私人音频、真实版权素材、最终发布 | 未执行，等待 Owner review |

不要把离线夹具的候选、脚本或 `fixture` 状态写成真实 Bilibili、真实模型或 publish-ready 结果。最终退出标记必须保留 `READY_FOR_NEXUS_REVIEW`，并等待 Nexus 独立复审。
