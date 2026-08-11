# Visual Spec 0.5（V0.5.1 加固）

Visual Spec 是 Research-grounded 画面意图，不是已经完成的视频时间线。

每项必须包含 `visual_id`、Beat、类型、purpose、标题/副标题、事件/数据/节点、Claim/Evidence、attribution、`1920×1080`、16:9、安全区、建议秒数、动画意图、style tokens、屏幕文字、render target hints 和实际 SVG 的路径/大小/SHA-256。

| 类型 | 必需数据 | 核心校验 |
|---|---|---|
| timeline | Research timeline events | 日期、Claim、Evidence 组合和 label 必须原样存在 |
| bar | numeric data points | 每项 Claim/Evidence 对应；数值使用数字边界，label 必须显示同值 |
| comparison | left/right items | 每个内部项的 Claim/Evidence 必须存在且对应 |
| diagram | nodes/edges | Node ID 唯一且每个 node 有 Research Claim；Edge 端点必须存在 |

默认画面风格是现代、克制、高对比、高信息密度，不使用模板化“AI 蓝”。SVG 是 V0.5 的正式最小 render target。`remotion_candidate` / `hyperframes_candidate` 仅说明未来适合转成动画，不表示已有 Composition、音频同步或完整视频。

Visual 的顶层 Claim/Evidence refs 不能替子项“代签”：timeline、bar、comparison 的顶层 refs 必须等于子项的确定性并集。任何内部 C404、E404 或把别的 Claim 的 Evidence 挂进当前项的情况均在 render 前拒绝。Generated Visual 始终只是 context/illustration，不能冒充现实世界 evidence。
