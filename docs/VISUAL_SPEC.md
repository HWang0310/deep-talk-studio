# Visual Spec 0.5

Visual Spec 是 Research-grounded 画面意图，不是已经完成的视频时间线。

每项必须包含 `visual_id`、Beat、类型、purpose、标题/副标题、事件/数据/节点、Claim/Evidence、attribution、`1920×1080`、16:9、安全区、建议秒数、动画意图、style tokens、屏幕文字、render target hints 和实际 SVG 的路径/大小/SHA-256。

| 类型 | 必需数据 | 核心校验 |
|---|---|---|
| timeline | Research timeline events | 日期与 Claim 组合必须原样存在 |
| bar | numeric data points | 数值必须出现在绑定 Claim 文本 |
| comparison | left/right items | Claim/Evidence 必须存在且对应 |
| diagram | nodes/edges | Node ID 唯一，Edge 端点必须存在 |

默认画面风格是现代、克制、高对比、高信息密度，不使用模板化“AI 蓝”。SVG 是 V0.5 的正式最小 render target。`remotion_candidate` / `hyperframes_candidate` 仅说明未来适合转成动画，不表示已有 Composition、音频同步或完整视频。

