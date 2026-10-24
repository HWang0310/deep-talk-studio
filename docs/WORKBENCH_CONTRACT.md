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

# Creator Workbench Contract（创作工作台：选题 → 参考分析 → 研究 → 选题卡 → 口播稿 → 音频交付）v1

> **状态：IMPLEMENTED_UNRELEASED（Issue #23，PR 待审）。** 本合同描述统一创作工作台（Web UI 六步流程）的最小可用能力：用户仅通过产品界面，从输入选题一路走到获得**经独立审核通过**的原创口播文稿，并可继续导入自己的口播音频、运行真实本地对齐和领取 Asset Pack / Edit Map。它复用既有 canonical 引擎（Research、Fact-Check、Content Thesis、Script 写稿与审核、Audio-only delivery）与发现合同（`REFERENCE_DISCOVERY_CONTRACT.md`），只做接入编排，不改任何既有合同语义。

## 五视频口播提取补充（PR #48，6384621479，待复审）

本节取代下面历史默认流程。首页是独立提取工具，用户输入1～5个B站URL/BV（支持多行、query tracker、按BV去重），明确勾选本批下载/本地分析授权才开始；不搜索、不调用LLM。逐视频元数据核验后下载→FFmpeg→Whisper，保存完整TXT与含时间码、来源元数据的JSON。任一失败不阻断其余视频，显式单条重试复用已有媒体/转写；原批次和旧文件不覆盖。没有配置下载目录时使用该会话私有media目录，无需模型Key。

`POST /api/workbench/transcripts/{start,state,process,sessions,fuse}` 均有同源/loopback/JSON/body-cap检查；process/fuse共享互斥写锁。state恢复会话与完整原文；TXT复制/下载和JSON下载在浏览器本地生成，合并TXT同时持久落盘。合并稿完整按来源顺序拼接，含失败标记，不制造缺失口播。刷新、进程重启后可恢复。

可选融合须单独同意向已配置模型发送转写及费用，提供目标字数200～10000和简短风格要求，只生成一篇未审核Creative Draft。源文本全部注入模型；超过100000字符透明拒绝并提供完整TXT供外部AI使用，永不裁剪保存原文。每次融合另存新TXT。正式Reviewed Script等原有审批Gate不变。

`/advanced` 保留原聊天、历史重命名/软删除/恢复及旧流程入口；`/settings`复用原用户Key设置。不会迁移/覆盖既有数据。播放量仍仅采用逐视频API核验值，媒体文件扩展名前保留实际整数播放量，无法核验时使用“播放量未知”。

## Owner 流程收口补充（PR #48，6383823863，待复审）

本节取代下文“输入主题就生成三稿”的默认行为，保留原有数据、模型设置、下载/转写工件和正式 Gate。

- 单一聊天页：选题→本地短提示与四步进度卡（找参考/选择分析/三稿/修改导出）。未处理视频时不调用模型写长稿；第一条短标题也可以作为选题，问候/问题保留普通聊天路径。
- 参考在聊天内展开，默认选最高播放量一条；本批显式勾选“我有权下载这些视频，并授权仅在本地学习分析”。后端只处理选中ID并保存该次声明，不把勾选当成正式Rights审批或许可证。下载/抽音/Whisper/爆点分析/写稿由真实阶段事件报告，缺ASR或成功分析不得生成标为基于视频的稿件。失败显式重试，未自动重试模型收费。
- `POST /api/workbench/chat/create` 提供有会话在飞保护的SSE编排，断线在下一阶段停止、已花费费用不承诺退回。参考路径必须同选题、同原始发现turn、候选ID合法且有授权；自由路径 `mode=topic_only` 明确标记“仅按选题自由创作 · 未分析参考视频”。每次写稿复核实际完整ASR和所选study，不能凭模型或状态字段自称看过视频。
- 三篇完整稿直接进入聊天并留存，也保存既有不可变稿件revision。每条模型回复可复制/导出，继续对话修改无需重新下载。编辑器在生成/刷新后均收起，点击才展开；自动随正文长高，只滚动文档，不让底部输入框盖住末尾/按钮。显式打开可定位编辑器，编辑和切版本不主动滚屏。
- 旧正式流程默认完全隐藏，在设置>高级显式打开，刷新重新隐藏；底层状态与审批/版权门禁不变。已有历史稿件、v1–v6等所有revision、回收站与Key照常保留。
- 爆点分析失败时，已完成的全文ASR仍可查看/导出；失败研究不会被默认为视频二创成功。当前依据（参考/仅选题）与实际完成工件由代码判定。

## PR #48 爆款二创 1.0 候选补充（2026-10-24，待 Nexus 审核）

按 Owner 最终评论 6383273699，Chat-first 自由创作以 B站娱乐二创为默认定位：一次写出犀利吐槽、搞笑玩梗、故事反转三篇完整中文口播，直接聊天改写，默认60–90秒仅为创作起点，不是硬时长 Gate。摘要注入只含题材/可归因观点/梗机制/叙事节拍，不拼接完整参考转写或改写原作者独特表达。真实严重指控不编成定论；正式 Reviewed Script 等原审批 Gate 不变。

- 免费选题检索复用 canonical reference discovery 的相关性过滤、逐视频播放量核验与降序排序，最多5条，不等于全站榜单；单轮12秒上限、2个后台检索槽，超时丢弃迟到结果。UI 发送即显示准备检索，结果后才显示完成/不可用。相同选题和重试幂等，来源按选题/原触发 turn 留存；切换选题时模型不接收旧题对话、来源或草稿。旧 singleton 数据兼容读取。
- 按需“参考工作区”与聊天选题绑定，明确选择来源、授权声明后沿用现有获取流程。新媒体名末尾为 `-<核验整数>播放.<ext>`，非逐视频核验则 `-播放量未知.<ext>`，碰撞加随机区分片段，旧下载不重命名/覆盖。完整 `transcript.json` 保留，旁边原子保存 `标题-BVID-口播转写.txt`，附来源/BVID/ASR模型/状态/时间/媒体SHA；界面全文搜索、复制、TXT和含完整segments的JSON导出。缺 Whisper 仅报明确路径，不自动下载大模型，聊天照常可用。既有成功分析不重复付费，显式 reanalyze 才重跑摘要。
- 历史 `···` 原生键盘可达菜单：重命名(1–80字符)、删除前确认标题/草稿数量、软删除、回收站恢复。无自动过期清除，不删参考/媒体；SSE或草稿操作在飞时拒绝冲突修改；ID/路径与symlink服务端校验。Key与历史主存储为用户级 `~/.deeptalk/workbench.local.json`、`~/.deeptalk/chat/`，不是下面历史单会话设计中的仓库配置路径。
- 新增同源、loopback、body-cap 路由：`POST /chat/manage`、`/chat/references`、`/references/transcript`（均在 `/api/workbench` 下）；`GET /chat/sessions` 同时返回 active 和 trash 元数据。转写端点只按 session/BVID 解析本地工件，不接受任意文件路径。
- Three.js 不启用；静态 CSS 渐变细节无需 GPU 动画/第三方依赖。测试、真模型与合成媒体的边界见交付证据。

## 范围

输入：视频主题（1–200 字、0–5 条可选用户 B 站链接）→ 本机会话。

输出：一个 Web UI 内完成的六步链路 —— ① 主题检索最多 5 条 B 站参考候选（发现合同 v1）→ ②（用户明确授权后）本地下载 + whisper.cpp 转写 + 叙事手法分析 → ③ 用户提供的独立来源（抓取或粘贴）驱动的研究草稿 + 独立事实核查 → ④ 选题卡（写作纲领）经独立审核与用户确认 → ⑤ 原创口播文稿经独立 Schema 审核后全文交付 → ⑥ 用户导入有来源声明的本地口播音频/视频，运行真实本地 ASR/对齐，查看时间轴与 `AUDIO_ONLY` / `VISUAL_GAP`，下载 QA-ready Asset Pack / Edit Map。

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
| `/research/generate` | POST | 研究草稿（落盘 canonical `reports/` 研究工件树，研究 mode 记录真实来源）；可选 `partial_override` + `partial_reason`：已授权参考未全部完成分析时必须显式带 override 与理由（≥10 字，逐字存档） |
| `/fact-check/run` | POST | 独立事实核查（真实 Fact-Check 引擎 + 质量门禁） |
| `/research/approve` | POST | 用户批准研究结论（确认词约束） |
| `/thesis/generate` | POST | 生成选题卡（V1 内容驱动 profile + 批准研究） |
| `/thesis/review` | POST | 选题卡独立审核（gate） |
| `/thesis/approve` | POST | 用户确认选题卡（确认词必须同时含「确认」与「进入写稿」） |
| `/script/generate` | POST | 写稿 + 独立 Script Review（一体，落盘 canonical `script_drafts/`） |
| `/script/final` | GET | 完整口播稿全文 + 提词器文本交付视图 |
| `/audio/import` | POST（二进制） | 会话内 bounded atomic 导入 WAV/MP3/M4A/AAC/FLAC/MP4/MOV/M4V；记录来源、大小与 SHA-256，不覆盖既有文件 |
| `/audio/deliver` | POST | 调用既有真实本地 ASR/对齐/Audio Asset Pack + Edit Map 链；缺少审核工件时返回 `WAITING_FOR_OWNER_REVIEW` |
| `/audio/artifact` | GET | 仅下载当前会话内 allow-listed 的 Markdown/CSV/JSON/manifest/QA/对齐工件 |
| `/audio/source` | GET | 仅以内联方式播放当前会话导入的本地口播文件；不上传外部服务 |

## 关键边界（fail-closed）

1. **本机 HTTP 边界**（同发现合同）：127.0.0.1 绑定、窄 Host 白名单、Origin 同源检查、JSON `Content-Type` 强制、读 body 前先验证 `Content-Length`；每个工作台路由有独立请求体上限（`WORKBENCH_ROUTE_CAPS`，超限 413），全部工作台写操作经 `workbench_lock` 串行化（一次一个状态变更，不并发写会话）。
2. **授权获取合同**：下载前必须提交用户填写的授权声明（逐字存档进每条 `acquisition.json`）；下载目录必须是用户在设置中指定的**已存在**目录；工具固定为本机 `yt-dlp`，无 cookie、无登录、单一 720p 格式选择、单条 900 秒超时；平台拒绝访问（风控/验证/登录墙）时返回中文诚实错误、不做任何绕过。下载文件记录大小与 SHA-256。
3. **选题一致性门禁（B1，fail-closed）**：研究草稿、选题卡草稿在**生成时**即做选题一致性校验（主题信号词覆盖率 < 20%，且至少命中一个去除“大学/留学生/事件”等泛化词后的主题锚点，否则拒绝写入；合理语义改写保留）；研究批准、选题卡人工确认、写稿（研究报告 + 选题卡 + 口播稿终稿）在**批准/交付边界**复核同一校验——偏题内容既不能保存、不能批准，也不可能以 Gate pass 形态交付。报告中的 `topic` 元数据不作为正文证据。
4. **来源抓取公网限定（B2，fail-closed）**：用户提供的来源 URL 仅允许真实公网 HTTP(S) 目标——连接前解析（A/AAAA）并要求**全部**解析结果为公网单播地址（拒绝 loopback/私网/链路本地/保留/多播/文档网段），连接**固定**到已验证地址（验证与拨号之间无 DNS 重绑定窗口），重定向仅跟随 http(s) 且上限 4 跳（每跳同规则复验），显式禁用系统代理（防代理侧绕过）；解析失败/含糊一律拒绝并提示粘贴正文回退。合法公网来源抓取行为不变。
5. **参考视频天花板原则**：参考视频产物**只**用于叙事结构启发与可归因观点对比（`creator_viewpoint` 为立场概括、非事实转述），研究/事实/素材三查全来自独立来源；参考转录文本永不进入任何正式素材包或事实主张。
6. **五方综合就绪度（B3，fail-closed）**：生成研究草稿前必须完成**所有已授权参考**的本地分析。已授权包括成功下载、已分析，以及授权后下载失败且已持久化原因的条目；后者计入 `eligible` 与未完成 `pending`，在重试成功前会阻断研究。用户只有在**显式勾选部分分析并填写理由**（≥10 字，逐字存档）后才能绕过——UI 明示 `已分析 N / 已授权 M` 与失败待重试数，任何部分分析都如实记录（`reference_comparison.partial`），绝不以 1/5 冒充完整综合；研究/选题卡提示词注入确定性「N 方观点对比」（逐条可归因观点 + 高频结构/钩子/语速统计），选题卡可在差异化定位中概括引用各参考创作者观点（明确归因、禁止复述表达、绝不作为事实来源）。
7. **LLM 提供方式**：两种模式——OpenAI Responses（支持模型联网研究 `web_search`）与通用 Chat 兼容（**仅用用户提供的来源**；研究输出中出现未被用户提供的来源 URL 即 fail-closed 拒绝，绝不静默接受）；连通性测试要求模型对固定 prompt 回复「正常」。
8. **核查引文重核**：事实核查返回的 `verified` 检查必须附「」引文（≥12 字）且服务器在来源正文中逐字找到该引文；找不到即降级 `unverified` 并在 UI/报告中如实说明，绝不静默放行。
9. **既有引擎门禁全部保留**：approved research 的 confirmed_fact 需 2 个独立来源组、高风险主张 100% 核查覆盖、证据覆盖 ≥80%、Script Review 33 项全过 —— 工作台无任何降低。
10. **音频交付边界**：只接受普通文件名和受支持后缀，上传有 512 MiB 上限、禁止 Transfer-Encoding、路径穿越、符号链接和覆盖。交付只生成真实时间轴、QA-ready 候选素材与 Edit Map；缺少审核通过的 Production/Material 工件时 fail-closed 为 `WAITING_FOR_OWNER_REVIEW`。纯音频的 `AUDIO_ONLY` / `VISUAL_GAP` 行必须由创作者人工补画面，系统不生成真人画面、成片或 NLE 工程。

## 工件落盘

- `workbench/sessions/WBX-<id>/` — 会话状态、每条参考的授权与转录文档（gitignored）
- `reports/`、`content_theses/`、`script_drafts/` — canonical 引擎工件（与研究 CLI 同构，可被既有 QA 复核）
- `discoveries/` — 规范候选集工件（发现合同 v1，gitignored）
- `config/workbench.local.json` — 设置与 API Key（gitignored，仅本机）

## 已知限制

- 参考下载受 B 站对匿名请求的带宽限制，长音频流可能触发 900 秒超时——这是刻意不绕过的诚实行为；授权后的下载失败会保留状态与原因并阻塞研究，用户需重试成功或提交有理由的部分分析 override（叙事 insight 仅对已完成分析的参考生效）。
- 一次一个会话（单浏览器页）；多会话并存需要后续版本（不在本合同范围）。
- Chat 兼容模式下模型无法自主联网，研究广度依赖用户提供的来源数量与质量（UI 明示）。

## 测试

`tests/test_workbench.py`（28 项）：全闭环夹具测试（会话→来源→研究→核查→批准→选题卡→审核→确认→写稿→审核→交付）、chat 模式编造来源 fail-closed、坏引文降级、**B1 选题一致性回归**（莫斯科主题+图书馆夹具在研究/批准/写稿边界全拒、相邻考试主题与元数据伪装全拒、合理改写保留）、**B2 netfetch 确定性测试**（私网字面量/私网解析/混合解析/重绑定固定/离线 HTTP(S) 重定向/非 http 重定向/代理旁路防护）、**B3 就绪度与 override**（授权下载失败持久化、未完成分析阻断、重试清除与显式 override 记录）、**确定性完整五方综合链**（5/5 分析→对比注入研究与选题卡→脚本交付视图如实标注 5/5），以及 **ThesisPromptTests**（直接测试真实 prompt builder 的对比块渲染——防止真实构建路径再次只被 fake provider 覆盖）；`tests/test_webui.py`（路由层）：边界、body 上限、B1 负例 HTTP 400、partial_override 管道；浏览器 E2E 证据：`evaluations/issue23_workbench/`。
