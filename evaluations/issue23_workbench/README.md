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

> **结论：全链路验收通过。** 普通用户仅通过产品界面，从输入选题一路走到获得**经独立审核通过、Gate pass 的原创口播文稿**（真实验收目标达成）。LLM 文本由本地 mock 夹具生成并诚实标注；B 站检索/下载/转写与全部引擎门禁真实执行。过程中发现并修复 3 个真实产品缺陷（各配回归测试）。

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

## 诚实声明

- LLM 生成文本（研究/核查/选题卡/写稿/审核）全部来自**本地 mock 夹具**（`.temp/mock_llm_usage.log` 逐请求留痕）；不宣称任何真实模型商输出。
- B 站检索、播放量核验、下载授权与存档、ffmpeg/whisper 本地转写、canonical 引擎校验与质量门禁全部真实执行；平台限速/拒绝时如实失败（步骤 04）。
- 本报告不代替 Nexus 独立审核；`evaluations/issue23_workbench/` 之外无新证据目录。
