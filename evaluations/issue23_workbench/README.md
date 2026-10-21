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

# Issue #23 — 创作工作台浏览器 E2E 验收证据

> **Round 1（已被 Nexus 标记 CHANGES_REQUIRED）：全链路导航走通，但暴露 3 个真实缺陷已修复（见下），并按 Nexus 审查意见补充 B1/B2/B3 三个阻断项的修复。**
> **Round 2（本版，Nexus B1/B2/B3 纠偏后）：主题一致的 MSU 夹具全链复测通过 + 5/5 真实转录 + 浏览器负例演示（B1 偏题阻断、B2 回环/私网抓取拒绝）。创作内容质量标注 UNVERIFIED（本地 mock 生文）。**

## 环境

- 仓库：`/Users/hwang/Movies/Program/DeepTalk/deep-talk-studio`（分支 `agent/issue23-workbench`）
- UI：`http://127.0.0.1:8321`（本机回环，`python -m deeptalk_studio ui`）
- LLM：**本地 mock chat-completions 服务（127.0.0.1:8931，`.temp/mock_llm_server.py`，gitignored E2E 夹具）**——脚本化回复与 `tests/test_workbench.py` 同源，绝不冒充真实模型商输出
- 真实环节：B 站检索（匿名 API，播放量逐条核验）、yt-dlp 下载（匿名、无 cookie、≤720p、900s/条）、ffmpeg 抽音轨、whisper.cpp large-v3 本地转写、canonical Research/Fact-Check/Thesis/Script 引擎与全部质量门禁
- 会话：`workbench/sessions/WBX-abe47806511330ec/`（gitignored，含全部授权存档与叙事研究文件）
- 选题：`莫斯科大学留学生旭日旗事件`（E2E 的研究文档使用夹具主题「本市图书馆夜间开放试点」 —— mock 是诚实夹具，验证链路而非内容匹配）

## 步骤记录（全部真实浏览器操作）

| # | 步骤 | 结果 | 证据 |
|---|---|---|---|
| 01 | 打开工作台首页 | ✓ 五步流程 UI 渲染 | `screenshots/01-workbench-home.png` |
| 02 | 设置面板：chat 模式（127.0.0.1:8931/v1 + mock 模型 + 下载目录）→ 保存 → 测试连接 | ✓ Key 掩码显示、「连接正常」 | `screenshots/02-settings-test-connection-ok.png` |
| 03 | 输入主题「莫斯科大学留学生旭日旗事件」→ 开始本集创作 | ✓ 真实 B 站检索返回 **5 条已核验候选**（播放量 200K–589K），会话建立 | `screenshots/03-references-found-5.jpg` |
| 04 | 授权声明（逐字存档）→ 授权获取 | **首轮如实失败**（见 Bug 1）；第 1 条音频流被平台限速 ~2KB/s，900 秒超时不绕过；第 2 条下载成功（授权声明 + SHA256 + 时长完整存档） | `references/*/acquisition.json` |
| 05 | 修复 Bug 1/2 后再次授权获取 | ✓ 幂等跳过已下载条目；断点续传补齐第 1 条；**全部 5 条真实下载完成**（约 168MB，含 589K 播放的 10:52 长视频） | 下载目录 `/Users/hwang/Movies/DeepTalk参考视频/` |
| 06 | 第 1 条本地分析（ffmpeg 抽音轨 → whisper.cpp large-v3 `--dtw large.v3`） | ✓ 652 秒 / **503 段**真实中文转写落盘；叙事研究（hook/pacing/结构模式/top_terms/takeaways）+ 确定性指标（5.85 字/秒）注入 | `screenshots/04-reference-analyzed-whisper.jpg`、`transcript.json`/`study.json` |
| 07 | 中断剩余 4 条分析（E2E 最小验收路径：本地 large-v3+DTW 转写慢，产品如实报错展示） | ✓（杀转写进程后 UI 展示真实错误 `本地语音识别失败：read_audio_data…`，4 条保留「已下载待分析」状态可后续补跑） | `screenshots/04`（状态行残留说明：研究草稿先前的 Gate fail 摘要行未刷新，属已知 P3 瑕疵） |
| 08 | 添加研究来源 ×2（粘贴正文，真实抓取不可用时的人工路径） | ✓ S1 示例新闻社报道 / S2 市财政局预算说明 | 会话 `sources/` |
| 09 | 生成研究草稿 | ✓ 草稿 r0001 落盘 canonical `reports/`（研究 mode 记录 openai_api + user-supplied 来源） | session.json research.draft_path |
| 10 | 执行独立核查（真实 Fact-Check 引擎 + 引文逐字重核） | ✓ **3 条主张已核查 · 高风险未解决 0 · 质量 Gate：pass** | `screenshots/05-fact-check-pass.jpg` |
| 11 | 批准研究（明确批准词） | ✓ `ready_for_script`，批准快照 r0002 存档 | session.json |
| 12 | 生成选题卡（修复 Bug 3 后区域可达） | ✓ CTC 卡片草稿（core_question/core_thesis/差异化角度/钩子承诺） | UI 呈现 |
| 13 | 独立审核选题卡 | ✓ 逐项检查表全 Pass，Thesis Gate：pass | `screenshots/06-thesis-review-pass.jpg` |
| 14 | 人工确认（含「确认」+「进入写稿」） | ✓ `approved_for_script` | session.json |
| 15 | 生成并审核口播稿（canonical 引擎 + 33 项独立 Script Review） | ✓ **《夜间图书馆：谁在用，谁买单，谁来评》· 487 字 · 1.9 分钟 · 6 段 · 审核 Gate：pass**，全文 + 提词器/编辑稿三格式落盘 canonical `script_drafts/`（r0001 草稿 + r0002 定稿 + review 工件） | `screenshots/07-script-delivered-gate-pass.jpg` |
| 16 | 最终交付验证（公开 API `GET /api/workbench/script/final`） | ✓ status=reviewed，gate=pass，teleprompter 559 字符，文件存在 | curl 复验 |

## E2E 发现并修复的真实产品缺陷（均配回归测试）

### Bug 1（阻断级）：acquire/analyze 状态持久化回调签名不匹配

- **现象**：第 2 条下载成功、`acquisition.json` 落盘后 UI 报「这一步执行失败：TypeError：unhashable type：'dict'」，第 3–5 条不再执行，会话状态丢失。
- **根因**：`SessionStore.update` 协议是 `mutate(session_dict)`（session 为第一个位置参数），而 `flow.acquire_references`/`analyze_reference` 的 `_mark(ref_bvid=bvid, …)` 把 session dict 落进 `ref_bvid` → `setdefault(dict, …)` Typeerror。
- **为何 7/7 单测全绿**：测试从未执行这两个真实方法体——acquire 后手动用正确签名的 lambda 写状态，analyze 整个方法被 fake 替换。**浏览器 E2E 首次真实执行即暴露。**
- **修复**：`flow.py` 两处 `_mark` 第一参数接收 session dict；在 store.load 的最新状态上更新（不再闭包引用旧快照）。回归测试 `test_acquire_references_persists_state_real_flow_path` / `test_analyze_reference_persists_state_real_flow_path` 走**真实方法体**断言持久化。

### Bug 2（体验级）：重复下载已下载参考

- 授权按钮把「已下载待分析」条目也算进获取目标（重复下载 + 重复授权存档）。前端 `runAcquisition` 区分「需下载 / 已下载直进分析」；服务端对媒体文件在磁盘的已下载条目幂等跳过（`skipped: already_downloaded`）。幂等 re-run 回归断言：acquirer 未被再次调用。

### Bug 3（阻断级）：④ 选题卡 / ⑤ 口播稿区域永不可达

- `renderThesis`/`renderScript` 以**自身**状态 `not_started` 判隐藏——研究批准后（research=ready_for_script）用户没有任何入口开始选题卡；选题卡确认后同样看不到写稿入口。真实用户在步骤 ③ 结束即死锁。
- 修复：区域可达性由**上游就绪状态**驱动（research ready → 显示 ④；thesis approved → 显示 ⑤）。这正是验收标准「普通用户能仅通过产品界面从选题走到文稿」的直接缺陷——**若不做浏览器级验证，单测无法发现**（路由层 HTTP 测试不渲染前端）。

### E2E 夹具说明（非产品缺陷）

- mock（`.temp/mock_llm_server.py`）script 分支对真实写稿 prompt 的 report 提取缺 `limitations`/`open_questions` 键导致 KeyError 被静默转 `{"error": …}` 外层报 schema 缺字段——已健壮化（setdefault）；except 分支补 usage 记录。gitignored，不进产品代码。
- 转写中断（步骤 07）是刻意的最小验收路径决策：5 条全部 large-v3+DTW 转写预计 1–2 小时；1 条完整证据已覆盖 P2 环节，其余条目文件就绪、状态诚实（已下载待分析），用户可随时补跑。

## 已知限制（记录，不修）

- 研究草稿的历史 Gate fail 摘要行在核查 pass 后未刷新（新行正确显示 pass，旧行残留）——P3 展示瑕疵。
- 长任务（下载/转写）无进度分解与取消机制，仅整段状态提示——后续版本范畴。
- 一次一单会话；多会话未在本合同范围。

## 截图（screenshots/，真实浏览器捕获）

1. `01-workbench-home.png` — 五步流程首页
2. `02-settings-test-connection-ok.png` — 设置 + 连接测试通过（Key 掩码）
3. `03-references-found-5.jpg` — 真实 B 站检索 5 条已核验候选
4. `04-reference-analyzed-whisper.jpg` — 第 1 条完整分析（652s/503 段）+ 4 条已下载待分析
5. `05-fact-check-pass.jpg` — 独立核查通过（Gate pass + 批准入口）
6. `06-thesis-review-pass.jpg` — 选题卡审核逐项全过 + 人工确认
7. `07-script-delivered-gate-pass.jpg` — 口播稿完整全文交付（Gate pass，全页）

## 测试

- `tests/test_workbench.py` **9/9**（2 个真实方法体回归 + 幂等断言 + 全闭环夹具 + fail-closed 用例）
- `tests/test_webui.py` **49/49**（含工作台路由边界/body 上限/全闭环 HTTP 层）
- **全量套件：Ran 1041 tests in 204.4s — OK（skipped=7，0 failed，退出码 0）**（含本轮新增 14 个测试：workbench 9 + webui 路由 3 + 升级断言 2）。

## Round 2 — Nexus CHANGES_REQUIRED（B1/B2/B3）修复与复测证据

Nexus 审查意见（PR #33 @ `5a63795`，2026-10-21T15:02:58Z）提出三个阻断项，全部修复并按下述证据复测。

### B1 — 偏题研究/选题卡/口播稿无法再通过任何门禁（fail-closed）

- **修复**：新增 `ensure_topic_consistency`（主题信号词 = 中文字符二元组 + ASCII 词，覆盖率 < 20% 拒绝；语义改写保留）。检查点：①`generate_research` 保存前（本次观察到的错配——莫斯科选题 + 图书馆 payload——在写入前即被拒，不再静默改写 topic）；②`approve_research`（已核查报告偏题不能批准）；③`generate_thesis`/`approve_thesis`（选题卡偏题不能生成/确认）；④`generate_script`（报告、选题卡、以及**写好的口播稿终稿**全部复核——偏题脚本永不进入交付视图/不会显示 Gate pass）。
- **回归测试**（`tests/test_workbench.py::TopicConsistencyTests` + `tests/test_webui.py` HTTP 层）：
  - `test_off_topic_research_is_rejected_not_relabelled` —— 用**实际观察到的错配**（莫斯科大学主题 + 图书馆夹具）：研究生成被拒（HTTP 400，含「选题主题明显不符」），研究状态保持 not_started；
  - `test_off_topic_report_cannot_be_approved_and_cannot_drive_script` —— 报告完成后会话主题偏移 → 批准拒绝；
  - `test_off_topic_thesis_payload_is_rejected` —— 偏题选题卡 payload 拒绝；
  - `test_topical_paraphrase_still_passes` —— 语义改写（不含原主题字面串但含关键实体）不被误拒。
- **浏览器演示**：研究问题输入「主题不符测试」→ mock 刻意返回偏题 payload → UI 展示类型化阻断错误（见 round-2 截图）。

### B2 — 用户来源 URL 抓取公网限定（SSRF 防护）

- **修复**：新增 `workbench/netfetch.py` 取代裸 `urlopen`：仅 http(s) + 显式主机名（拒绝 userinfo）；**逐连接**解析（A/AAAA）并要求全部结果为公网单播（拒绝 loopback/私网/链路本地/CGNAT/测试网段/多播/保留——含 IP 字面量与域名解析两种路径）；连接**固定拨向**已验证地址（验证与拨号原子化，无 DNS 重绑定窗口）；重定向仅 http(s)、上限 4 跳（每跳同规则再验）；**显式禁用系统代理**（代理代拨会绕过 IP 校验）；解析失败/含糊一律 fail-closed 并引导粘贴正文回退。合法公网抓取契约（2MB 上限/文本抽取/≥50 字/SHA256）不变。
- **确定性测试**（`tests/test_workbench.py::NetFetchTests`）：11 类私网/回环/链路本地/文档网段 IP 字面量逐例拒绝（无任何 socket 活动）；域名解析到回环/私网、公网+私网混合、空解析、DNS 错误全部拒绝；重绑定模拟——首次解析公网、再次解析私网，连接只拨向已验证公网地址（证词：仅 1 次解析、从未尝试私网）；非 http 重定向拒绝（ftp/file）；代理环境变量下的行为验证（拒绝 192.168 目标而非回环代理地址，证明未走代理）。
- **浏览器演示**：`http://127.0.0.1:8931/v1/models`（回环）与 `http://192.168.1.1/`（私网）作为来源添加 → UI 展示「来源地址不是公网地址，已拒绝访问」；`https://www.baidu.com/robots.txt`（真实公网文本）→ 抓取成功入库（证明合法公网来源保留）。

### B3 — 五方观点综合：就绪度、显式 override、结构化对比与诚实标注

- **修复**：
  1. 参考 study schema 增加可选 `creator_viewpoint`（可归因观点立场概括——观点描述而非事实转述；prompt 明确要求；旧 study 回退「未提取到观点立场」）；研究/选题卡 system prompt 与 user prompt 重写：允许在差异化定位中**明确归因地概括**参考创作者观点，但绝不作为事实来源/证据支撑、绝不拼凑复述表达（`thesis_prompt.py` 原先「不引用其具体观点」的限制按 Owner 核心价值改为有边界的允许）。
  2. `generate_research` 强制就绪度：任何**已授权（已下载）参考**未完成分析 → 默认拒绝（错误明示 `已分析 N/共 M`）；仅在用户**显式勾选允许部分分析并填写 ≥10 字理由**后放行，理由逐字存档，session 记录 `reference_comparison.partial`（绝不把 1/5 标为完整综合；未授权/未下载的候选不算 pending——用户选择不下载的参考永不阻塞研究）。
  3. 确定性对比注入：`render_reference_comparison`（本地计算，无 LLM）——逐条「可归因观点 + 钩子/节奏/结构」+ N 方对比小结（高频结构模式、钩子取向分布、语速区间、反问句分布），硬性标注「绝不作为事实来源，禁止拼凑或复述表达」；同时注入研究 user prompt 与选题卡 user prompt。
  4. 诚实标注贯通全 UI：分析区「就绪度：已分析 N · 已下载待分析 K · 本集候选 Z」；研究区「参考分析就绪度：已分析 N/已授权 M」+ 部分分析 override 控件（仅 pending>0 时显示）；研究生成结果行「参考观点对比：已注入 N/M 条（可归因观点 X 条，部分分析/完整）」；口播稿交付区与终稿 API 携带 `reference_synthesis`（analyzed/eligible/viewpoint_count/partial）——交付视图永不显示无证据的「完整综合」。
- **回归测试**（`tests/test_workbench.py::ReferenceSynthesisTests`）：
  - `test_research_blocked_until_analysis_complete_or_explicit_override` —— 1/2 分析：无 override 阻断（错误含「1/2」）、理由不足拒绝、显式 override 放行且 `partial=True` 与理由入库；
  - `test_full_five_analysis_injects_comparison_and_chains_to_script` —— 确定性完整五方链：5 条全部分析 → 无需 override → 对比块注入研究与选题卡（断言 5 条可归因观点、`问题—事实—评价（5/5 条)` 统计、prompt 含硬性边界文案）→ 核查/批准/选题卡/确认/写稿全链 → 交付视图 `reference_synthesis` 如实 5/5（partial=False）。
  - 路由层（`tests/test_webui.py`）：partial_override/partial_reason HTTP 管道 + B1 负例 400。
- **真实证据（round 2 浏览器复测）**：**全部 5 条已授权参考均完成真实 whisper.cpp large-v3 转写**（`--dtw large.v3`；参考「五方综合真实转录记录」表），研究生成注入 5/5 对比（观点 5/5），最终口播稿（mock 组文但结构遵循真实对比结论——问题开场/先事实后评判/中段转折/结尾回扣）交付视图标注 5/5。

### 五方综合真实转录记录（round 2）

全部 5 条已授权参考均完成**真实**本地分析（ffmpeg 抽音轨 → whisper.cpp large-v3 `--dtw large.v3`，逐条真实转录与观点字段入库；观点文案为 mock 基于真实指标（标题/反问数/时长）确定性生成的格式化描述，转录与全部确定性指标为真实产物）：

| BVID | 标题（截断） | 时长(秒) | 转录分段 | 真实 whisper 转录 | 观点字段 |
|---|---|---|---|---|---|
| BV1NLnP63EvS | 南京人披旭日旗挑衅，莫大校友透露朋友圈内容… | 652 | 503 | 是 | 是 |
| BV1waJi6dEXe | 中国留学生公开身披旭日旗学生的露脸道歉视频… | 136 | 48 | 是 | 是 |
| BV1hJnG66Eng | 中国留学生披旭日旗：有些人啊，真是蠢透了 | 415 | 260 | 是 | 是 |
| BV1t4nc6KEvE | 中国留学生披旭日旗！开除遣返、官方定性… | 313 | 137 | 是 | 是 |
| BV1Phnc6eEvf | 鞠躬道歉这事就算完了吗？南京籍精日留学生… | 1657 | 778 | 是 | 是 |

总计 3173 秒（约 53 分钟）参考视频、1726 个真实转录分段；5/5 提取到可归因观点字段。终端日志：`.temp/` 后台任务 `real whisper analysis of all 5 references via UI API`（服务器串行执行真实 ffmpeg/whisper 调用）。

### Round 2 步骤记录（真实浏览器操作）

会话：沿用 round 1 会话 `WBX-abe47806511330ec`（莫斯科大学主题；round 2 用主题一致的 MSU 夹具重做研究链，旧图书馆研究报告工件保留在 canonical 树中作为历史，不删除不覆盖）。

| # | 步骤 | 结果 | 证据 |
|---|---|---|---|
| 01 | 真实转录补齐 | **5/5 全部完成真实 whisper.cpp large-v3 转写**（含 round 1 已完成的第 1 条重跑以补观点字段；记录见「五方综合真实转录记录」表） | 后台任务日志 + `references/*/transcript.json` |
| 02 | 就绪度展示 | ✓ 「已分析 5 · 已下载待分析 0 · 本集候选 5」+「已分析 5/已授权 5 条（完整分析）」 | `screenshots/08` |
| 03 | B2 负例：回环来源 `http://127.0.0.1:8931/v1/models` | ✓ 拒绝「来源地址不是公网地址（127.0.0.1），已拒绝访问」 | `screenshots/09` |
| 04 | B2 负例：私网来源 `http://192.168.1.1/admin` | ✓ 拒绝「来源地址不是公网地址（192.168.1.1），已拒绝访问」 | `screenshots/09` |
| 05 | B2 正例：公网来源 `https://cn.bing.com/robots.txt` | ✓ 真实抓取成功入库（S3，kind=fetched）——期间发现并修复 netfetch 连接实现缺陷（见下「round 2 追加修复」），公网合法抓取保留 | `screenshots/09b` |
| 06 | 粘贴 MSU 夹具来源 ×2（S4 新闻社 / S5 校方通报，正文内明确标注「E2E 夹具正文，非真实报道」；引文与 mock 逐字校验一致） | ✓ | session sources |
| 07 | **B1 负例演示**：研究问题填「主题不符测试」→ 生成研究草稿 | ✓ mock 刻意返回图书馆 payload（round 1 观察到的真实错配）→ **阻断**「研究草稿与选题主题明显不符（关键内容一致度约 8%），已拒绝写入」 | `screenshots/10` |
| 08 | 清除触发词 → 生成研究草稿（研究问题为 MSU 主题方向） | ✓ 草稿落盘（3 主张 · 2 来源）；结果行「参考观点对比：已注入 5/5 条已分析参考（可归因观点 5 条）」 | `screenshots/11` |
| 09 | 执行独立核查 | ✓ 3 主张已核查 · 0 高风险未解决 · **质量 Gate：pass**（校验过程见下：夹具先触发引擎质量门禁真实的 confirmed_fact 双源与 attributes 要求，修正夹具后通过——引擎门禁未被放宽） | reviewed 报告 r0002 |
| 10 | 批准研究 | ✓ ready_for_script | — |
| 11 | 生成选题卡（MSU 主题一致） | ✓ 草稿生成（期间抓到并修复一个真实 bug：thesis_prompt 相对导入路径错误——单测的 fake provider 不走真实 prompt 构建，只有真实链路暴露，已补直接回归） | — |
| 12 | 独立审核选题卡 | ✓ 逐项全过，Thesis Gate：pass | `screenshots/12` |
| 13 | 人工确认（确认+进入写稿） | ✓ approved_for_script | — |
| 14 | 生成并审核口播稿 | ✓ **《莫斯科大学旭日旗事件：证据分三层，别让情绪跑在程序前》501 字 · 6 段 · 审核 Gate：pass**；状态行「审核通过：原创口播稿已交付 · 参考综合：5/5 条已分析参考进入对比」；交付行「参考综合：5/5 条已分析参考进入对比（可归因观点 5 条）」；提词器落盘 canonical `script_drafts/`，选题标注「莫斯科大学留学生旭日旗事件」 | `screenshots/13` |
| 15 | 终稿 API 复核（GET /api/workbench/script/final） | ✓ status=reviewed、gate=pass、topic=莫斯科大学留学生旭日旗事件、**reference_synthesis={analyzed:5, eligible:5, viewpoint_count:5, partial:false}**；session `reference_comparison` 完整记录 5 个 BVID | curl 复验 |

**最终文稿是否受参考分析影响**：是——mock 稿件结构（问题开场→媒体确证→群体表态→官方通报→信息转折→结尾回扣）刻意遵循 5/5 真实对比的确定性结论（全部参考采用「问题—事实—评价」结构与「先摆事实再评判」视角）；但创作内容质量标注 **UNVERIFIED**（mock 组文）。

#### Round 2 追加修复（复测中发现的真实缺陷）

1. **netfetch 连接实现缺陷**：初版 `_PinnedHTTPConnection` 整体覆盖 `connect()` 与 stdlib 行为漂移，导致部分真实公网目标（cn.bing.com）连接被重置。改为只替换 `HTTPConnection._create_connection` 钩子（验证+固定拨号），其余（重试/TLS/NODELAY）与 stdlib 完全一致——公网抓取恢复且防护不变（重绑定模拟回归更新断言）。
2. **thesis_prompt 相对导入路径错误**（`.prompts` → 应为 `.workbench.prompts`）：fake provider 不走真实 prompt 构建，只有真实链路暴露；修复后新增 `ThesisPromptTests` 直接测试真实 prompt builder（对比块渲染）防回退。
3. **mock 夹具两处语义修正（非产品缺陷）**：P2 category 不在 schema 枚举；C3 最初误标 confirmed_fact（单来源）触发引擎质量门禁诚实拒绝（confirmed_fact 需 ≥2 独立来源组、说法类主张需 attributes 证据）——按引擎要求改为新闻社文本补「确认处理决定」句形成真实双源互证后通过。**引擎门禁全程未放宽**。

#### 截图清单（round 2）

- `08-readiness-5of5-analyzed.jpg` — 5/5 就绪度 + 每条可归因观点展示
- `09-b2-ssrf-guard-rejects-loopback-private.jpg` — 回环/私网来源拒绝（127.0.0.1 / 192.168.1.1）
- `09b-b2-public-fetch-ok-after-fix.jpg` — 公网来源真实抓取成功（修复 netfetch 缺陷后）
- `10-b1-offtopic-blocked-in-browser.jpg` — 偏题研究生成被阻断（一致度 8%，round 1 错配不再发生）
- `11-msu-research-5of5-comparison.jpg` — 主题一致研究草稿 + 5/5 对比注入
- `12-msu-thesis-reviewed.jpg` — MSU 选题卡审核全过
- `13-msu-script-delivered-5of5-synthesis.jpg` — MSU 口播稿 Gate pass 全文交付 + 参考综合 5/5（全页）

### Round 2 测试与结果

- `tests/test_workbench.py` **23/23**（新增 NetFetchTests 6、TopicConsistencyTests 4、ReferenceSynthesisTests 2、ThesisPromptTests 2 + fake provider 增强；另含既有 9 项闭环与降级测试）
- `tests/test_webui.py`（含路由层 B1 负例 400 + partial_override 管道）全绿
- **全量套件（最终代码重跑）：Ran 1057 tests in 200.5s — OK（skipped=7，0 失败，EXIT=0）**（在 netfetch `_create_connection` 修复与 thesis_prompt 导入修复之后的最终代码上执行；1057 = 此前 1055 + 新增 ThesisPromptTests 2）

---

## 诚实声明

- **创作内容质量 UNVERIFIED**：LLM 生成文本（研究/核查/选题卡/写稿/审核）全部来自本地 mock 夹具（round 2 为主题一致的 MSU 夹具，`.temp/mock_llm_usage.log` 逐请求留痕）；不宣称任何真实模型商输出，亦不宣称文稿创作质量已达真实模型水准。
- B 站检索、播放量核验、下载授权与存档、ffmpeg/whisper 本地转写（round 2 覆盖全部 5 条）、canonical 引擎校验与质量门禁全部真实执行；平台限速/拒绝时如实失败。
- 本报告不代替 Nexus 独立审核；`evaluations/issue23_workbench/` 之外无新证据目录。
