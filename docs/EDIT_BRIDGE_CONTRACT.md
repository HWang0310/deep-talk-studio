# Audio Alignment + Visual Edit Bridge Contract（Unreleased）

本阶段把用户已经剪好口气的真人口播视频作为唯一 canonical timeline。系统不自动剪口气、不改变 reviewed Script / approved Research，不伪造词级时间戳，也不把 B-roll / Motion 原音混入主音轨。Basic Subtitle V1 从同一 Timed Transcript 确定性生成并烧录进最终 Aligned Preview。

历史 Preview 兼容流程由 `run_real_edit_bridge_session` 所有：不可变导入 Clean A-roll → 提取保留 presentation 语义的转录音频 → 确定性分块与带时间戳转录 → Subtitle Artifact/SRT → Script/Transcript 全局对齐 → 统一 Visual Placement → Edit Bridge → 烧录字幕的 Remotion Preview → 原 A-roll 音轨 mux → canonical QA。当前默认用户交付改由 `docs/ASSET_PACK_EDIT_MAP_CONTRACT.md` 规定：同一真实对齐链只生成 QA-ready 独立视觉素材与 Edit Map，用户在 NLE 手工完成最终剪辑。provider、时钟、ID 与 renderer 可以注入，但阶段顺序和正式 validator 不可注入。

关键边界：

- canonical machine time 是十进制秒；`HH:MM:SS.mmm` 只作可读表达。
- 30fps、ceil 和 exclusive OUT 只属于 Aligned Preview 派生字段。
- word/token 才能成为精细 ready placement；segment-only 是 coarse。
- 分块边界高风险、重复候选、漏读或同起点选择歧义不能变成 false-ready。
- `placement_status` 与 `timing_status` 正交。可靠 Motion 时长不一致是 warning，不抹掉 placement。
- 只有 ready Placement 进入 Preview。其余项目保留在 marker package 和 warnings 中。
- Clean A-roll 音频是唯一主音轨，原正偏移和内部静音必须保留。
- 字幕只使用真实 Transcript unit boundary。segment-only 保持 coarse；Subtitle/Profile/Transcript digest、renderer enablement 和 Preview Manifest binding 必须由 QA 重推导。
- Rights/Reuse 提示不进入制作 Gate；来源、身份、事实 grounding、文件 path/SHA/MIME/codec 仍必须通过。
- historical absolute path 是 digest-covered 证据，不因工作区迁移而改写。`align-video` 通过 machine-local canonical root、显式可信 historical roots 和消费者推导的 artifact-relative identity 生成独立 runtime observation；任何 unknown root、traversal、identity mismatch、symlink、missing、size/SHA mismatch 或 artifact tampering 均失败关闭。
- machine-local 配置若给出 `current_production_id`，只接受该精确且 bindings 合格的 Production。未配置时的兼容 fallback 只按 Artifact 自有时间、revision、identity 与 lexical path 确定性排序，不读取 filesystem mtime；正式不可变 current-production index 仍是后续架构项。
- synthetic pass 只说明实现和对抗测试通过；真实用户拖入实际 Clean A-roll 并审看成片前，不得声称真实 E2E 或 V1.0 pass。
