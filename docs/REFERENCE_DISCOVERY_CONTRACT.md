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

# Reference Discovery Contract（B 站参考视频发现）v1

> **状态：NEXUS PASS / ACCEPTED / IMPLEMENTED_UNRELEASED；PR #25 已合入 `main`（Issue #24）。** 本合同描述 Creater Workbench Phase 1 的最小可用能力：按主题 + 0–5 条用户链接，产出最多 5 条带完整溯源的 B 站参考视频候选。它不是 v1.0.0 的一部分，不是生产默认能力，不改变任何既有 canonical contract。

## 范围

输入：主题文本 + 0–5 条可选 B 站参考（`www.bilibili.com/video/BV…` 完整链接或裸 BV 号）。

输出：版本化 `reference-candidate-set/1` JSON 工件（默认写入 gitignored `discoveries/`），机器可读、字段校验 fail-closed，供后续本地 Web UI 直接调用。

不做的事：不下载视频/音频/字幕，不读取浏览器 Cookie 或登录凭据，不绕过平台风控，不把参考视频当作 Research 事实来源，不宣称站内整体排名。

上限：用户最多 5 条、总候选最多 5 条（`max_candidates` 仅允许 1–5）。

## 调用方式

```bash
./scripts/deeptalk discover-references "主题" \
  --url "https://www.bilibili.com/video/BVxxxx" --url BV1yyyyyyyyy \
  --alias "备选查询词" --require-term 关键词 --exclude-term 排除词 \
  --max-candidates 5 --output discoveries --print-json
```

退出码：`0` = 已产出候选；`2` = 无候选或参数非法。带 `--print-json` 时 **stdout 只输出唯一完整 JSON 工件**（人类摘要全部转到 stderr，可直接 `json.loads`），无参数时人类摘要在 stdout。

Python 侧可注入 transport（离线确定性测试）与自定义 provider。

### Mac 本地 Web UI（Issue #26，IMPLEMENTED_UNRELEASED 待审）

```bash
./scripts/deeptalk ui          # http://127.0.0.1:8321/，仅绑定本机回环
```

零新依赖（Python 标准库 HTTP 服务）+ 原生中文创建者页面，直接调用本合同的服务与 Provider：每次点击"搜索"都是一个新的有界 run，完整保留 run 级风控熔断。端点仅三个：`GET /`（页面）、`GET /healthz`、`POST /api/discover`（唯一业务端点；请求体 `{topic, urls?}`，响应即本合同工件 JSON，`blocked/degraded` 同样返回 200 + 诚实 status 由 UI 呈现降级指引）。输入限制：请求体 ≤8KB（413）、主题 1–200 字、链接 0–5 条 × ≤300 字（400 + 类型化中文错误）；检索以锁串行化（一次一个有界 run，重复点击排队为新 run 而非绕过）。

**本机 HTTP 边界（Nexus 审核修复轮新增）**：除 127.0.0.1 绑定外，所有请求须通过回环边界检查——窄 `Host` 白名单（仅 `127.0.0.1:<监听端口>` / `localhost:<监听端口>`，防 DNS rebinding）、`Origin` 存在时必须同源（跨站与 `null` 来源 403，防 CSRF）；JSON API 强制 `Content-Type: application/json`（415），且不支持 `OPTIONS` 预检（跨源浏览器 JSON 请求无法送达）。任何 body 读取前先验证 `Content-Length`（单一、非负、≤上限：缺失/重复/非数字 411、负数 400、超限 413；不支持 `Transfer-Encoding`），处理线程带 socket 超时，杜绝无限 read。工件以排他创建（`O_EXCL`）落盘到固定目录，重名冲突不覆盖、返回安全错误。

## 选择流水线（确定性）

1. **用户链接优先**：URL → BVID 规范化；格式错误、重复、超过上限（>5）、视频无效/失效/受限均以类型化 reason 记录在 `rejected_user_urls`，绝不静默丢弃；元数据获取被平台阻断的用户链接保留为 `unverified`/`metadata_fetch_blocked` 候选。用户候选永远排在自动候选之前；同一 BVID 在搜索中再次出现会合并 query 溯源；**已被元数据拒绝的用户 BVID 再次出现在搜索中时被确定性排除（不重新请求、不进入自动候选、不崩溃）**。隐私：工件 `user_supplied_urls` 只存无参数 canonical URL；`rejected_user_urls[].input` 只存脱敏摘录（URL 去参去尾斜杠截断，非 URL 截断），原始输入绝不回显。
2. **有界搜索**：查询计划 = `[主题, 主题去通用后缀变体（事件/视频/完整版/最新…）, *aliases]`，去重后上限 4 条，每条仅第 1 页。
3. **相关性判定（无发明语义）**：`excluded_terms`/`required_terms` 先行；命中主题锚点（去通用后缀的完整主题串）或 ≥2 个主题 3-gram 判为相关；判定、理由、命中词逐候选记录。变体措辞（如字面被平台改写）可通过 3-gram 命中保留；泛科普内容（仅命中单个词）被排除并写入 `excluded_preview`。
4. **播放量核验（有界）**：相关自动候选按搜索片段播放量预排序后，最多核验 15 条 per-video 元数据；搜索片段数字永不作为已核验播放量呈现。`verified` 必须来自 per-video API；核验被阻断的候选标 `unverified` 且 `view_count` 为 null，排序置于已核验之后。
5. **排序与补齐**：自动候选按（已核验优先 → 播放量降序 → 片段值降序 → BVID 升序）确定性排序，补齐到 `max_candidates`；不足时不强行凑数，`action_note` 给出扩大检索或手动补链建议。

## 工件契约（fail-closed 校验）

顶层：`artifact_version`（恒 "1"）、`candidate_set_id`（`REF-` 前缀）、`generated_at`、`topic`、`provider`、`query_plan`、`user_supplied_urls`、`candidates`、`rejected_user_urls`、`search`、`status`、`action_note`、`limitations`。

候选字段：`bvid`、`url`、`title`、`uploader`、`published_at`、`view_count`、`view_count_status`（verified/unverified/unavailable）、`view_count_source`（per_video_api/search_result/none）、`search_snippet_view_count`、`duration_sec`、`user_supplied`、`found_via_queries`、`relevance{decision,reason,matched_terms,anchor_hit,trigram_hits,score}`、`retrieval_note`、`fetched_at`。额外/缺失字段、违反排序规则、verified 无整数播放量等一律校验失败。

`search` 块记录逐查询状态（ok/blocked/failed + 结果数）、`raw_result_count`、`deduplicated_count`、`verification_budget`、`verification_performed`、`excluded_preview`、`not_selected_relevant` 与 `coverage_note`——排序仅代表检索范围内（已检索、相关、已核验）的最高播放量，**不代表 B 站站内整体排名**。

## 访问方式与合规边界

- 仅匿名访问浏览器首访即用的公开端点（搜索 + 单视频元数据）；可通过 B 站自身公开的访客初始化端点获得随机、与账号无关的访客标识（`--no-visitor-identity` 关闭，Nexus 已确认此产品选择）。标识仅存于内存，不写日志、不写工件。
- **风控熔断（run 内 circuit latch）**：同一次发现运行中首次真实遇到 HTTP 403/412/429、HTML 拦截页或 API 层已知风控码（如 `code=-412`）时，Provider 立即进入阻断状态，后续所有 `search_videos`/`fetch_video_metadata` **不再发起任何网络请求**，直接返回 blocked；产物 status 诚实降级为 `degraded`/`blocked`，绝不误报 ok。**匿名访客初始化请求本身遇风控（412/403/429、HTML 拦截页、API `-412`）同样触发熔断**——运行在任何搜索或元数据请求发出之前即停止；访客初始化的良性失败（网络错误、5xx、非风控 JSON）仍静默降级，运行继续（不带访客标识）。普通超时/5xx 不触发熔断（仍为可重试的 `failed`）。无任何绕过机制。
- HTTP 412/403/429、拦截页、以及 API 层已知风控码（如 `code=-412`）一律标 `blocked`/`degraded` 并降级为用户提供链接的离线补齐；未知非零 API 码保持 `failed`，不猜测归类；永不重试绕过、伪造签名或解验证码。瞬时故障（网络、5xx）最多重试 2 次并退避。
- 内建限速：请求间隔默认 1 秒、超时 15 秒、查询 ≤4 条 ×1 页、单视频核验 ≤15 次。

## 已知限制

- B 站 Web 端点为非合同化公开接口，随时可能变更或失效；本合同不承诺其可用性。
- 字面相关性启发式对刻意规避措辞（如"X日旗""菊花旗"）依赖 3-gram 重叠；`--require-term`/`--alias` 可人工强化，LLM 辅助相关性判定是未来显式配置项，本期未实现。
- 播放量是传播信号，不是事实质量；参考视频仅用于研究叙事结构与风格（见 AGENTS.md 内容与研究安全规则）。

## 测试

- 离线确定性单测：`tests/test_reference_discovery.py`（注入 fake transport/provider；覆盖 URL 规范化、去重、排序、缺失/冲突播放量、低相关排除、不足结果、412/API-412 降级、run 内风控熔断——首个 query blocked 后不再请求后续 query、单视频核验 blocked 后不再请求其余视频、部分候选已核验时诚实降级、多用户 BV 首个 blocked 后不再请求其余 BV、**匿名访客初始化 SPI 遇 412/API-412/HTML 拦截页时整 run 熔断（默认 `use_visitor_identity=True` 路径，全 run 仅 1 次网络请求）、SPI 良性失败不熔断继续**、元数据失效用户 BVID 与搜索重叠的确定性排除、候选上限 5、输入脱敏与工件隐私、`--print-json` 纯 JSON stdout、工件校验、CLI 装配）。
- 真实网络冒烟：`tests/test_reference_discovery_live.py`，仅 `DEEPTALK_LIVE_BILI_SMOKE=1` 显式开启，一次运行、默认限速，CI 不依赖 B 站。
