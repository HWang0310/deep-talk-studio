---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'f19a87bd-94e6-4591-819c-2a5e0e4f684f'
  PropagateID: 'f19a87bd-94e6-4591-819c-2a5e0e4f684f'
  ReservedCode1: '3a4dbc85-e553-4e33-9baa-62c929ff47cd'
  ReservedCode2: '3a4dbc85-e553-4e33-9baa-62c929ff47cd'
---

# Creater Workbench Contract（创作工作台：选题 → 参考分析 → 研究 → 选题卡 → 口播稿）v1

> **状态：IMPLEMENTED_UNRELEASED（Issue #23，PR 待审）。** 本合同描述统一创作工作台（Web UI 五步流程）的最小可用能力：用户仅通过产品界面，从输入选题一路走到获得**经独立审核通过**的原创口播文稿。它复用既有 canonical 引擎（Research、Fact-Check、Content Thesis、Script 写稿与审核）与发现合同（`REFERENCE_DISCOVERY_CONTRACT.md`），只做接入编排，不改任何既有合同语义。

## 范围

输入：视频主题（1–200 字、0–5 条可选用户 B 站链接）→ 本机会话。

输出：一个 Web UI 内完成的五步链路 —— ① 主题检索最多 5 条 B 站参考候选（发现合同 v1）→ ②（用户明确授权后）本地下载 + whisper.cpp 转写 + 叙事手法分析 → ③ 用户提供的独立来源（抓取或粘贴）驱动的研究草稿 + 独立事实核查 → ④ 选题卡（写作纲领）经独立审核与用户确认 → ⑤ 原创口播文稿经独立 Schema 审核后全文交付。

不做的事：不发布、不自动剪辑、不生成/代录配音、不读取 Cookie 或登录凭据、不绕过平台风控（HTTP 403/412/429 与验证墙一律如实失败）、不把参考视频当作事实来源或素材、不在用户授权前下载任何媒体、不做多账号并发绕限。

## 调用方式

```bash
./scripts/deeptalk ui          # http://127.0.0.1:8321/，仅绑定本机回环
```

页面上方「设置」面板配置模型提供方式与下载目录；设置持久化到 **gitignored `config/workbench.local.json`**（API Key 仅存本机该文件，UI 回显永远掩码；下载目录必须由用户填写且必须已存在）。

## API 全景（全部带会话 ID，`/api/workbench/*`）

| 端点 | 方法 | 作用 |
|---|---|---|
| `/settings`、`/settings/test` | GET/POST | 设置读取保存（Key 掩码）与模型连通性测试 |
| `/session/start` | POST | 主题 + 用户链接 → 规范发现 run → 创建本集会话 |
| `/state` | GET | 当前会话状态（前端每步刷新） |
| `/references/acquire` | POST | **用户授权声明 + bvids** → 逐条 yt-dlp 下载（匿名、无 cookie、720p 有界、单条 900s 超时）→ 授权与文件哈希存档 |
| `/references/analyze` | POST | 单条参考 → ffmpeg 抽音频 → 本地 whisper.cpp large-v3 转写 → 叙事手法 JSON（hook/pacing/struct_patterns 等，含 top_terms 频次） |
| `/sources/url` | POST | 抓取一条独立来源原文（URL） |
| `/sources/text` | POST | 粘贴一条独立来源正文（标题 + 正文 + 来源 URL；页面抓不到时使用） |
| `/research/generate` | POST | 研究草稿（落盘 canonical `reports/` 研究工件树，研究 mode 记录真实来源） |
| `/fact-check/run` | POST | 独立事实核查（真实 Fact-Check 引擎 + 质量门禁） |
| `/research/approve` | POST | 用户批准研究结论（确认词约束） |
| `/thesis/generate` | POST | 生成选题卡（V1 内容驱动 profile + 批准研究） |
| `/thesis/review` | POST | 选题卡独立审核（gate） |
| `/thesis/approve` | POST | 用户确认选题卡（确认词必须同时含「确认」与「进入写稿」） |
| `/script/generate` | POST | 写稿 + 独立 Script Review（一体，落盘 canonical `script_drafts/`） |
| `/script/final` | GET | 完整口播稿全文 + 提词器文本交付视图 |

## 关键边界（fail-closed）

1. **本机 HTTP 边界**（同发现合同）：127.0.0.1 绑定、窄 Host 白名单、Origin 同源检查、JSON `Content-Type` 强制、读 body 前先验证 `Content-Length`；每个工作台路由有独立请求体上限（`WORKBENCH_ROUTE_CAPS`，超限 413），全部工作台写操作经 `workbench_lock` 串行化（一次一个状态变更，不并发写会话）。
2. **授权获取合同**：下载前必须提交用户填写的授权声明（逐字存档进每条 `acquisition.json`）；下载目录必须是用户在设置中指定的**已存在**目录；工具固定为本机 `yt-dlp`，无 cookie、无登录、单一 720p 格式选择、单条 900 秒超时；平台拒绝访问（风控/验证/登录墙）时返回中文诚实错误、不做任何绕过。下载文件记录大小与 SHA-256。
3. **参考视频天花板原则**：参考视频产物**只**用于叙事结构启发（`insights` 注入研究），研究/事实/素材三查全来自独立来源；参考转录文本永不进入任何正式素材包或事实主张。
4. **LLM 提供方式**：两种模式——OpenAI Responses（支持模型联网研究 `web_search`）与通用 Chat 兼容（**仅用用户提供的来源**；研究输出中出现未被用户提供的来源 URL 即 fail-closed 拒绝，绝不静默接受）；连通性测试要求模型对固定 prompt 回复「正常」。
5. **核查引文重核**：事实核查返回的 `verified` 检查必须附「」引文（≥12 字）且服务器在来源正文中逐字找到该引文；找不到即降级 `unverified` 并在 UI/报告中如实说明，绝不静默放行。
6. **既有引擎门禁全部保留**：approved research 的 confirmed_fact 需 2 个独立来源组、高风险主张 100% 核查覆盖、证据覆盖 ≥80%、Script Review 33 项全过 —— 工作台无任何降低。

## 工件落盘

- `workbench/sessions/WBX-<id>/` — 会话状态、每条参考的授权与转录文档（gitignored）
- `reports/`、`content_theses/`、`script_drafts/` — canonical 引擎工件（与研究 CLI 同构，可被既有 QA 复核）
- `discoveries/` — 规范候选集工件（发现合同 v1，gitignored）
- `config/workbench.local.json` — 设置与 API Key（gitignored，仅本机）

## 已知限制

- 参考下载受 B 站对匿名请求的带宽限制，长音频流可能触发 900 秒超时——这是刻意不绕过的诚实行为；参考分析失败不阻塞研究链路（叙事 insight 退化为空）。
- 一次一个会话（单浏览器页）；多会话并存需要后续版本（不在本合同范围）。
- Chat 兼容模式下模型无法自主联网，研究广度依赖用户提供的来源数量与质量（UI 明示）。

## 测试

`tests/test_workbench.py`（7/7）：全闭环夹具测试（会话→来源→研究→核查→批准→选题卡→审核→确认→写稿→审核→交付）、chat 模式编造来源 fail-closed、坏引文降级；`tests/test_webui.py::WorkbenchRoutesTests`（3/3）：路由边界与 body 上限；见 ISSUE E2E 证据目录 `evaluations/issue23_workbench/`（真实浏览器全链路 + 截图）。
