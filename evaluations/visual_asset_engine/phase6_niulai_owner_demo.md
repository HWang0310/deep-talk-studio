---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'e61f3493-2c1c-45f4-87dd-bbbafa4ccec9'
  PropagateID: 'e61f3493-2c1c-45f4-87dd-bbbafa4ccec9'
  ReservedCode1: '75bb776e-7687-42a0-adfe-c5b91a4609d1'
  ReservedCode2: '75bb776e-7687-42a0-adfe-c5b91a4609d1'
---

# DT-CORE-6-001 Phase 6 — Owner-visible Micro Demo（真实《牛来》A-roll）

- Date: 2026-09-02 (`Asia/Shanghai`)
- Branch: `agent/phase6-niulai-owner-demo`
- Base: `db172ce`（Phase 5 accepted baseline）
- Gate result: **DEMO_RUN_COMPLETED — OWNER_REVIEW_PENDING**

## 范围与边界

- 仅运行了"有限、有意义"的真实机会（非覆盖配额），不修改 `main` / tag / release / `agent/multi-asset-studio`
- 时间窗口全部绑定真实 `semantic-timeline/1`（`timing_provenance: actual_aroll_alignment`）
- 不选 winner、不自动剪辑；全部媒体留在 `.artifacts/**`（gitignored 私有）
- 本文件为 de-contented evidence：只含产品级结论，不含任何私有/内容材料

## 运行摘要

两轮运行（均 `production_profile=RICH`，本地 pin 配置 `config/visual-asset-plugins.local.json`）：

1. **run-r0001** — 隐喻/数据型机会（VO-ST002/003/004）
2. **run-r0002-mechanism** — 机制型机会（VO-ST008/015），因为 MG generation 只实现 causal / mechanism transmission

## 候选结果（4 个 READY，均非 placeholder、中文可读、H.264 1920×1080）

| 机会 | 插件 | 结果 | 说明 |
|---|---|---|---|
| VO-ST002（隐喻） | Illustrated Metaphor | **READY**（3s） | 拟人化隐喻（负重拖拽） |
| VO-ST008（机制） | Illustrated Metaphor | **READY**（8s） | 隐喻抽象（拉拽重物） |
| VO-ST015（机制循环） | Illustrated Metaphor | **READY**（8s） | 隐喻抽象（播放意象） |
| VO-ST015（机制循环） | **MG** | **READY**（7s） | **causal-flow 机制因果链，直接呈现传播循环** |

## 插件边界观察（产品级结论，均为真实行为而非配置错误）

- **MG**：generation 仅实现 causal / mechanism transmission（`UNSUPPORTED_OPPORTUNITY` 于隐喻/数据机会）；对含精确数值的机制机会（VO-ST008）主动 ABSTAIN（避免把精确数值伪装成机制图），对纯机制机会（VO-ST015）正常产出 causal-flow 候选。
- **Illustrated Metaphor**：对精确数值/数据比较主动 ABSTAIN（"装饰性隐喻会牺牲证据精度"，触发关键词：数字/数值）；对机制机会产出的隐喻画面语义相关度中等（偏抽象，未直接呈现机制逻辑）。
- **Hand-drawn Animation**：对隐喻/数据机会 ABSTAIN（未找到匹配组合语法）；对机制机会 SUITABLE 但**生成阶段 FAILED**——只输出帧序列（91 帧）未完成契约要求（无最终 media/manifest），被 Core 正确判为生成失败。

## 语义相关性与诚实性

- 真实 A-roll 时间窗口绑定真实 alignment；候选为诚实插图/示意，不伪造精确数字。
- 视觉抽查（抽帧 + 视觉模型）：
  - MG ST015：与传播循环机制高度相关，中文可读，无占位符/乱码。
  - Illustrated 三候选：中文清晰、风格统一、无占位符；但对机制机会的隐喻表达与机制语义相关度偏弱（ST015 仅"短视频/播放"意象）。

## 产品结论

`PRODUCT_USABLE_DEMO: PASS` — 三插件在真实内容上可独立运行、非排他、诚实边界清晰，
但**单一机会的多插件候选并存只在机制型机会（VO-ST015）出现**；数据型机会三插件均无候选（诚实拒绝）。
Owner 需在 NLE 手动选择使用，Core 不选 winner。

## 后续待办（Owner 决策）

1. Owner 查看 `owner-review-pack` 的 contact sheet / media，确认视觉方向
2. 若认可，进入 Phase 6 创作者手动组装（NLE）环节
3. Hand-drawn 生成 FAILED 需插件侧修复（提交帧序列但未完成契约 media），可作为后续优化项