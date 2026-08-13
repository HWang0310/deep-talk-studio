# Audio Alignment + Visual Edit Bridge Design

**文档状态：** Design Contract Hardened Review Candidate

**产品状态：** Unreleased

**产品基线：** `f087b6c295a9e015357e4433b103428b16a5e6be`

**Hardening 前 reviewed Design HEAD：** `f9cb70315ea02dbe83353d7c4eee97800dcddccf`

**Schema 标识说明：** 本文使用的 `*/1` 表示工件契约第一版，不代表 DeepTalk Studio 已成为 V1.0。产品是否达到 V1.0 只由真实真人视频 E2E 验收决定。

## 1. 目标与设计原则

本阶段把用户已经剪好口气的 Clean A-roll 设为整期视频唯一 canonical timeline，将 reviewed Script 的稳定 Beat、Material Cue、现有 Production Scene、真实素材与 QA-ready Motion 确定性映射到这条时间轴，输出带 IN、OUT、duration、layout 的 Edit Bridge Package 和 `ALIGNED_PREVIEW.mp4`。

系统负责机械剪辑安排，用户只保留审美修改权。以下原则贯穿全部模块：

- Clean A-roll 只读、不可覆盖，不改变剪辑结构或总时长。
- reviewed Script 是 intended narration；Clean A-roll 是 actual narration timeline；两者都不被改写。
- Speech-to-Text provider 只提供带来源的转录数据，不拥有 alignment status、confidence、Gate 或最终 timecode。
- canonical timestamp 只能来自 provider 的真实 timestamp boundary 和确定性序列对齐，不由 LLM 生成。
- Script Beat → Material Cue → Production Scene 的现有身份链继续作为唯一身份链，不创建第二套 Scene。
- Clean A-roll、Real Material、Original Motion 使用同一 Visual Placement contract。
- rights/reuse 信息继续可读，但不参与新制作 Gate；文件、安全、完整性、grounding 与 binding Gate 保持严格。
- partial success 必须保存；一个画面不确定不能抹掉其他已经可靠对齐的画面。
- 所有 canonical 工件不可覆盖、带输入 digest，并能由 validator 重新推导关键结论。

## 2. 方案选择

### 2.1 采用的方案：确定性 Core + provider/preview adapters

Core 接收规范化的 Timed Transcript，而不是任一厂商的 raw response；用版本化 normalization、序列对齐、阈值与 validator 生成 Beat/Cue/Placement timeline。预览 renderer 只消费已通过 Core 校验的 Edit Bridge Package。

该方案能诚实区分 word/token/segment 精度，支持离线对抗性评测，也能在更换转录服务或未来增加 NLE exporter 时保持 canonical alignment 不变。

### 2.2 未采用：让 LLM 直接标注时间码

LLM 难以复验重复句、漏读、即兴和 timestamp 粒度，且可能为“完整结果”猜测不存在的精度。LLM 仅可把机器已确定的 gap 转述为普通中文，不写 canonical 秒数或 Gate。

### 2.3 未采用：直接把 provider raw response 传给 renderer

该做法会把 provider 的字段、模型升级和 timestamp 语义泄漏到全部下游，无法稳定 revision，也无法用 deterministic test provider 完成离线回归。因此 raw response 只允许留在 provider 私有审计区，canonical 下游只读 Timed Transcript Artifact。

## 3. 总体架构与数据流

```text
reviewed Script ───────────────┐
approved Research ─────────────┤
reviewed Material history ─────┤
Production Plan + Motion QA ───┤
                               ▼
Clean A-roll → Media Import → Narration Media Artifact
                               │
                               ├→ lossless transcription audio derivative
                               ▼
                         Transcription Adapter
                               ▼
                      Timed Transcript Artifact
                               ▼
Script normalization ─→ Deterministic Sequence Alignment
                               ▼
                     Script Alignment Artifact
                       ├→ Beat Timeline
                       ├→ Cue Timeline
                       └→ gaps / ambiguity
                               ▼
              Material Compatibility Projection
                               +
                    existing Production Scenes
                               ▼
                    Visual Placement Planner
                               ▼
                      Edit Bridge Package
                   ├→ canonical JSON
                   ├→ readable Markdown
                   └→ NLE-neutral CSV
                               ▼
                    Aligned Preview Adapter
                               ▼
                    ALIGNED_PREVIEW.mp4
                               ▼
                  Alignment + Edit Bridge QA
```

根绑定顺序固定为：Media → Transcript → Alignment → Edit Bridge → Preview/QA。任一上游 SHA、revision 或 digest 变化，下游旧工件保留作历史，但重新验证时必须失效。

## 4. 文件与模块边界

实现阶段按以下职责拆分，避免形成一个巨大 workflow 文件：

| 模块 | 唯一职责 |
|---|---|
| `narration_schema.py` | Narration Media、Extracted Audio、Timed Transcript 严格 schema |
| `narration_media.py` | 安全导入、safe filename、SHA、ffprobe、音轨派生 |
| `audio_timestamp_mapping.py` | container/stream PTS、media presentation 与 extracted-audio 时间映射及重验 |
| `narration_storage.py` | 媒体与 transcript 不可覆盖存储 |
| `transcription/base.py` | provider-neutral 输入输出协议 |
| `transcription/deterministic.py` | 离线测试 provider |
| `transcription/openai.py` | 真实 provider adapter；只在官方文档核对后实现 |
| `text_normalization.py` | 可逆 span map 与中英文确定性 tokenization |
| `sequence_alignment.py` | provider-neutral 动态规划、候选与歧义检测 |
| `alignment_schema.py` | Profile、Beat/Cue timeline、gap、Alignment Artifact schema |
| `alignment_profile.py` | 版本化阈值与评分配置加载 |
| `alignment_builder.py` | Script/Transcript → Alignment Artifact |
| `alignment_validation.py` | 输入绑定、时间单调、阈值与状态重推导 |
| `alignment_storage.py` | Alignment revisions 不可覆盖存储 |
| `material_bridge.py` | 历史 Material 的非版权制作投影，不修改原包 |
| `edit_bridge_schema.py` | Visual Placement、conflict、package、QA schema |
| `edit_bridge_planner.py` | Beat/Cue/Scene → IN/OUT/duration/layout |
| `rough_cut_profile.py` | still exposure、Preview fps 与 frame rounding 的版本化策略 |
| `edit_bridge_validation.py` | placement、asset、binding、conflict 重推导 |
| `edit_bridge_storage.py` | JSON/Markdown/CSV/Preview revisions 不可覆盖保存 |
| `aligned_preview/base.py` | renderer-neutral preview 协议 |
| `aligned_preview/remotion.py` | 1920×1080、30fps 粗剪 composition adapter |
| `edit_bridge_qa.py` | ffprobe、SHA、preview 与 package Gate |
| `edit_bridge_renderer.py` | 普通中文摘要、Markdown 和 CSV reading view |
| `edit_bridge_workflow.py` | 只负责编排上述模块，不拥有算法或 Gate |

Runtime 根目录为 `narration_media/`、`alignment_packages/`、`edit_bridge_packages/`、`edit_bridge_assets/`、`edit_bridge_projects/`，全部 gitignored，并各保留 `.gitkeep`。现有 `production_*` 与 `material_*` 历史目录保持不变。

## 5. Clean A-roll 输入契约

### 5.1 正式路径

默认输入是 MP4、MOV 或 M4V 真人视频。导入前执行 basename 清理、扩展名 allowlist、regular-file 检查、byte size、SHA-256 与 ffprobe。正式视频必须同时含有效 video stream 与 audio stream；无 audio stream 时媒体可登记审计记录，但 Alignment Gate 为 `fail`，普通用户只看到“这个视频没有可用于对齐的声音”。

M4A、MP3、WAV、AAC、FLAC 是兼容输入。它们可以完成 transcript、alignment 和 marker package，但因为没有真人画面底轨，不生成完整 Aligned Preview；Edit Bridge 保留有效结果并以 `warnings` 暴露 `clean_aroll_video_missing`。

### 5.2 Canonical timeline

canonical A-roll timeline 是 Clean A-roll 按 container edit list 与 stream timestamp 实际播放后的 **media presentation timeline**。其原点是播放器呈现的 0 秒，终点是确定性 probe 得到的 presentation end；它不等同于 container 原始 PTS、任一 stream 的 start PTS，也不直接等同于 ffprobe format duration。原始文件只读复制后不做内容 trim、speed change、silence removal、pause tightening、重采样替换或覆盖。输出预览可以重新编码，但不得改变 media presentation timeline 上的内容顺序和总时长。

三类时间必须分开记录：

- `container_stream_time`：文件中按各自 time base 表示的原始 packet/frame PTS/DTS，可为非零或负值；
- `media_presentation_time`：应用 container edit list、stream start、discard/skip samples 等播放语义后，以 Clean A-roll 呈现起点为 0 的 canonical 时间；
- `extracted_audio_time`：派生 PCM/WAV 自身从 0 开始的 sample 时间，只供 transcription provider 使用。

Transcript provider 返回的是 extracted-audio timeline。进入 Alignment 前必须通过版本化 Timestamp Mapping 转换到 media presentation timeline；不能假设两个原点恒等，也不能用 transcript 文本反推 offset。

## 6. Narration Media Artifact

`artifact_version = narration-media/1`，字段至少包括：

- `media_id`、`revision`、`previous_revision`、`imported_at`；
- `media_kind = video | audio`；
- `safe_original_filename`、`immutable_local_path`；
- `sha256`、`byte_size`、`container`；
- `presentation_duration_seconds`、`format_duration_seconds`、`format_start_time_seconds`；
- `video_stream`：presence、codec、width、height、nominal/average fps、VFR signal、time_base、start_pts/start_time、duration_ts/duration；
- `audio_stream`：presence、codec、sample_rate、channels、channel_layout、time_base、start_pts/start_time、duration_ts/duration、codec frame samples、initial/trailing padding 与 skip/discard side data；
- `presentation_evidence`：edit-list/packet/frame probe 摘要、presentation origin/end 与证据 digest；
- `probe_tool`、`probe_version`、`probe_digest`；
- `artifact_digest`。

字段由 importer 和 ffprobe 生成，调用方不能提供 media identity、SHA、duration 或 stream 结论。safe filename 只保留清理后的 basename，不允许绝对路径、父目录或控制字符。Artifact 对外 Markdown 不显示本机绝对路径。

新 A-roll 只要 SHA 或 presentation duration 不同，就建立新 `media_id`；即使文件名相同也不继承任何旧 timecode。VFR 只影响画面采样，不改变 decimal-seconds canonical timeline。

## 7. 视频音轨解码与 Extracted Audio Artifact

Speech-to-Text 使用从 immutable media 派生的 lossless transcription audio。派生规则固定为 `audio-extraction-profile/1`：

1. 选择 ffprobe 登记的第一条 canonical audio stream；
2. 按 container presentation semantics 解码完整可呈现采样顺序，不做降噪、响度归一、silence trim、speed change 或内容编辑；
3. 使用 lossless WAV/PCM；采样率与声道按 provider 可接受范围做一次确定性转换，并记录输入/输出参数；
4. AAC encoder priming 使用 codec/packet 的 skip-samples 或 edit-list 证据排除，不把 priming 当正文；trailing padding 使用 discard/padding 证据排除，不把 padding 当可转录时长；
5. edit list 明确排除的 pre-roll/negative PTS 不进入 derivative；仍在 presentation timeline 内的负原始 PTS 先按 presentation origin 归一，再计算映射；edit list 或 timestamp 在已呈现音轨中形成的内部 gap 必须解码为等长静音保留，不能把 gap 两侧语音拼接；
6. audio presentation 晚于 media presentation 0 时，不强制补静音：derivative 从首个可呈现音频 sample 开始，正 offset 写入 Mapping；若 extraction profile 明确补前导静音，则该处理也必须进入证据和 Mapping，不能隐式完成；
7. 不为了凑齐 container duration 补末尾静音或裁掉可听内容；derivative 只覆盖真实 audio presentation interval；
8. 记录 sample count、首末 source PTS、applied edit/skip/discard、resampler delay、输入/输出 time base 和完整 extraction 参数摘要。

新增不可覆盖的 `audio-timestamp-mapping/1`，其 canonical 方程是：

```text
media_presentation_seconds = extracted_audio_seconds * scale + offset_seconds
```

首版 `scale` 必须是精确有理数 `scale_numerator/scale_denominator = 1/1`；非 1 表示发生 time-stretch，直接 fail。`offset_seconds` 可以非零，但只能由首个写入 derivative 的 decoded sample 的 presentation PTS 减去 media presentation origin 确定。Mapping 至少记录 media/audio IDs 与 digests、source stream index/time base、presentation origin、first/last included source PTS、first/last extracted sample index、scale、offset、mapped start/end、rounding mode、evidence digest 和 mapping digest。模型、provider、transcript 文本和人工输入均不能决定这些字段。

validator 使用同一 probe 与 extraction profile 重新计算 Mapping，并验证：

- mapped start/end 与 source audio presentation interval 一致；
- `mapped_end - mapped_start` 与 `sample_count / output_sample_rate * scale` 一致；
- 容差 `mapping_tolerance_seconds` 确定性取 `max(1/output_sample_rate, source_codec_frame_samples/source_sample_rate, source_stream_time_base_tick)`；未知 codec frame size 时该项为 0，不加入猜测常数；
- mapped Transcript boundary 最终必须落在 `[0, media presentation duration]`，越界不得 clamp 后冒充正确。

正常的 AAC priming/padding、edit list、非零/负 PTS、VFR 或 container/audio duration 微差只要能由证据与 Mapping 解释，就不能因为 offset 非零而失败。证据缺失、Mapping 无法重算、scale 非 1、或差异超过上述动态容差才 fail closed。

`extracted-audio/1` 记录 media ID/SHA、音轨索引、文件 SHA/size、codec/sample rate/channels/sample count/duration、extraction profile/version、ffmpeg version、命令参数摘要、timestamp mapping ID/digest 和 artifact digest。原视频、derivative 与 Mapping 都不可覆盖。

## 8. Timed Transcript Artifact

`artifact_version = timed-transcript/1`，字段至少包括：

- `transcript_id`、`revision`、`created_at`；
- `narration_media_id`、`narration_media_sha256`、`extracted_audio_digest`、`timestamp_mapping_id/digest`；
- `provider`、`provider_model`、`provider_model_version`、`provider_request_id`；
- `language`、`timestamp_granularity = word | token | segment`；
- `timed_units[]`：`unit_id`、`order`、provider 原始 `extracted_start_seconds/extracted_end_seconds`、Mapping 后的 canonical `media_start_seconds/media_end_seconds`、`spoken_text`、可空的 `provider_confidence`；
- `provider_metadata_digest`、`transcript_digest`。

Timed units 必须非空、按 order 连续；extracted boundary 必须位于 derivative sample interval，media boundary 必须由绑定 Mapping 逐项重算且位于 Clean A-roll presentation duration 内，两套 start/end 都必须单调不倒退。允许相邻 unit 接触；provider 明确返回的重叠必须保留并导致 transcript validation fail，而不是排序掩盖。

segment timestamp 只表示整个 segment 的真实边界。一个 segment 内拆出的匹配 token 全部继承同一 `[start,end]` 和 `segment` source；系统禁止在内部线性插值词级毫秒数。

## 9. Transcription Provider 边界

协议固定为：

```text
TranscriptionProvider.transcribe(
  extracted_audio_artifact,
  language,
  configured_model
) -> ProviderTranscript
```

adapter 负责把 provider raw response 转成 `ProviderTranscript`；Core 再生成严格 Timed Transcript Artifact。adapter 不得写 media binding、canonical confidence、alignment status 或 Gate。

必须提供两类 adapter：

- `deterministic`：读取固定 timed units，供 unit test、错误注入和 adversarial eval 离线运行；
- 真实 Speech-to-Text adapter：模型名从配置读取，Artifact 保存实际 provider/model/version。

若实现 OpenAI adapter，实现当日必须查阅 OpenAI 官方 Speech-to-Text 与 SDK 文档，按官方支持的 timestamp granularity 和 response schema 编码；不从旧模型名称或参数记忆推断。provider 若只给 segment timestamp，系统自动降级为 coarse，不通过客户端计算伪造 word timestamp。

## 10. 中文与混合文本 Normalization

Normalization 只用于匹配，不生成新 Script。每个 normalized token 保存：

- `token_id`、`normalized_text`、`match_keys[]`；
- `original_start_char`、`original_end_char`（右开区间）；
- `source_unit_id`（Transcript token 才有）；
- timestamp boundary 与 granularity（Transcript token 才有）。

`normalization-profile/1` 的确定性顺序为：

1. Unicode NFKC，把全角拉丁字母、数字和兼容字符统一为半角比较形式；
2. 英文使用 Unicode casefold；
3. 中文、英文标点和空白不产生匹配 token，但原 char span 不删除；
4. 普通汉字逐字成为 token，连续英文字母成为一个 token；
5. 连续阿拉伯数字、小数点和百分号成为 numeric token；
6. 只有完整匹配严格中文数字语法的连续片段才增加 Arabic numeric alias；无法完整解析的“一、两”等字符保持普通汉字，不猜数值；
7. 年月日、百分之、负号和小数的数字语法生成结构化 match key，不改变原文；
8. 中英文混排按字符边界稳定切分。

标点与空格差异因此不会降低匹配；`３` 与 `3`、英文大小写、可严格解析的“三十”与 `30` 可以匹配。任一 token 都能回查 reviewed Script 原始 char span，renderer 和报告继续显示原文。

## 11. Deterministic Alignment Algorithm

`alignment-algorithm/1` 分四步：

### 11.1 全文单调序列对齐

对 Script tokens 与 Transcript tokens 执行全局动态规划，允许 substitution、Script deletion 和 Transcript insertion。得分由 Alignment Profile 固定：primary match 高于 numeric alias match；substitution、deletion、insertion 为不同负分。相同输入、Profile 与 Transcript 必须得到相同 score matrix digest 和候选集合。

canonical path 的稳定 tie-break 顺序固定为：primary match → numeric alias match → transcript insertion → script deletion → substitution → 较早 transcript index。tie-break 只用于生成可重复路径，不会把真实歧义隐藏为高置信度。Artifact 记录 token streams、Profile、score dimensions、canonical operation trace 和候选摘要的 `alignment_trace_digest`；validator 使用同一输入重算该 digest，不保存或信任调用方提供的 score matrix。

### 11.2 最优路径歧义检测

使用 forward/backward optimal scores 计算每个 Script span 能落入的全部等价或近等价 Transcript windows。候选差值固定为 `(best_score - candidate_score) / max(1, theoretical_primary_match_score_for_span)`；若两个不重叠候选的差值不超过 Profile 的 `0.08` ambiguity margin，记录 `ambiguous_match`。canonical window 可以保留作诊断，但 Beat/Cue 不得成为 `aligned`。

### 11.3 Beat 独立候选与顺序检查

每个稳定 Beat 还在完整 Transcript 上执行受限局部比对，用于发现全文单调路径掩盖的重排。高分 Beat 候选若相对 Script Beat 顺序发生反转，相关 Beat 标记 `beat_order_changed`，不把其中 timestamp 强行写入正常 timeline。

### 11.4 Gap 与偏差

连续 Script deletion 形成 `omitted_script_span`；连续 Transcript insertion 形成 `ad_lib_transcript_span`；重复候选形成 `repeated_or_ambiguous_span`。Gap 保存 char/unit span、候选真实时间边界和机器原因。LLM 可把原因改写为易读说明，但不能改变这些字段。

## 12. Alignment Profile、评分与状态

`alignment-profile/1` 固定初始参数：

| 参数 | 值 |
|---|---:|
| primary token match | +4.0 |
| numeric alias match | +3.0 |
| substitution | -2.5 |
| Script deletion | -2.0 |
| Transcript insertion | -1.5 |
| ambiguity normalized margin | 0.08 |
| aligned token coverage floor | 0.85 |
| aligned similarity floor | 0.88 |
| needs-review coverage floor | 0.55 |
| needs-review similarity floor | 0.65 |
| long gap threshold | 8 normalized tokens |
| timestamp epsilon | 0.001 seconds |

Beat `match_score` 是对齐得分除以该 Beat 全部 primary match 的理论最大值后限制到 `[0,1]`；`token_coverage` 是有 Transcript 对应的 Script tokens 比例；`similarity` 是 matches 减 substitutions 后的归一化值。provider confidence 只原样记录，不进入首版 canonical status，避免不同 provider 的不可比尺度污染 Gate。

状态重推导规则：

- `aligned`：coverage ≥ 0.85、similarity ≥ 0.88、无 ambiguity、无长 gap、无顺序异常，且 granularity 是 word/token；
- `needs_review`：达到两项 needs-review floor，但存在小漏读、局部即兴、歧义、长 gap，或 timestamp granularity 只有 segment；
- `unmatched`：任一 needs-review floor 未达到，或没有可用 timestamp window。

`confidence = high | medium | low | none` 由同一字段重推导：aligned 为 high；无歧义且超过 needs-review floor 为 medium；其余 needs_review 为 low；unmatched 为 none。Profile digest 写入 Alignment Artifact。上述阈值必须通过本文 adversarial suite 校准；校准允许发布新的 Profile contract，不允许原地修改旧 Profile。

## 13. Script Alignment Artifact 与 Beat Timeline

`artifact_version = script-alignment/1`，根字段绑定：alignment ID/revision、Script ID/revision/content digest、Media ID/SHA/presentation duration、Extracted Audio Timestamp Mapping ID/digest、Transcript ID/digest、normalization profile、alignment profile/digest、algorithm version、alignment trace digest、created_at、gaps、artifact digest。

每个 `beat_timeline[]` 至少包含：

- `beat_id` 与 Script 原始 `intended_char_span`；
- `matched_transcript_unit_span`；
- 可空 `actual_start_seconds`、`actual_end_seconds`；
- `timestamp_source` 与 `timestamp_granularity`；
- `match_score`、`token_coverage`、`similarity`；
- `confidence`、`alignment_status`；
- `deviation_codes[]`、`deviation_summary`；
- `candidate_windows[]`，只保存 provider 真实边界。

aligned Beat 的时间来自首末已匹配 timed unit 边界。needs_review 可以保留真实候选 window，但 canonical start/end 只有候选唯一时才存在；unmatched 的 canonical start/end 必须为空。Beat 顺序、时间单调和状态由 validator 重新计算。

## 14. Cue Timeline 与 anchor 局部对齐

Cue 继续使用 Material Package 的 `cue_id`、`beat_id` 和 `placement_anchor`。流程固定为：

1. 先验证 anchor 在绑定 Beat 的 reviewed spoken text 中有唯一 Script char span；
2. 用 Beat 的 Script-token → Transcript-unit map 将 anchor tokens 映射到真实 timed units；
3. 在 Beat window 内计算全部局部候选；
4. 唯一且达到 aligned floor 时，Cue IN 为 anchor 首个匹配 unit 的真实 start；
5. 多个同等候选、Beat 非 aligned、anchor coverage 不足或 segment-only 时，Cue 分别成为 needs_review/coarse/unplaced，不猜选。

Cue 的 intended semantic span 从本 anchor 的 Script char start 延伸到同 Beat 下一个 Cue anchor 的 char start；若不存在下一个 Cue，则延伸到 Beat 末尾。actual semantic end 来自该 span 最后匹配 unit 的 end。Cue timeline 保存 anchor span、semantic span、候选、actual start/end、status、granularity 和 confidence。

同一 Beat 内重复 anchor 即使全文路径选择了一个位置，也必须标记 `ambiguous_anchor`。Beat needs_review 不会被 Cue 局部高分自动升级。

## 15. Material Compatibility Projection 与 Rights/Reuse

新流程不修改 V0.5/V0.6 artifact，也不删除其中 rights、reuse、reference_only 或 permission_required。它创建只供 Edit Bridge 使用的 `material-production-view/1`。专用 compatibility loader 先按历史 schema 验证原 Artifact digest、provenance 和 review linkage，再跳过旧 status 的“可进入 V0.6 Production”判断，确定性重推导以下制作视图：

- 重新读取 immutable Material input、inspection、review 与文件记录；
- 把 `rights_reuse` check、`permission_needed` issue 和仅由 rights 产生的 eligibility 当作非制作信息；
- 继续阻断 fabricated source、claim mismatch、misleading crop、wrong identity、unsafe MIME/path、缺失文件、SHA/size 不符、codec 不兼容、Research grounding 与 caption grounding 问题；
- 历史 package 若唯一 blocker 是 rights/reuse，可以生成 production view；存在任何非 rights blocker 时仍拒绝相应素材；
- URL 或 reference 不是文件。没有真实本地文件时状态只能是 `missing_asset`，用户提示固定为“素材文件尚未取得”；
- 不绕过 DRM、登录、付费墙或技术访问控制。

该 projection 只改变新制作资格的推导方式，不把历史 `reference_only` 改写为 `ready_to_use`，也不声称系统完成版权审批。

## 16. 统一 Visual Placement Model

`visual-placement/1` 对四种 source kind 使用同一 schema：

- `source_kind = clean_aroll | real_image | real_video | original_motion`；
- `placement_id`、`track_order`；
- `beat_id`、`cue_id`、`scene_id`（A-roll base 为空）；
- `material_id`、`visual_id`、`motion_asset_id`、`source_asset_path`、`source_sha256`；
- canonical `semantic_in_seconds`、`semantic_out_seconds`、`semantic_duration_seconds`，decimal seconds 是唯一机器真值；
- canonical `in_timecode`、`out_timecode`，由 decimal seconds 确定性格式化为与帧率无关的 `HH:MM:SS.mmm`；
- `source_clip_in_seconds`、`source_clip_out_seconds`、`source_duration_seconds`；
- `natural_duration_seconds`（静态图为空）、`target_duration_seconds`（等于 semantic duration）、`duration_source`；
- `duration_status = within_policy | long_still_warning | asset_duration_warning | not_applicable`；
- `anchor`、`timestamp_granularity`；
- `layout_mode`、`layout_source`、`audio_policy`；
- `placement_status`、`confidence`、`notes[]`；
- `timing_conflict_ids[]` 与 `timing_status = clear | warning | blocking`；
- Preview 派生字段 `preview_effective_in_seconds/out_seconds`、`preview_in_frame/out_frame`、`preview_in_frame_timecode/out_frame_timecode` 与 `preview_adjustment_id`。

`placement_status` enum 固定为：

- `ready`：narration placement 唯一且时间、身份、素材都可复验；非 blocking timing warning 不会取消 ready；
- `coarse`：只有 provider segment boundary，不伪装精细时间，首版 Preview 不覆盖；
- `needs_review`：anchor/Beat/重复候选/选择冲突使 narration placement 或应显示对象需要人工判断，首版 Preview 不覆盖；
- `unplaced`：没有 canonical timestamp，IN/OUT/duration 必须为空；
- `missing_asset`：narration placement 可保留，但真实文件不存在，不进入 Preview；
- `clip_selection_needed`：真实视频插入位置已知，但 source clip IN/OUT 为空，不进入 Preview；
- `rejected`：文件完整性、grounding 或 renderer compatibility 失败。

Clean A-roll 自身是 `VP0000`：覆盖 `[0, media presentation duration]`、`track_order=0`、`ready`、`full_screen_aroll`。所有 overlay placement 使用现有 Scene identity；不存在合适画面时不创建假 overlay，A-roll 自然持续显示。

Placement uncertainty 与 timing conflict 是正交维度：前者回答“画面是否被唯一、可靠地放到 narration timeline”，后者回答“已经可靠放置的画面自然时长与其他窗口怎样冲突”。Motion duration mismatch、source clip 长短差异或两个已可靠窗口 overlap 只产生 `timing_status=warning`，placement 仍可为 ready 并进入 Rough Cut；same-start 无法确定显示对象、anchor ambiguity 或无唯一 window 才使 placement 为 needs_review/unplaced，或产生 blocking conflict。

## 17. Real Image 与 Screenshot

图片、照片、网页截图、文档截图、产品界面和已安全取得的 PDF 页面图像统一为 `real_image`。进入 ready 的必要条件是：

- Material/Cue/Beat/Scene binding 存在；
- local regular file 存在且位于允许根目录；
- SHA、size、MIME magic 与登记一致；
- renderer 能解码 PNG/JPEG/WebP 或配置中明确允许的静态格式；
- caption/Display Text/Research grounding 合法；
- capture 页面与区域元数据在需要时完整。

默认 layout 为 `full_screen_broll`，使用 contain 适配和中性背景，避免自动裁掉上下文；真人原音继续。第一版不强制 pan/zoom。若既有 reviewed Scene 已包含可验证的轻量 motion intent，可以执行不改变内容的中心缩放，但不能裁切掉证明语境。

图片的 canonical semantic OUT 来自真实 Cue semantic window，不使用固定五秒规则。其 Preview exposure 还必须经过第 20.4 节的长静态画面 safeguard，不能无提示覆盖整个长 Beat。

## 18. Real Video B-roll

真实视频同时保存两条时间轴：

- narration timeline：应该覆盖 Clean A-roll 的 IN/OUT；
- source timeline：B-roll 文件内部的 clip IN/OUT。

文件先执行 ffprobe、SHA、size、codec、duration 与 path safety。Material 已有明确、合法且未越界的 clip/capture range 时直接继承。没有内部 range 时保留 narration IN/OUT，但 placement 为 `clip_selection_needed`，source clip IN/OUT 为空，Preview 继续显示 A-roll。

ready real video 默认 `full_screen_broll`、`audio_policy=mute_source_keep_aroll`。不得把 B-roll 原音变成主音轨，不做现场声 mixing，也不自动选择“最精彩片段”。source clip range 小于 narration semantic window 时记录 timing conflict，Preview 只使用真实可用部分并自动回到 A-roll；不循环或拉伸。

## 19. Original Motion

Original Motion 只接受现有 Motion Asset Manifest 中 `qa_status=ready` 且可由 Production QA、Production Plan digest、scene ID、cue ID、beat ID、文件 size/SHA、width/height/fps 重新验证的资产。

Edit Bridge 复用原 `scene_id`、scene payload、designed duration 和 binding，不重新解释 Research，不重新生成 Motion。历史 Scene 若原先因 rights-only 降级成 `aroll_placeholder`，material production projection 只能把已取得且通过非版权 Gate 的真实文件绑定回这个同一 `scene_id`，不能新建替代 Scene。只有 Production Plan 或 Motion Manifest digest 变化时才要求新 Edit Bridge；Alignment 本身不会触发 Motion 重渲染。

默认 layout 为 `full_screen_visual`，Motion 原音保持静音，Clean A-roll 原音继续。

## 20. IN、OUT 与 Duration 推导

### 20.1 IN

ready placement 的 `semantic_in_seconds` 等于 Cue placement anchor 首个匹配 timed unit 经 Timestamp Mapping 转换后的真实 media presentation start。只允许映射到 provider 返回的 word/token boundary。segment-only 使用 segment media start 并标 coarse，不进入首版 Preview。unplaced 不得携带 IN。

### 20.2 Semantic OUT

`semantic_out_seconds` 等于 Cue intended semantic span 最后一个唯一匹配 timed unit 经 Mapping 转换后的 media presentation end；无法唯一映射时为空。图片与截图的 canonical OUT 使用该值。

### 20.3 Asset-aware OUT

- image/screenshot：`OUT = semantic OUT`；
- real video：有 source clip range 时，canonical target OUT 仍为 semantic OUT，同时保存 source available duration；不足或超出形成 conflict；
- original motion：canonical target OUT 为 semantic OUT，同时保存 designed OUT=`IN + designed_duration`；二者不一致形成 conflict；
- A-roll：`OUT = media presentation duration`。

`semantic_duration_seconds = semantic_out_seconds - semantic_in_seconds`，不接受模型或 payload 自报。下一 overlay 的 IN 只用于 overlap 检测和 Preview effective OUT，不静默改写 canonical OUT。

### 20.4 Canonical timecode、Preview frame 与长 still safeguard

canonical machine time 使用 media presentation timeline 的 decimal seconds；canonical human timecode 使用 `HH:MM:SS.mmm`，以毫秒 half-up 格式化并允许超过 24 小时，不包含 frame 编号，也不依赖 Clean A-roll 是 25、29.97、30、50/60fps 或 VFR。CSV 优先输出 seconds 与该毫秒 timecode。

30fps 只属于 `aligned-preview-profile/1` 的派生映射。Preview 使用 `preview_in_frame = ceil(preview_effective_in_seconds * 30)`、`preview_out_frame = ceil(preview_effective_out_seconds * 30)`，OUT 为 exclusive frame；这样 overlay 不会早于 canonical IN 出现，也不会在 canonical effective OUT 之前消失。`preview_in_frame_timecode/out_frame_timecode` 必须带 Preview 前缀并采用 `HH:MM:SS:FF`。frame snap 差值写入 preview adjustment，不反写 Alignment、semantic seconds 或 canonical timecode。

静态图片/截图另应用 `rough-cut-duration-profile/1`。Profile 首版不新增拍脑袋常数，而是继承已在 Material Profile 0.5 中版本化的 `default_cue_duration_seconds = 7`，并记录来源 Profile/digest。规则为：

- `canonical semantic OUT` 始终保留，不被 exposure cap 覆盖；
- 若 still semantic duration ≤ 7 秒，Preview effective OUT 等于 semantic OUT；
- 若 still semantic duration > 7 秒且没有结构化 user duration override，placement 仍为 ready、`duration_status=long_still_warning`，生成 `still_exposure_capped` warning 与 preview adjustment，`preview_effective_out_seconds = semantic_in_seconds + 7`；
- 若更早出现下一 ready overlay，仍按 overlap policy 取更早 effective OUT；
- 用户说“这张截图时间太长/短”并唯一定位后，建立新的 Bridge revision，保存 user adjustment provenance；canonical semantic window 不变。

7 秒只是一版 Rough Cut exposure policy，不是事实语义时长。它必须在长 Beat adversarial case 与真实 E2E 中验证“不会明显拖沓且不会过短到不可读”；若校准需要变化，只能发布新的 Rough Cut Duration Profile，不能修改旧 Bridge 的 policy digest。

## 21. Layout / Compositing Modes

enum 固定为：

- `full_screen_aroll`
- `full_screen_broll`
- `full_screen_visual`
- `picture_in_picture`
- `split_screen`
- `side_card`

默认映射：Clean A-roll → full_screen_aroll；真实图片/截图/视频 → full_screen_broll；Timeline/Diagram/Comparison/Data Motion → full_screen_visual。

首版自动 planner 只产生三个默认模式。picture-in-picture、split-screen、side-card 只能来自结构化用户 revision 或未来版本化 Editing Style Profile，不能从自由文本 `layout_intent` 猜测。用户说“这里一直保留真人”等自然语言时，resolver 先按可读 caption、filename、Beat 文本和时间邻域定位 placement；匹配唯一后建立新 Edit Bridge revision。歧义时只问用户指出哪一幅可读画面，不要求 Scene ID 或精确秒数。

## 22. Timing Conflict 与 Preview-only Policy

`timing-conflict/1` 至少包含 conflict ID/type、相关 placement IDs、canonical windows、asset natural duration、`conflict_class = timing_warning | selection_blocker`、severity、human summary、preview policy 与 `resolution_status = unresolved | preview_adjusted | user_resolved`。

类型包括：

- `motion_longer_than_semantic_window`
- `motion_shorter_than_semantic_window`
- `source_clip_shorter_than_semantic_window`
- `source_clip_longer_than_semantic_window`
- `visual_overlap`
- `same_start_selection_ambiguity`
- `out_of_media_bounds`

前五项 duration/overlap conflict 在相关 placement 的 canonical IN/OUT 都可靠时属于 `timing_warning`：placement 保持 ready，Package Gate 为 warnings，并执行可审计的 Preview policy。`same_start_selection_ambiguity` 在系统无法确定应显示哪个对象时属于 `selection_blocker`：相关 placement 必须 needs_review 且不进入 Preview。`out_of_media_bounds` 表示 canonical mapping 或输入非法，不允许用 clamp 掩盖，相关 placement rejected，根源是 Mapping 时可升级 Gate fail。

Core 不加速、拉伸、循环、移动 timestamp、覆盖源文件或静默改写 canonical OUT。Aligned Preview 的确定性临时策略为：

1. 只渲染 `ready` placement；
2. 只对已经验证在 `[0, media presentation duration]` 内的 seconds 做 30fps frame 派生；不得先 clamp 越界时间再假装合法；
3. Motion 或视频长于 semantic window时仅在 Preview effective OUT 裁掉尾部，源 asset 与 canonical target/natural windows 保留；
4. asset 短于 semantic window 时播放到自然结束，余下显示 A-roll；
5. 后开始的 ready placement 在其 IN 接管上层画面，较早 placement 的 Preview effective OUT 临时缩到该 IN；
6. 两个 placement 只是 30fps frame snap 后同 frame、但 canonical decimal IN 不同，仍按更早 canonical IN 显示并记录 frame collision adjustment；若 canonical IN 完全相同且没有结构化 track priority，生成 `same_start_selection_ambiguity`，两者均 needs_review，不使用内部 ID 顺序冒充编辑决定；
7. coarse、needs_review、unplaced、missing_asset、clip_selection_needed、rejected 均不覆盖 A-roll。

每项临时变化写 `preview_adjustment/1`；QA 不得把 adjustment 表述为最终剪辑决定。

## 23. Edit Bridge Package

`artifact_version = edit-bridge/1`，严格绑定：

- bridge ID/revision/previous revision/created_at；
- Narration Media ID/SHA/presentation duration/digest；
- Extracted Audio digest；
- Extracted Audio Timestamp Mapping ID/digest；
- Transcript ID/digest/provider/model/granularity；
- Script ID/revision/content digest；
- approved Research ID/revision/digest；
- Material Package ID/revision/digest 与 production-view digest；
- Production Plan ID/revision/digest；
- Motion Manifest ID/digest 与 Production QA digest；
- Alignment ID/revision/digest/Profile digest、Rough Cut Duration Profile/digest 与 Aligned Preview Profile/digest；
- Beat Timeline、Cue Timeline、Visual Placements；
- real image bindings、real video bindings、motion bindings；
- missing asset markers、clip selection markers；
- timing conflicts、alignment gaps、preview adjustments；
- QA state 与 package digest。

输出固定为：

1. `edit-bridge-rNNNN.json`：唯一 canonical machine interface；
2. `edit-bridge-rNNNN.md`：普通中文摘要，隐藏绝对路径和内部矩阵；
3. `edit-bridge-markers-rNNNN.csv`：UTF-8 with BOM、RFC 4180 quoting、NLE-neutral。

CSV 列固定为：canonical IN seconds、canonical OUT seconds、canonical IN `HH:MM:SS.mmm`、canonical OUT `HH:MM:SS.mmm`、semantic duration、natural duration、target duration、Preview effective IN/OUT seconds、Preview IN/OUT frame、Preview IN/OUT frame timecode、Beat、Cue、Scene、visual role、source kind、asset type、safe filename/motion asset、layout mode、anchor、placement status、timing status、duration status、confidence、notes。Preview 派生列必须含 `Preview` 前缀。CSV 不声称原生兼容 Premiere、DaVinci Resolve 或 Final Cut；特定 exporter 不属于本阶段。

## 24. Aligned Preview Composition

首版 adapter 复用 Remotion/现有 Production Profile 的 1920×1080、30fps 环境，但消费 Edit Bridge placement，而不是重新规划 Research 或 Scene。

Composition 规则：

- Clean A-roll 视频完整铺设为 layer 0；比例不符时 contain + 黑色/中性背景，不做时间裁剪；
- ready image/screenshot 在 effective IN/OUT 覆盖，结束后自动露出 A-roll；
- ready real video 按 source clip range 播放、静音，结束后自动露出 A-roll；
- ready Motion 按 effective IN/OUT 播放、静音；
- 没有 ready overlay 的区间持续显示真人；
- 不显示 missing/coarse/unplaced 占位卡，不为了换画面插入视觉；
- 不加字幕、BGM、SFX、标题或封面。

音频采用两阶段：视觉 composition 全部静音渲染；随后把 Clean A-roll canonical audio stream 作为唯一主音轨 mux 到 Preview。若 MP4 容器不支持 source codec，只允许无剪辑、无混音的 codec 转换并记录参数；不做 trim、normalize 或 time stretch。最终 duration 必须与 Clean A-roll 相差不超过一帧。

Preview 输出 `ALIGNED_PREVIEW-rNNNN.mp4`，H.264、1920×1080、30fps。Manifest 记录 Bridge digest、renderer/profile、文件 path、size、SHA、codec、duration、dimensions、fps 和命令摘要。

## 25. Alignment + Edit Bridge QA / Gate

QA 分为 root、transcript、alignment、placement、preview 五组 typed checks，并重新读取真实文件。至少重推导：

- Clean A-roll SHA/size/presentation duration/container metadata/video/audio streams；
- Script、Research、Material、Production Plan、Motion Manifest/QA 的 exact revision 与 digest；
- Transcript → media SHA/digest binding；
- timed units timestamp 单调、范围、真实 granularity；
- container/stream PTS、media presentation timeline、extracted timeline 与 Timestamp Mapping 的 evidence/digest/scale/offset/tolerance；
- normalization/Profile/algorithm digest；
- Beat 顺序、match score、status 和 candidate ambiguity；
- Cue/anchor existence 与局部 match；
- Scene/Cue/Beat identity；
- canonical `IN < OUT <= media presentation duration`、semantic duration、`HH:MM:SS.mmm` 与 Preview-only frame conversion；
- real material file/path/MIME/codec/size/SHA/grounding；
- Motion QA-ready、scene binding 与 SHA；
- missing/unplaced 不伪装 ready，不携带虚假 canonical timestamp；
- layout/audio policy enum；
- placement status 与 timing status 正交一致性、long-still duration warning、timing conflict 与 Preview adjustment 完整性；
- Preview 存在、ffprobe、codec、1920×1080、30fps、duration、size、SHA 和 Bridge binding。

Gate 规则：

- `fail`：root binding/digest 无效、视频默认路径无 audio、Transcript timestamp 非法、Timestamp Mapping 无法由 media/extraction evidence 重算或 scale 非 1、mapped timestamp 越界、Preview 使用 tampered/unready asset、视频默认路径 Preview 缺失或关键 metadata 不符；
- `warnings`：根工件有效，但存在个别 needs_review/coarse/unplaced/missing/clip-selection、未解决 timing warning、long-still exposure cap、selection blocker，或音频兼容路径无视频 Preview；
- `pass`：全部必需 binding 与 Preview 通过，所有可用 Cue 已 ready，无未解决 warning。

单一 placement 的文件或 SHA 失败会把该 placement 标 rejected 并产生 typed issue；其他 placement、JSON/CSV 与可用 Preview 继续保存，整体通常是 warnings。若被拒素材实际进入 Preview，则升级为 fail。Gate、issue ID、scope、severity 和 status 全由代码重推导，provider、LLM 和 renderer 不得自报 pass。

## 26. Revision、不可覆盖与失效传播

目录建议：

```text
narration_media/YYYY/MM/DD/<media_id>/
  narration-media-r0001.json
  original/<safe-filename>
  extracted-audio-r0001.wav
  extracted-audio-r0001.json
  audio-timestamp-mapping-r0001.json
  timed-transcript-r0001.json

alignment_packages/YYYY/MM/DD/<script_id>/<media_id>/<alignment_id>/
  script-alignment-r0001.json
  script-alignment-r0001.md

edit_bridge_packages/YYYY/MM/DD/<script_id>/<media_id>/<bridge_id>/
  edit-bridge-r0001.json
  edit-bridge-r0001.md
  edit-bridge-markers-r0001.csv
  edit-bridge-qa-r0001.json

edit_bridge_assets/<bridge_id>/r0001/ALIGNED_PREVIEW-r0001.mp4
edit_bridge_projects/<bridge_id>/r0001/
```

任何目标已存在即拒绝写入。用户重新剪 A-roll 后，SHA/presentation duration 变化触发新 Media → Mapping → Transcript → Alignment → Bridge → Preview 链，旧 timecode 永不继承。

Script content digest、Material Package/production-view digest、Production Plan digest 或 Motion Manifest digest 变化时，旧 Bridge 验证失败并要求新 revision。仅普通中文 Markdown 变化不影响 machine digest。用户审美修改建立新的 Bridge revision，保留原 alignment 与明确的 user adjustment provenance；不会覆盖 canonical source artifacts。

## 27. Partial Success 与普通用户恢复体验

Workflow 不因局部问题丢弃可靠结果。输出摘要按可读画面名称和口播上下文组织，例如：

> 8 个画面中，7 个已经自动放好。还有 1 个画面暂时无法确定位置，因为你这一段的实际说法和正式稿差异较大。

> 这段真实视频已经知道应该出现在 4 分 12 秒附近，但还没有确定素材内部使用哪一小段。

用户只需说“这张截图时间太长”“这里一直保留真人”“关系图晚一点”。系统通过 safe filename、caption、Beat spoken text 与时间邻域解析到 placement；唯一匹配后创建 revision，歧义时展示少量可读候选。界面与 Markdown 不暴露 token matrix、Claim ID、JSON schema、traceback、ffmpeg command、本机绝对路径或要求用户选择 Scene ID。

## 28. Adversarial Eval Strategy

所有算法测试使用 deterministic provider，timestamp 与文本均为显式 fixture；真实 E2E 另用用户真正的 Clean A-roll，不能用 fixture 宣称最终完成。

| Case | 期望结果 |
|---|---|
| A 完全按稿 | 所有 Beat/Cue 高置信 aligned，ready placement |
| B 少量语气词/小口误 | insertion/substitution 被记录，整体不降级 |
| C 漏读一句 | 局部 needs_review/unmatched，后续 Beat 恢复 |
| D 重复一句 | 候选 margin 触发 ambiguous，不随便选 |
| E 大段即兴 | transcript gap，不能产生虚假 placement |
| F Beat 顺序改变 | 独立候选检测 inversion |
| G timestamp 倒退 | Transcript validation fail |
| H 错误 media SHA | Transcript binding fail |
| I Script digest 改变 | 旧 Alignment invalid |
| J Material digest 改变 | 旧 Bridge invalid |
| K Motion SHA 篡改 | placement rejected；若进入 Preview 则 Gate fail |
| L 正常 Clean MP4 | video/audio probe、transcribe、alignment 正常 |
| M 视频无 audio | Alignment fail，普通中文提示 |
| N screenshot 无 rights metadata | 文件与 grounding 合法即可制作 |
| O 历史 rights-only reference_only | projection 不因 rights 阻塞 |
| P 真实素材文件不存在 | missing_asset，不生成 ready |
| Q 图片 SHA 修改 | placement rejected |
| R 视频无 clip range | narration placement 保留，clip_selection_needed |
| S segment-only Transcript | coarse，不插值 word timestamp，不进首版 Preview |
| T Beat 内 anchor 重复 | ambiguous_anchor |
| U 标点/全半角差异 | normalization 后正常匹配 |
| V 新 A-roll revision | 全新下游链，不继承 timecode |
| W Motion 比 spoken window 长 | timing conflict + preview-only crop record |
| X 两个 visual 重叠 | conflict + 稳定 Preview policy |
| Y Image duration | 使用 semantic window，不固定五秒 |
| Z 无合适 Visual | A-roll 连续显示，无假画面 |
| AA AAC priming/padding | 由 skip/discard/edit 证据排除，Mapping 可重算，不误移正文时间 |
| AB 非零或负 audio PTS | media/extracted offset 非零但有证据时正常映射，不强制 identity |
| AC container edit list | canonical media presentation 0 与 raw stream PTS 分离，Transcript 映射正确 |
| AD 正常 duration 微差 | 在动态 codec-frame/time-base tolerance 内通过，超出则 fail |
| AE 25/29.97/VFR A-roll | canonical seconds 与 `HH:MM:SS.mmm` 不变，30fps 只作为 Preview 派生 |
| AF reliable Motion duration mismatch | placement 保持 ready，timing warning + adjustment，Gate warnings |
| AG reliable Visual overlap | 两个 placement 保持 ready，后开始者 Preview 接管并记录 adjustment |
| AH same-start selection ambiguity | placement needs_review，不按内部 ID 擅自选画面 |
| AI 单一 Image Cue 位于长 Beat | semantic OUT 保留，Preview exposure 按 Profile cap，记录 long-still warning |

额外 property tests 覆盖：相同输入输出 digest 稳定；Mapping 重算后所有 media timestamp 单调且在 presentation timeline 内；不同源 fps/VFR 不改变 canonical seconds/timecode；unplaced 无 canonical timestamp；timing warning 不降低可靠 placement；selection blocker 不进入 Preview；所有 Preview overlay 都能回链 ready placement；长 still adjustment 不改变 semantic OUT；任意单字段篡改被 validator 拒绝。

Profile 验收优先避免 false precision：Case D/E/F/S/T 出现一个被误判为 high-confidence ready 即为 calibration fail；Case A 必须全部 aligned；Case C 后续 Beat 不能连锁 unmatched。

## 29. Explicit Out of Scope

本阶段不包含：

- 自动剪口气、silence removal、pause shortening、filler-word 自动删除；
- 重录检测后的自动删除、Raw A-roll 自动 cleanup；
- TTS、voice clone、假主播；
- 字幕成片、BGM、SFX、自动音效；
- 自动标题、封面、发布或平台上传；
- 完整自动最终成片；
- Premiere、DaVinci Resolve、Final Cut 专属工程导出；
- 高级现场声 mixing；
- 自动寻找真实视频“最佳几秒”；
- 复杂 Editing Style Profile 或不可复验的导演 heuristic；
- copyright approval、reuse permission Gate、授权证明上传或用户版权确认框；
- DRM、付费墙、登录或其他技术访问控制绕过。

## 30. 2.0 A-roll Cleanup Boundary

Auto A-roll Cleanup / Pause Tightening 是未来 2.0 候选能力，必须位于本系统之前：

```text
Raw A-roll → user cleanup（当前）/ future cleanup workflow（2.0）
→ immutable Clean A-roll
→ Alignment
→ Visual Edit Bridge
```

即使 2.0 引入自动 cleanup，它也必须输出新的 immutable Clean A-roll Media Artifact；Alignment 永远只读 cleanup 后的成品，不在同一 timeline 上一边删口气一边计算 Visual timecode。

## 31. Open Design Risks 与已定应对

1. **真实 provider 的 timestamp 能力会变化。** adapter 启用时查官方文档、模型配置化、Artifact 记录实际 granularity；segment-only 自动 coarse。
2. **中文 ASR token 边界不统一。** Core 不信 provider tokenization，统一经过自己的 span-preserving normalization；不在 timed unit 内插值。
3. **长稿动态规划的内存。** algorithm/1 使用分块保存 score rows 与 forward/backward pass，输出与完整 DP 等价；性能优化不能改变 tie-break 或 digest。
4. **历史 rights 与 eligibility 耦合较深。** 使用独立 production projection，不修改旧 canonical loader；非 rights checks 必须全部重验。
5. **真实视频 clip range 经常缺失。** narration placement 和 source selection 分离，先保留前者，后者诚实标记 clip_selection_needed。
6. **Motion natural duration 与实际讲话不同。** 可靠 placement 与 timing warning 正交，使用双窗口 + preview-only adjustment，不改 Motion 文件或 canonical time。
7. **A-roll 编码、VFR、edit list 与音轨 PTS 多样。** ffprobe/ffmpeg evidence 建立 media presentation timeline 与版本化 Timestamp Mapping；正常非零 offset 不失败，无法重算或 time-stretch 才失败。Preview 30fps 不冒充 source fps。
8. **用户自然语言修改可能指向多个画面。** resolver 只在唯一匹配时自动 revision，否则给普通中文候选，不要求内部 ID。
9. **Rough Cut 容易被误认最终成片。** Artifact、文件摘要和 UI 明确标为 Aligned Preview，保留 timing conflicts 与 adjustments，不提供“发布完成”状态。
10. **长 Beat 中的单张 still 可能覆盖过久。** semantic window 保留为事实范围，Preview exposure 继承版本化 7 秒 Cue 默认并产生 warning；真实 E2E 校准只能形成新 Profile。

## 32. Design Review 验收边界

本 Design 只定义 contracts、算法、模块、Gate、失败恢复和 E2E 验收方式。本轮不创建 implementation plan，不修改 Python/renderer/Skill 行为，不运行真实 transcription 或 render，不产生产品 Release。

Design Review 通过后，下一轮才把本文拆成 TDD implementation plan。实现完成后的最终验收必须使用用户真正的 Clean A-roll、真实 Material 和现有 Motion，生成真实 `ALIGNED_PREVIEW.mp4` 并由用户观看；fixture 只证明回归，不证明产品达到 V1.0。
