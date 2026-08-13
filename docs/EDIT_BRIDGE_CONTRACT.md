# Audio Alignment + Visual Edit Bridge Contract（Unreleased）

本阶段把用户已经剪好口气的真人口播视频作为唯一 canonical timeline。系统不自动剪口气、不改变 reviewed Script / approved Research，不伪造词级时间戳，也不把 B-roll / Motion 原音混入主音轨。

流程为：不可变导入 Clean A-roll → 提取保留 presentation 语义的转录音频 → 确定性分块与带时间戳转录 → Script/Transcript 全局对齐 → 复用 Beat/Cue/Scene 身份 → 统一 Visual Placement → Edit Bridge JSON/Markdown/CSV → 纯视觉 Remotion Preview → 原 A-roll 音轨 presentation-preserving mux → 五组 QA。

关键边界：

- canonical machine time 是十进制秒；`HH:MM:SS.mmm` 只作可读表达。
- 30fps、ceil 和 exclusive OUT 只属于 Aligned Preview 派生字段。
- word/token 才能成为精细 ready placement；segment-only 是 coarse。
- 分块边界高风险、重复候选、漏读或同起点选择歧义不能变成 false-ready。
- `placement_status` 与 `timing_status` 正交。可靠 Motion 时长不一致是 warning，不抹掉 placement。
- 只有 ready Placement 进入 Preview。其余项目保留在 marker package 和 warnings 中。
- Clean A-roll 音频是唯一主音轨，原正偏移和内部静音必须保留。
- Rights/Reuse 提示不进入制作 Gate；来源、身份、事实 grounding、文件 path/SHA/MIME/codec 仍必须通过。
- synthetic pass 只说明实现和对抗测试通过；真实用户拖入实际 Clean A-roll 并审看成片前，不得声称真实 E2E 或 V1.0 pass。
