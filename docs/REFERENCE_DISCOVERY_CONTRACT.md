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

> **状态：IMPLEMENTED_UNRELEASED，等待 Nexus 审核（Issue #24）。** 本合同描述 Creater Workbench Phase 1 的最小可用能力：按主题 + 0–5 条用户链接，产出最多 5 条带完整溯源的 B 站参考视频候选。它不是 v1.0.0 的一部分，不是生产默认能力，不改变任何既有 canonical contract。

## 范围

输入：主题文本 + 0–5 条可选 B 站参考（`www.bilibili.com/video/BV…` 完整链接或裸 BV 号）。

输出：版本化 `reference-candidate-set/1` JSON 工件（默认写入 gitignored `discoveries/`），机器可读、字段校验 fail-closed，供后续本地 Web UI 直接调用。

不做的事：不下载视频/音频/字幕，不读取浏览器 Cookie 或登录凭据，不绕过平台风控，不把参考视频当作 Research 事实来源，不宣称站内整体排名。

## 调用方式

```bash
./scripts/deeptalk discover-references "主题" \
  --url "https://www.bilibili.com/video/BVxxxx" --url BV1yyyyyyyyy \
  --alias "备选查询词" --require-term 关键词 --exclude-term 排除词 \
  --max-candidates 5 --output discoveries --print-json
```

退出码：`0` = 已产出候选；`2` = 无候选或参数非法。

Python 侧可注入 transport（离线确定性测试）与自定义 provider。

## 选择流水线（确定性）

1. **用户链接优先**：URL → BVID 规范化；格式错误、重复、超过上限、视频无效/失效/受限均以类型化 reason 记录在 `rejected_user_urls`，绝不静默丢弃；元数据获取被平台阻断的用户链接保留为 `unverified`/`metadata_fetch_blocked` 候选。用户候选永远排在自动候选之前；同一 BVID 在搜索中再次出现会合并 query 溯源。
2. **有界搜索**：查询计划 = `[主题, 主题去通用后缀变体（事件/视频/完整版/最新…）, *aliases]`，去重后上限 4 条，每条仅第 1 页。
3. **相关性判定（无发明语义）**：`excluded_terms`/`required_terms` 先行；命中主题锚点（去通用后缀的完整主题串）或 ≥2 个主题 3-gram 判为相关；判定、理由、命中词逐候选记录。变体措辞（如字面被平台改写）可通过 3-gram 命中保留；泛科普内容（仅命中单个词）被排除并写入 `excluded_preview`。
4. **播放量核验（有界）**：相关自动候选按搜索片段播放量预排序后，最多核验 15 条 per-video 元数据；搜索片段数字永不作为已核验播放量呈现。`verified` 必须来自 per-video API；核验被阻断的候选标 `unverified` 且 `view_count` 为 null，排序置于已核验之后。
5. **排序与补齐**：自动候选按（已核验优先 → 播放量降序 → 片段值降序 → BVID 升序）确定性排序，补齐到 `max_candidates`；不足时不强行凑数，`action_note` 给出扩大检索或手动补链建议。

## 工件契约（fail-closed 校验）

顶层：`artifact_version`（恒 "1"）、`candidate_set_id`（`REF-` 前缀）、`generated_at`、`topic`、`provider`、`query_plan`、`user_supplied_urls`、`candidates`、`rejected_user_urls`、`search`、`status`、`action_note`、`limitations`。

候选字段：`bvid`、`url`、`title`、`uploader`、`published_at`、`view_count`、`view_count_status`（verified/unverified/unavailable）、`view_count_source`（per_video_api/search_result/none）、`search_snippet_view_count`、`duration_sec`、`user_supplied`、`found_via_queries`、`relevance{decision,reason,matched_terms,anchor_hit,trigram_hits,score}`、`retrieval_note`、`fetched_at`。额外/缺失字段、违反排序规则、verified 无整数播放量等一律校验失败。

`search` 块记录逐查询状态（ok/blocked/failed + 结果数）、`raw_result_count`、`deduplicated_count`、`verification_budget`、`verification_performed`、`excluded_preview`、`not_selected_relevant` 与 `coverage_note`——排序仅代表检索范围内（已检索、相关、已核验）的最高播放量，**不代表 B 站站内整体排名**。

## 访问方式与合规边界

- 仅匿名访问浏览器首访即用的公开端点（搜索 + 单视频元数据）；可通过 B 站自身公开的访客初始化端点获得随机、与账号无关的访客标识（`--no-visitor-identity` 关闭）。标识仅存于内存，不写日志、不写工件。
- HTTP 412/403/429、验证码、登录墙、反爬拦截一律标 `blocked`/`degraded` 并降级为用户提供链接的离线补齐；永不重试绕过、伪造签名或解验证码。瞬时故障（网络、5xx）最多重试 2 次并退避。
- 内建限速：请求间隔默认 1 秒、超时 15 秒、查询 ≤4 条 ×1 页、单视频核验 ≤15 次。

## 已知限制

- B 站 Web 端点为非合同化公开接口，随时可能变更或失效；本合同不承诺其可用性。
- 字面相关性启发式对刻意规避措辞（如"X日旗""菊花旗"）依赖 3-gram 重叠；`--require-term`/`--alias` 可人工强化，LLM 辅助相关性判定是未来显式配置项，本期未实现。
- 播放量是传播信号，不是事实质量；参考视频仅用于研究叙事结构与风格（见 AGENTS.md 内容与研究安全规则）。

## 测试

- 离线确定性单测：`tests/test_reference_discovery.py`（注入 fake transport/provider；覆盖 URL 规范化、去重、排序、缺失/冲突播放量、低相关排除、不足结果、412 降级、工件校验、CLI 装配）。
- 真实网络冒烟：`tests/test_reference_discovery_live.py`，仅 `DEEPTALK_LIVE_BILI_SMOKE=1` 显式开启，一次运行、默认限速，CI 不依赖 B 站。
