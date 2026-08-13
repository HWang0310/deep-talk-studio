# Audio Alignment + Visual Edit Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将用户已经剪好口气的 immutable Clean A-roll 作为唯一时间轴，确定性对齐 reviewed Script、reviewed Material 与 QA-ready Motion，输出可复验的 Edit Bridge 和带真人原音的 Aligned Preview。

**Architecture:** 新实现保持 Python Core 拥有 schema、时间映射、alignment、placement、Gate 与 revision；Speech-to-Text 和 Remotion 只是可替换 adapter。根工件按 Media → Extracted Audio/Mapping → Transcript → Alignment → Material Projection/Bridge → Preview/QA 绑定，明确分离 container/stream timeline、media presentation timeline 与 extracted-audio timeline；所有 machine 字段由程序推导、validator 重推导，任何局部 placement 失败只隔离该画面。

**Tech Stack:** Python 3.9+ 标准库、现有 strict JSON Schema helpers、ffmpeg/ffprobe、Remotion 4.0.507 + React 19.2.3、`unittest`；OpenAI 文件转录使用 `/v1/audio/transcriptions`，真实调用只在显式 smoke/E2E Gate 运行。

## Global Constraints

- 唯一设计依据是 Design HEAD `993daf5a89862a827d72d3949c8c05a1b93a391b` 的 `docs/superpowers/specs/2026-08-13-audio-alignment-edit-bridge-design.md`。
- Clean A-roll 是只读 canonical media presentation timeline；V1.0 不做 silence removal、pause shortening、filler-word removal、重录删除或任何自动 A-roll cleanup。
- canonical machine time 只用 decimal seconds；canonical readable timecode 只用可超过 24 小时的 `HH:MM:SS.mmm`；30fps frame/timecode 只属于 Preview 派生。
- Script Beat → Material Cue → Production Scene 是唯一身份链；不得生成第二套 Beat/Cue/Scene identity。
- provider、模型、renderer 和调用方都不能自报 SHA、digest、status、confidence、Gate 或 canonical timestamp；builder 推导，validator 独立重推导。
- segment-only timestamp 只能形成 coarse placement，不做 word/token 线性插值，也不进入首版 Preview。
- rights/reuse 继续保留作历史信息，但不参与新制作 Gate；path、MIME/codec、SHA、grounding、binding、integrity 与 QA 仍 fail closed。
- `placement_status` 与 `timing_status` 正交：可靠 placement 可带 timing warning 进入 Preview；selection ambiguity 不自动 Preview。
- 真实视频没有 source clip range 时只能 `clip_selection_needed`，不得自动猜“最佳几秒”；ready B-roll 静音、不 loop、不 stretch，结束后回 A-roll。
- still exposure 首版继承 Material Profile 0.5 的 `default_cue_duration_seconds = 7`，保存来源 version/digest；只改 Preview effective OUT，不改 canonical semantic OUT。
- Aligned Preview 固定 H.264、1920×1080、30fps；Clean A-roll 原音是唯一主音轨，不加字幕、BGM、SFX、标题、封面或发布能力。
- Runtime 根 `narration_media/`、`alignment_packages/`、`edit_bridge_packages/`、`edit_bridge_assets/`、`edit_bridge_projects/` 全部 gitignored，工件与输出均不可覆盖。
- synthetic/adversarial pass 不是正式产品验收；完整实现后必须停在真实用户 Clean A-roll Gate。

---

## File and module map

| Path | Responsibility |
|---|---|
| `src/deeptalk_studio/narration_schema.py` | `narration-media/1`、`extracted-audio/1`、`audio-timestamp-mapping/1`、`timed-transcript/1` strict schemas |
| `src/deeptalk_studio/narration_media.py` | safe import、ffprobe/packet/frame evidence、lossless extraction |
| `src/deeptalk_studio/audio_timestamp_mapping.py` | extracted time → media presentation time 与动态 tolerance |
| `src/deeptalk_studio/narration_storage.py` | Media/Audio/Mapping/Transcript immutable storage |
| `src/deeptalk_studio/transcription/base.py` | provider-neutral protocol 与 raw result types |
| `src/deeptalk_studio/transcription/deterministic.py` | 离线 deterministic provider |
| `src/deeptalk_studio/transcription/openai.py` | 当前 OpenAI adapter、chunk evidence、capability boundary |
| `src/deeptalk_studio/transcript_builder.py` | ProviderTranscript → canonical Timed Transcript |
| `src/deeptalk_studio/text_normalization.py` | NFKC/casefold/数字 alias/token span preservation |
| `src/deeptalk_studio/sequence_alignment.py` | 等价全局 DP、tie-break、forward/backward ambiguity、trace digest |
| `src/deeptalk_studio/alignment_schema.py` | Profile、Beat/Cue、gap、`script-alignment/1` schemas |
| `src/deeptalk_studio/alignment_profile.py` | candidate profile 和 immutable calibration record |
| `src/deeptalk_studio/alignment_builder.py` | Script/Transcript → Beat/Cue timeline |
| `src/deeptalk_studio/alignment_validation.py` | binding、trace、status、time 与 ambiguity 重推导 |
| `src/deeptalk_studio/alignment_storage.py` | Alignment JSON/Markdown revisions |
| `src/deeptalk_studio/material_bridge.py` | `material-production-view/1` compatibility projection |
| `src/deeptalk_studio/edit_bridge_schema.py` | placement/conflict/adjustment/profiles/Bridge/QA schemas |
| `src/deeptalk_studio/rough_cut_profile.py` | 7 秒 provenance、Preview 30fps、rounding policies |
| `src/deeptalk_studio/edit_bridge_planner.py` | unified placement、IN/OUT/duration/conflict/layout |
| `src/deeptalk_studio/edit_bridge_validation.py` | Bridge key fields、asset、status、adjustment 重推导 |
| `src/deeptalk_studio/edit_bridge_renderer.py` | canonical JSON 的 Markdown 与 BOM RFC4180 CSV reading views |
| `src/deeptalk_studio/edit_bridge_storage.py` | Bridge/QA/Preview revisions 与 user adjustment provenance |
| `src/deeptalk_studio/aligned_preview/base.py` | renderer-neutral project/render/mux protocol |
| `src/deeptalk_studio/aligned_preview/remotion.py` | project staging、validation、visual-only render、audio mux |
| `renderer_templates/aligned_preview_remotion/` | Clean A-roll + ready overlay composition |
| `src/deeptalk_studio/edit_bridge_qa.py` | root/transcript/alignment/placement/preview checks → issues → Gate |
| `src/deeptalk_studio/edit_bridge_workflow.py` | partial-success orchestration only |
| `.agents/skills/align-video/SKILL.md` | 普通用户语义入口与真实用户 Gate |
| `tests/media_fixture_factory.py` | 可重复生成微型真实媒体，不提交大二进制 |
| `tests/alignment_fixtures.py` | reviewed roots、provider units 与 A–AI case builders |
| `evaluations/audio-alignment-edit-bridge/` | 分组 eval runner、candidate profile evidence、去内容化结果 |

## Dependency order

`1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24 → 25 → 26 → 27 → 28`。Task 18 可在 Task 17 完成后与 Task 19 的模板编码分开执行，但合并验证仍按上述顺序。

### Task 1: Strict narration schemas and canonical time utilities

**Files:**
- Create: `src/deeptalk_studio/narration_schema.py`
- Create: `src/deeptalk_studio/canonical_time.py`
- Test: `tests/test_narration_schema.py`
- Test: `tests/test_canonical_time.py`

**Interfaces:**
- Consumes: existing `schema._object/_array/_enum/_string/_integer/_number` and `validation.validate_json_schema`.
- Produces: `NARRATION_MEDIA_SCHEMA`, `EXTRACTED_AUDIO_SCHEMA`, `AUDIO_TIMESTAMP_MAPPING_SCHEMA`, `TIMED_TRANSCRIPT_SCHEMA`; `format_canonical_timecode(seconds: Decimal) -> str`, `preview_frame(seconds: Decimal, fps: int = 30) -> int`, `format_preview_frame_timecode(frame: int, fps: int = 30) -> str`.

- [ ] **Step 1: Write failing schema/time tests**

```python
def test_canonical_time_is_fps_neutral_and_supports_more_than_24_hours():
    assert format_canonical_timecode(Decimal("90061.2345")) == "25:01:01.235"
    assert preview_frame(Decimal("1.001")) == 31

def test_machine_schemas_reject_unknown_fields():
    validate_json_schema(valid_mapping(), AUDIO_TIMESTAMP_MAPPING_SCHEMA, "mapping")
    with self.assertRaises(ReportValidationError):
        validate_json_schema({**valid_mapping(), "model_gate": "pass"}, AUDIO_TIMESTAMP_MAPPING_SCHEMA, "mapping")
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_narration_schema tests.test_canonical_time -v`

Expected: FAIL with `ModuleNotFoundError` for `narration_schema`/`canonical_time`.

- [ ] **Step 3: Implement all four strict contracts and Decimal half-up/ceil helpers**

```python
def format_canonical_timecode(seconds: Decimal) -> str:
    millis = int((seconds * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
```

Include every Design field, fixed `artifact_version` enum, `additionalProperties: false`, non-negative durations, stream/presentation evidence, dual extracted/media transcript boundaries, digests and continuous integer revision/order fields. Do not add frame fields to Timed Transcript.

- [ ] **Step 4: Run green tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_narration_schema tests.test_canonical_time -v`

Expected: PASS including >24h, 25/29.97/30/50/60/VFR-neutral seconds, half-up milliseconds, Preview ceil IN and exclusive OUT.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/narration_schema.py src/deeptalk_studio/canonical_time.py tests/test_narration_schema.py tests/test_canonical_time.py
git commit -m "feat: define narration and canonical time contracts"
```

### Task 2: Deterministic real-media fixture factory

**Files:**
- Create: `tests/media_fixture_factory.py`
- Create: `tests/test_media_fixture_factory.py`

**Interfaces:**
- Consumes: local `ffmpeg` and `ffprobe` executables.
- Produces: `MediaFixtureSpec`, `build_media_fixture(root: Path, spec: MediaFixtureSpec) -> Path`, `probe_fixture(path: Path) -> dict`.

- [ ] **Step 1: Write failing factory tests**

```python
def test_factory_builds_decodable_pts_offset_and_vfr_media(self):
    path = build_media_fixture(self.root, MediaFixtureSpec(name="offset", video=True, audio=True, audio_offset="0.375", vfr=True))
    probe = probe_fixture(path)
    self.assertTrue(probe["has_video"] and probe["has_audio"])
    self.assertGreaterEqual(probe["audio_start_time"], 0.37)
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_media_fixture_factory -v`

Expected: FAIL because the factory module does not exist.

- [ ] **Step 3: Implement synthetic fixture commands**

Use `subprocess.run([...], check=True)` argument arrays only. Generate 1–3 second color/testsrc video plus sine audio for MP4, MOV, M4V, M4A, WAV, AAC, FLAC and cases: identity, positive audio offset, negative raw PTS normalized by presentation, edit-list trim, AAC priming/trailing padding, internal audio gap, resampled 44.1→48 kHz, VFR, no-audio, audio-only. Keep commands and probe JSON in the temporary test directory; commit no media binary.

- [ ] **Step 4: Run green test and actual decode**

Run: `PYTHONPATH=src python3 -m unittest tests.test_media_fixture_factory -v`

Expected: PASS; each fixture is probed and decoded with `ffmpeg -v error -i <fixture> -f null -`.

- [ ] **Step 5: Commit**

```bash
git add tests/media_fixture_factory.py tests/test_media_fixture_factory.py
git commit -m "test: generate deterministic narration media fixtures"
```

### Task 3: Clean A-roll immutable media import and probe evidence

**Files:**
- Create: `src/deeptalk_studio/narration_media.py`
- Test: `tests/test_narration_media.py`

**Interfaces:**
- Consumes: Task 1 schemas and Task 2 real fixtures.
- Produces: `MediaProbeEvidence`; `probe_narration_media(path: Path) -> MediaProbeEvidence`; `import_narration_media(source: Path, media_root: Path, *, imported_at: str, id_factory: Callable[[str], str]) -> NarrationMediaResult`.

- [ ] **Step 1: Write failing import/probe tests**

```python
def test_import_copies_media_immutably_and_derives_identity(self):
    result = import_narration_media(self.mp4, self.root, imported_at=NOW, id_factory=lambda _: "MEDIA001")
    self.assertEqual(result.artifact["sha256"], sha256_file(result.immutable_path))
    self.assertNotEqual(result.immutable_path, self.mp4)
    self.assertTrue(result.artifact["presentation_evidence"]["evidence_digest"])
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_narration_media -v`

Expected: FAIL because `import_narration_media` is missing.

- [ ] **Step 3: Implement probe and importer**

Accept `.mp4/.mov/.m4v` video and `.m4a/.mp3/.wav/.aac/.flac` compatibility audio. Sanitize basename/control characters, reject symlink/non-regular/empty/unsupported files, copy with exclusive creation, then derive size/SHA/container, streams, raw PTS/timebase, nominal/average fps, VFR evidence, AAC skip/discard/padding and edit/presentation evidence from ffprobe JSON/packets/frames. Derive `media_kind`; video lacking audio is recorded but marked for downstream root failure. Never accept caller-provided identity, duration, SHA or stream conclusions.

- [ ] **Step 4: Run green unit and real-media tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_narration_media tests.test_media_fixture_factory -v`

Expected: PASS for MP4/MOV/M4V/audio-only, same-name different-SHA new media, VFR metadata, no-audio audit, traversal/symlink/duplicate/tamper rejection.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/narration_media.py tests/test_narration_media.py
git commit -m "feat: import immutable clean aroll media"
```

### Task 4: Lossless audio extraction evidence

**Files:**
- Modify: `src/deeptalk_studio/narration_media.py`
- Test: `tests/test_audio_extraction.py`

**Interfaces:**
- Consumes: `NarrationMediaResult`, canonical audio stream evidence.
- Produces: `extract_transcription_audio(media: Mapping[str, Any], output_path: Path, *, profile: Mapping[str, Any]) -> ExtractedAudioResult` with complete source PTS/sample/extraction evidence.

- [ ] **Step 1: Write failing extraction tests**

```python
def test_extraction_preserves_internal_gap_and_excludes_aac_padding(self):
    result = extract_transcription_audio(self.media, self.wav, profile=audio_extraction_profile())
    self.assertEqual(result.artifact["sample_count"], count_pcm_samples(self.wav))
    self.assertIn("internal_gap", result.artifact["applied_timeline_operations"])
    self.assertEqual(result.artifact["profile_version"], "audio-extraction-profile/1")
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_audio_extraction -v`

Expected: FAIL because extraction is not implemented.

- [ ] **Step 3: Implement evidence-driven WAV/PCM extraction**

Select the registered canonical audio stream, decode complete presentation order, preserve internal gaps as silence, exclude edit-list pre-roll and evidenced AAC priming/trailing padding, and record resampler delay/sample count/source first-last PTS. Allow deterministic sample-rate/channel conversion only; command must contain no trim, loudnorm, silence removal or tempo filter. Write output exclusively and compute file SHA/size.

- [ ] **Step 4: Run green tests against real fixtures**

Run: `PYTHONPATH=src python3 -m unittest tests.test_audio_extraction -v`

Expected: PASS for identity, edit list, AAC padding, internal gap, resampling ratio preservation and duplicate-path refusal.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/narration_media.py tests/test_audio_extraction.py
git commit -m "feat: extract evidenced transcription audio"
```

### Task 5: Audio timestamp mapping and tamper validation

**Files:**
- Create: `src/deeptalk_studio/audio_timestamp_mapping.py`
- Test: `tests/test_audio_timestamp_mapping.py`

**Interfaces:**
- Consumes: Narration Media evidence + Extracted Audio evidence.
- Produces: `derive_timestamp_mapping(media, extracted, *, mapping_id: str, created_at: str) -> dict`; `map_extracted_seconds(mapping, value: Decimal) -> Decimal`; `validate_timestamp_mapping(mapping, media, extracted) -> None`.

- [ ] **Step 1: Write failing mapping tests**

```python
def test_nonzero_offset_is_evidence_backed_not_forced_to_identity(self):
    mapping = derive_timestamp_mapping(self.media_offset, self.audio_offset, mapping_id="MAP001", created_at=NOW)
    self.assertEqual(mapping["scale_numerator"], 1)
    self.assertEqual(Decimal(mapping["offset_seconds"]), Decimal("0.375"))
    validate_timestamp_mapping(mapping, self.media_offset, self.audio_offset)
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_audio_timestamp_mapping -v`

Expected: FAIL because mapping functions are missing.

- [ ] **Step 3: Implement affine mapping and dynamic tolerance**

Derive `media = extracted * 1 + offset` only from first included decoded sample presentation PTS. Compute tolerance exactly as `max(1/output_sample_rate, codec_frame_samples/source_sample_rate if known else 0, source_time_base_tick)`. Store evidence/mapping digests, mapped start/end and rational scale; reject scale != 1, missing evidence, sample-duration mismatch or out-of-media boundaries. Never clamp.

- [ ] **Step 4: Run green mapping suite**

Run: `PYTHONPATH=src python3 -m unittest tests.test_audio_timestamp_mapping -v`

Expected: PASS for identity, positive offset, negative raw PTS, edit list, AAC priming/padding, internal gap and resampling; fail for scale tamper, offset/digest tamper, excess tolerance and mapped Transcript overflow.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/audio_timestamp_mapping.py tests/test_audio_timestamp_mapping.py
git commit -m "feat: map extracted audio to presentation time"
```

### Task 6: Immutable narration storage and invalidation chain

**Files:**
- Create: `src/deeptalk_studio/narration_storage.py`
- Modify: `.gitignore`
- Create: `narration_media/.gitkeep`
- Test: `tests/test_narration_storage.py`

**Interfaces:**
- Consumes: validated Media/Audio/Mapping/Transcript dictionaries.
- Produces: `NarrationPaths`; `save_narration_bundle(...) -> NarrationPaths`; `load_narration_bundle(media_path: Path) -> NarrationBundle`.

- [ ] **Step 1: Write failing storage tests**

```python
def test_storage_is_immutable_and_new_media_never_inherits_transcript(self):
    paths = save_narration_bundle(self.bundle, self.root)
    with self.assertRaisesRegex(NarrationStorageError, "覆盖"):
        save_narration_bundle(self.bundle, self.root)
    self.assertNotEqual(paths.media.parent, paths_for(self.changed_sha).media.parent)
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_narration_storage -v`

Expected: FAIL because storage module is missing.

- [ ] **Step 3: Implement safe dated layout and canonical reload**

Use Design paths, strict safe IDs, exclusive writes and exact file comparison on reload. Copy original only through Task 3. A new SHA or presentation duration creates a new `media_id`; no loader searches a previous media directory for Mapping/Transcript.

- [ ] **Step 4: Run green storage tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_narration_storage tests.test_narration_media -v`

Expected: PASS for no overwrite, traversal, tamper, missing artifact and changed-A-roll invalidation.

- [ ] **Step 5: Commit**

```bash
git add .gitignore narration_media/.gitkeep src/deeptalk_studio/narration_storage.py tests/test_narration_storage.py
git commit -m "feat: store narration artifacts immutably"
```

### Task 7: Provider-neutral transcription protocol and deterministic provider

**Files:**
- Create: `src/deeptalk_studio/transcription/__init__.py`
- Create: `src/deeptalk_studio/transcription/base.py`
- Create: `src/deeptalk_studio/transcription/deterministic.py`
- Test: `tests/test_transcription_provider.py`

**Interfaces:**
- Consumes: Extracted Audio Artifact.
- Produces: `ProviderTimedUnit`, `ProviderTranscript`, `TranscriptionProvider.transcribe(extracted_audio_artifact, language, configured_model) -> ProviderTranscript`, `DeterministicTranscriptionProvider`.

- [ ] **Step 1: Write failing protocol tests**

```python
def test_deterministic_provider_returns_declared_real_granularity_only(self):
    result = DeterministicTranscriptionProvider(self.units, granularity="segment").transcribe(self.audio, "zh", "fixture")
    self.assertEqual(result.timestamp_granularity, "segment")
    self.assertFalse(hasattr(result.units[0], "interpolated_words"))
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_transcription_provider -v`

Expected: FAIL because transcription protocol is missing.

- [ ] **Step 3: Implement immutable provider result dataclasses/protocol**

Require raw extracted start/end, spoken text, order, optional provider confidence, request/model metadata and raw-response digest. Reject provider-produced media timestamps, alignment status, Gate and canonical confidence fields.

- [ ] **Step 4: Run green protocol tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_transcription_provider -v`

Expected: PASS for word/token/segment fixtures, provider overlap preservation, empty/negative/reordered unit rejection at builder boundary.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/transcription tests/test_transcription_provider.py
git commit -m "feat: add provider neutral timed transcription"
```

### Task 8: OpenAI transcription adapter with explicit capability fallback

**Files:**
- Create: `src/deeptalk_studio/transcription/openai.py`
- Test: `tests/test_openai_transcription.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 7 protocol; injected `OpenAITranscriptionTransport.create(file_path, model, response_format, timestamp_granularities) -> Mapping`.
- Produces: `OpenAITranscriptionProvider`; `OPENAI_TRANSCRIPTION_CAPABILITIES`; normalized `ProviderTranscript`.

**Official capability record (verified 2026-08-13):**
- Official Python SDK call is `client.audio.transcriptions.create(model=..., file=..., response_format=..., timestamp_granularities=[...])`.
- File transcription guide caps uploads at 25 MB and lists MP3/MP4/MPEG/MPGA/M4A/WAV/WebM; API reference additionally accepts FLAC/OGG.
- Current endpoint lists `gpt-transcribe`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-mini-transcribe-2025-12-15`, `whisper-1`, `gpt-4o-transcribe-diarize`.
- Current guide says `timestamp_granularities` is only supported for `whisper-1`; word timestamps require `verbose_json`. Diarized output provides segment boundaries and must remain coarse here. Sources: `https://developers.openai.com/api/docs/guides/speech-to-text` and `https://developers.openai.com/api/reference/resources/audio/subresources/transcriptions/methods/create`.

- [ ] **Step 1: Write failing adapter/capability tests**

```python
def test_whisper_word_response_normalizes_without_provider_owned_status(self):
    provider = OpenAITranscriptionProvider(api_key="test", transport=self.transport)
    result = provider.transcribe(self.audio, "zh", "whisper-1")
    self.assertEqual(result.timestamp_granularity, "word")
    self.assertNotIn("alignment_status", result.raw_metadata)

def test_model_without_timestamps_fails_instead_of_fabricating_precision(self):
    with self.assertRaisesRegex(TranscriptionCapabilityError, "时间戳"):
        provider.transcribe(self.audio, "zh", "gpt-transcribe")
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_openai_transcription -v`

Expected: FAIL because adapter is missing.

- [ ] **Step 3: Implement adapter and >25 MB deterministic request chunks**

Default to `whisper-1` word timestamps. Split oversized WAV at exact sample boundaries into <=24 MiB temporary WAV chunks, no overlap/time stretch; add exact `chunk_start_sample / sample_rate` to provider boundaries and preserve all request IDs only in provider audit metadata. Use injected transport in tests, redact keys/errors, delete temporary chunks, and distinguish `TranscriptionEnvironmentError` (network/key/API unavailable) from invalid provider response. Segment responses normalize as segment units; untimed responses raise capability error.

- [ ] **Step 4: Run green adapter tests without network**

Run: `PYTHONPATH=src python3 -m unittest tests.test_openai_transcription -v`

Expected: PASS for SDK-shaped word response, segment coarse response, >25 MB chunk offsets, malformed/overlap response, key redaction, supported-format check and non-timestamp model refusal. No API call occurs.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/transcription/openai.py tests/test_openai_transcription.py README.md
git commit -m "feat: adapt evidenced OpenAI word timestamps"
```

### Task 9: Timed Transcript builder and validation

**Files:**
- Create: `src/deeptalk_studio/transcript_builder.py`
- Test: `tests/test_timed_transcript.py`

**Interfaces:**
- Consumes: ProviderTranscript + Media/Extracted/Mapping.
- Produces: `build_timed_transcript(...) -> dict`; `validate_timed_transcript(transcript, media, extracted, mapping) -> None`.

- [ ] **Step 1: Write failing transcript tests**

```python
def test_builder_maps_every_real_provider_boundary(self):
    artifact = build_timed_transcript(self.provider_result, self.media, self.audio, self.mapping, transcript_id="TR001", created_at=NOW)
    self.assertEqual(artifact["timed_units"][0]["media_start_seconds"], "0.375")
    validate_timed_transcript(artifact, self.media, self.audio, self.mapping)
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_timed_transcript -v`

Expected: FAIL because builder is missing.

- [ ] **Step 3: Implement builder/revalidator**

Assign continuous unit IDs/order, preserve provider extracted boundaries, map each boundary through Task 5, derive metadata/transcript digests, and validate non-empty/monotonic/non-overlapping units, derivative bounds, media bounds, exact Mapping binding and truthful granularity. A segment stays one segment; no client word split with fabricated timestamps.

- [ ] **Step 4: Run green transcript tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_timed_transcript tests.test_audio_timestamp_mapping -v`

Expected: PASS for word/segment and nonzero mapping; fail for SHA/digest/granularity/order/overlap/boundary tamper.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/transcript_builder.py tests/test_timed_transcript.py
git commit -m "feat: build canonical timed transcripts"
```

### Task 10: Span-preserving Chinese and mixed-text normalization

**Files:**
- Create: `src/deeptalk_studio/text_normalization.py`
- Test: `tests/test_text_normalization.py`

**Interfaces:**
- Consumes: reviewed Script strings or Transcript timed units.
- Produces: `NormalizedToken`; `normalize_script_text(text: str, profile: Mapping[str, Any]) -> tuple[NormalizedToken, ...]`; `normalize_transcript_units(units, profile) -> tuple[NormalizedToken, ...]`; `normalization_digest(...) -> str`.

- [ ] **Step 1: Write failing normalization tests**

```python
def test_nfkc_numeric_alias_and_original_span_are_preserved(self):
    tokens = normalize_script_text("ＡI增长百分之三十，约30%。", normalization_profile())
    self.assertIn("30%", {key for token in tokens for key in token.match_keys})
    self.assertEqual("ＡI", source_text[tokens[0].original_start_char:tokens[0].original_end_char])
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_text_normalization -v`

Expected: FAIL because normalizer is missing.

- [ ] **Step 3: Implement exact profile order**

Apply NFKC, Unicode casefold, punctuation/space skipping without span deletion, per-Han tokenization, continuous Latin and Arabic numeric tokens, strict Chinese number/date/percent/negative/decimal aliases and stable mixed-language boundaries. Transcript tokens retain source unit ID, provider boundary and granularity.

- [ ] **Step 4: Run green normalization tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_text_normalization -v`

Expected: PASS for Chinese/English punctuation, NFKC, full/half width, casefold, strict Chinese numerals, Arabic digits, dates/percent/negative decimals, ambiguous “一、两”, mixed text and original char spans.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/text_normalization.py tests/test_text_normalization.py
git commit -m "feat: normalize narration with reversible spans"
```

### Task 11: Strict alignment schemas and candidate profiles

**Files:**
- Create: `src/deeptalk_studio/alignment_schema.py`
- Create: `src/deeptalk_studio/alignment_profile.py`
- Create: `config/alignment-profile-candidate.json`
- Test: `tests/test_alignment_profile_schema.py`

**Interfaces:**
- Consumes: schema helpers.
- Produces: `ALIGNMENT_PROFILE_SCHEMA`, `SCRIPT_ALIGNMENT_SCHEMA`; `load_alignment_profile(path: Optional[Path] = None) -> dict`; `alignment_profile_digest(profile) -> str`.

- [ ] **Step 1: Write failing profile/schema tests**

```python
def test_candidate_values_are_versioned_and_digest_bound():
    profile = load_alignment_profile()
    self.assertEqual(profile["artifact_version"], "alignment-profile/1")
    self.assertEqual(profile["ambiguity_normalized_margin"], 0.08)
    self.assertEqual(profile["profile_digest"], alignment_profile_digest(profile))
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_profile_schema -v`

Expected: FAIL because schemas/profile do not exist.

- [ ] **Step 3: Implement profile as explicit candidate, not accepted calibration**

Encode Design candidate scores/floors `+4/+3/-2.5/-2/-1.5`, `0.08`, `0.85/0.88`, `0.55/0.65`, 8 tokens and epsilon 0.001. Schema requires `calibration_status = candidate | accepted`, immutable value revision, source Design HEAD and digest. Define full Beat/Cue/gap/trace/artifact contract and reject model-owned threshold/status fields.

- [ ] **Step 4: Run green profile tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_profile_schema -v`

Expected: PASS for exact values/schema; fail for digest, threshold, revision, unknown field and premature `accepted` tamper.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/alignment_schema.py src/deeptalk_studio/alignment_profile.py config/alignment-profile-candidate.json tests/test_alignment_profile_schema.py
git commit -m "feat: define candidate alignment profile"
```

### Task 12: Deterministic global sequence alignment

**Files:**
- Create: `src/deeptalk_studio/sequence_alignment.py`
- Test: `tests/test_sequence_alignment.py`
- Test: `tests/test_sequence_alignment_properties.py`

**Interfaces:**
- Consumes: normalized Script/Transcript tokens + accepted/candidate Profile.
- Produces: `AlignmentOperation`, `CandidateWindow`, `AlignmentTrace`; `align_sequences(script_tokens, transcript_tokens, profile) -> AlignmentTrace`; `rederive_alignment_trace(...) -> AlignmentTrace`.

- [ ] **Step 1: Write failing DP/tie/ambiguity tests**

```python
def test_repeated_span_exposes_candidates_instead_of_hiding_tie():
    trace = align_sequences(tokens("甲乙甲乙"), timed_tokens("甲乙甲乙甲乙"), profile())
    self.assertGreaterEqual(len(trace.candidate_windows), 2)
    self.assertEqual(trace.ambiguity_code, "ambiguous_match")
    self.assertEqual(trace.digest, rederive_alignment_trace(...).digest)
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_sequence_alignment tests.test_sequence_alignment_properties -v`

Expected: FAIL because sequence alignment is missing.

- [ ] **Step 3: Implement algorithm/1 exactly**

Use global DP with primary/numeric/substitution/deletion/insertion scores and tie-break order: primary → numeric → transcript insertion → script deletion → substitution → earlier transcript index. Compute forward/backward optimal scores and all non-overlapping candidate windows within normalized 0.08 margin; perform Beat-local candidate scans and order inversion detection; group deletion/insertion gaps. For long稿, use row checkpoints and deterministic recomputation so the canonical operations/candidate set/digest equals the full-matrix reference implementation used by tests.

- [ ] **Step 4: Run green and equivalence/property tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_sequence_alignment tests.test_sequence_alignment_properties -v`

Expected: PASS for insertion/deletion/substitution/numeric alias/repetition/order inversion/long gaps/tie-break; randomized short inputs prove optimized and reference DP identical and same inputs produce stable digest.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/sequence_alignment.py tests/test_sequence_alignment.py tests/test_sequence_alignment_properties.py
git commit -m "feat: align script and transcript deterministically"
```

### Task 13: Beat and Cue timeline builder

**Files:**
- Create: `src/deeptalk_studio/alignment_builder.py`
- Create: `tests/alignment_fixtures.py`
- Test: `tests/test_alignment_builder.py`
- Test: `tests/test_cue_timeline.py`

**Interfaces:**
- Consumes: reviewed Script, Timed Transcript, Mapping, normalization/Profile, Material Cue Sheet.
- Produces: `build_script_alignment(script, transcript, mapping, profile, cues, *, alignment_id, created_at) -> dict`.

- [ ] **Step 1: Write failing Beat/Cue tests**

```python
def test_exact_anchor_reuses_existing_beat_and_cue_identity():
    artifact = build_script_alignment(self.script, self.transcript, self.mapping, self.profile, self.cues, alignment_id="AL001", created_at=NOW)
    self.assertEqual(artifact["beat_timeline"][0]["beat_id"], self.script.beats[0].beat_id)
    self.assertEqual(artifact["cue_timeline"][0]["cue_id"], self.cues[0]["cue_id"])
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_builder tests.test_cue_timeline -v`

Expected: FAIL because builder is missing.

- [ ] **Step 3: Implement Beat status and Cue local mapping**

Derive match score/coverage/similarity/status/confidence from Profile and trace. Build Beat actual windows from first/last real units; needs_review only retains canonical window when candidate is unique; unmatched has null time. Locate each `placement_anchor` uniquely in its bound Beat char span, map it through the same token-unit path, derive semantic span to next Cue/Beat end, and emit exact `aligned/needs_review/coarse/unplaced` without new IDs.

- [ ] **Step 4: Run green timeline tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_builder tests.test_cue_timeline -v`

Expected: PASS for exact/missing/duplicate anchor, Beat needs_review, unique candidate, timestamp monotonicity, segment coarse, Beat boundary, same-Beat multiple Cues and semantic spans.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/alignment_builder.py tests/alignment_fixtures.py tests/test_alignment_builder.py tests/test_cue_timeline.py
git commit -m "feat: build beat and cue timelines"
```

### Task 14: Alignment validator and immutable storage

**Files:**
- Create: `src/deeptalk_studio/alignment_validation.py`
- Create: `src/deeptalk_studio/alignment_storage.py`
- Modify: `.gitignore`
- Create: `alignment_packages/.gitkeep`
- Test: `tests/test_alignment_validation.py`
- Test: `tests/test_alignment_storage.py`

**Interfaces:**
- Consumes: Script/Transcript/Mapping/Profile/Cues and built Alignment.
- Produces: `validate_script_alignment(...) -> None`; `save_script_alignment(artifact, root) -> AlignmentPaths`; `load_script_alignment(...) -> dict`.

- [ ] **Step 1: Write failing re-derivation/storage tests**

```python
def test_validator_rejects_status_tamper_even_with_recomputed_outer_digest(self):
    forged = deepcopy(self.artifact)
    forged["beat_timeline"][0]["alignment_status"] = "aligned"
    forged["artifact_digest"] = digest_without(forged, "artifact_digest")
    with self.assertRaises(AlignmentValidationError):
        validate_script_alignment(forged, self.script, self.transcript, self.mapping, self.profile, self.cues)
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_validation tests.test_alignment_storage -v`

Expected: FAIL because validator/storage are missing.

- [ ] **Step 3: Implement canonical re-build comparison and immutable saves**

Re-run normalization, DP, ambiguity, Beat/Cue derivation and digest; compare every machine field. Check Script content digest, Media/Mapping/Transcript/Profile bindings, Beat order, timestamps and real unit boundaries. Save `script-alignment-rNNNN.json/.md` exclusively; Markdown may describe gaps but cannot become machine input.

- [ ] **Step 4: Run green validation/storage tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_validation tests.test_alignment_storage -v`

Expected: PASS; fail on Script/Transcript/Profile/trace/status/confidence/candidate/time/digest tamper and overwrite/path traversal.

- [ ] **Step 5: Commit**

```bash
git add .gitignore alignment_packages/.gitkeep src/deeptalk_studio/alignment_validation.py src/deeptalk_studio/alignment_storage.py tests/test_alignment_validation.py tests/test_alignment_storage.py
git commit -m "feat: revalidate and store script alignments"
```

### Task 15: Candidate Profile calibration with A–AI alignment cases

**Files:**
- Create: `evaluations/audio-alignment-edit-bridge/run_alignment_calibration.py`
- Create: `evaluations/audio-alignment-edit-bridge/alignment-cases.json`
- Create: `evaluations/audio-alignment-edit-bridge/alignment-profile-evidence.json`
- Modify: `config/alignment-profile-candidate.json`
- Test: `tests/test_alignment_calibration.py`

**Interfaces:**
- Consumes: deterministic provider, normalization, sequence alignment, builder/validator.
- Produces: `run_alignment_calibration(profile) -> CalibrationResult`; accepted Profile revision/digest only after mandatory cases pass.

- [ ] **Step 1: Write failing calibration acceptance test**

```python
def test_candidate_cannot_be_accepted_without_false_precision_suite():
    result = run_alignment_calibration(load_alignment_profile())
    self.assertTrue(result.case("A").all_beats_aligned)
    self.assertTrue(result.case("C").later_beats_recovered)
    self.assertEqual(result.false_ready_cases, [])
```

- [ ] **Step 2: Run red calibration**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_calibration -v`

Expected: FAIL while Profile is candidate and evidence is absent.

- [ ] **Step 3: Encode alignment-sensitive A–F, S, T, AH fixtures and execute**

Require A all aligned; C later Beat recovery; D/T/AH no arbitrary selection; E no false ready; F inversion exposed; S coarse/no interpolation. Also run B/U normalization tolerance. If the Design candidate values pass, change only `calibration_status` to `accepted` and record cases/profile/output digests. If they fail, create Profile `value_revision=2` with explicit old/new values and reason in evidence, rerun the same suite, and never mutate revision 1 evidence.

- [ ] **Step 4: Run green calibration and deterministic repeat**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_calibration -v && PYTHONPATH=src python3 evaluations/audio-alignment-edit-bridge/run_alignment_calibration.py --verify-repeat`

Expected: PASS; two runs have identical case results and trace digests, with zero false-ready in D/E/F/S/T/AH.

- [ ] **Step 5: Commit**

```bash
git add config/alignment-profile-candidate.json evaluations/audio-alignment-edit-bridge tests/test_alignment_calibration.py
git commit -m "test: calibrate deterministic alignment profile"
```

### Task 16: Material compatibility production projection

**Files:**
- Create: `src/deeptalk_studio/material_bridge.py`
- Test: `tests/test_material_bridge.py`

**Interfaces:**
- Consumes: historical canonical Material r1/provenance/Review/r2 plus Script/Research and material asset root.
- Produces: `build_material_production_view(package_path, script, report, profile, asset_root) -> dict`; `validate_material_production_view(...) -> None`.

- [ ] **Step 1: Write failing compatibility tests**

```python
def test_rights_only_reference_item_can_be_production_eligible_without_rewriting_history(self):
    view = build_material_production_view(self.package_path, self.script, self.report, self.profile, self.assets)
    self.assertEqual(self.original_package.materials[0].eligibility_status, "reference_only")
    self.assertEqual(view["items"][0]["production_status"], "ready")
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_material_bridge -v`

Expected: FAIL because projection is missing.

- [ ] **Step 3: Implement canonical replay plus rights-only filtering**

Reuse `load_material_package` to replay history, retain rights/reuse fields, remove only `rights_reuse` check, `permission_needed` issue and rights-only eligibility from production decision. Recheck source identity, non-rights review blockers, local regular file/root/path, magic MIME/codec, size/SHA, Claim/Evidence/Research and caption grounding. URL-only stays `missing_asset`; do not add copyright confirmation UX.

- [ ] **Step 4: Run green projection tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_material_bridge tests.test_material_storage_workflow tests.test_material_validation -v`

Expected: PASS for rights-only compatibility; fail/reject for fabricated source, wrong identity, missing/tampered/unsafe file, codec, grounding and caption mismatch.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/material_bridge.py tests/test_material_bridge.py
git commit -m "feat: project reviewed materials for production"
```

### Task 17: Edit Bridge schemas and versioned Rough Cut profiles

**Files:**
- Create: `src/deeptalk_studio/edit_bridge_schema.py`
- Create: `src/deeptalk_studio/rough_cut_profile.py`
- Create: `config/rough-cut-duration-profile.json`
- Create: `config/aligned-preview-profile.json`
- Test: `tests/test_edit_bridge_profile_schema.py`

**Interfaces:**
- Consumes: Material Profile 0.5 and schema helpers.
- Produces: schemas for `visual-placement/1`, `timing-conflict/1`, `preview-adjustment/1`, `rough-cut-duration-profile/1`, `aligned-preview-profile/1`, `edit-bridge/1`, Edit Bridge QA; `load_rough_cut_profile()`, `load_aligned_preview_profile()`.

- [ ] **Step 1: Write failing schema/provenance tests**

```python
def test_still_cap_is_inherited_and_digest_bound(self):
    profile = load_rough_cut_profile(load_material_profile())
    self.assertEqual(profile["still_exposure_seconds"], 7)
    self.assertEqual(profile["source_profile_version"], "0.5")
    self.assertTrue(profile["source_profile_digest"])
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_profile_schema -v`

Expected: FAIL because Bridge schemas/profiles are missing.

- [ ] **Step 3: Implement strict orthogonal contracts**

Include four source kinds, all placement/time/duration/layout/audio/source fields, separate status enums, canonical/Preview fields, conflict classes, user adjustment provenance, exact Bridge root bindings and QA checks/issues/Gate. Preview profile fixes 1920×1080/30fps/ceil/exclusive OUT. Rough Cut Profile derives 7 seconds and source digest at load time; a new profile revision never changes stored Bridge profile digest.

- [ ] **Step 4: Run green profile/schema tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_profile_schema -v`

Expected: PASS for <=7, >7 profile metadata and tamper; schemas reject mixed placement/timing states, canonical `HH:MM:SS:FF`, arbitrary renderer status and unknown fields.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/edit_bridge_schema.py src/deeptalk_studio/rough_cut_profile.py config/rough-cut-duration-profile.json config/aligned-preview-profile.json tests/test_edit_bridge_profile_schema.py
git commit -m "feat: define edit bridge and rough cut profiles"
```

### Task 18: Unified visual placement source bindings

**Files:**
- Create: `src/deeptalk_studio/edit_bridge_planner.py`
- Test: `tests/test_visual_placement.py`
- Test: `tests/test_real_material_placement.py`
- Test: `tests/test_motion_placement.py`

**Interfaces:**
- Consumes: Alignment Beat/Cue timeline, material-production-view, Production Plan, Motion Manifest/QA, Media.
- Produces: `build_base_aroll_placement(media) -> dict`; `build_visual_placements(...) -> tuple[dict, ...]`.

- [ ] **Step 1: Write failing source binding tests**

```python
def test_video_without_source_range_keeps_narration_window_but_is_not_ready():
    placement = placement_for(self.video_without_range)
    self.assertEqual(placement["placement_status"], "clip_selection_needed")
    self.assertIsNotNone(placement["semantic_in_seconds"])
    self.assertIsNone(placement["source_clip_in_seconds"])
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_placement tests.test_real_material_placement tests.test_motion_placement -v`

Expected: FAIL because planner is missing.

- [ ] **Step 3: Implement one placement contract for all sources**

Create `VP0000` A-roll `[0,duration]`. For real images validate local binding/decode/contain/grounding; for videos preserve narration/source timelines and require explicit clip range for ready; for Motion revalidate QA-ready Manifest, plan/scene/cue/beat binding, SHA and designed duration without rerender or Research reinterpretation. Assign only existing Beat/Cue/Scene IDs and default layouts/audio policies.

- [ ] **Step 4: Run green placement tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_visual_placement tests.test_real_material_placement tests.test_motion_placement -v`

Expected: PASS for clean A-roll, real image contain, video range/no-range, source audio mute, QA-ready Motion reuse, missing/rejected assets and no fake overlay.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/edit_bridge_planner.py tests/test_visual_placement.py tests/test_real_material_placement.py tests/test_motion_placement.py
git commit -m "feat: bind unified visual placements"
```

### Task 19: IN/OUT/duration/conflict and Preview adjustment planner

**Files:**
- Modify: `src/deeptalk_studio/edit_bridge_planner.py`
- Test: `tests/test_duration_conflicts.py`
- Test: `tests/test_preview_adjustments.py`

**Interfaces:**
- Consumes: source-bound placements + Rough Cut/Preview profiles.
- Produces: `derive_placement_timing(placements, profiles, user_adjustments=()) -> PlacementTimingResult` containing updated placements, conflicts and adjustments.

- [ ] **Step 1: Write failing orthogonality/duration tests**

```python
def test_reliable_motion_mismatch_warns_without_cancelling_ready():
    result = derive_placement_timing([self.long_motion], self.profiles)
    self.assertEqual(result.placements[0]["placement_status"], "ready")
    self.assertEqual(result.placements[0]["timing_status"], "warning")
    self.assertEqual(result.conflicts[0]["conflict_class"], "timing_warning")
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_duration_conflicts tests.test_preview_adjustments -v`

Expected: FAIL because timing derivation is absent.

- [ ] **Step 3: Implement semantic and Preview policies separately**

IN/OUT come only from unique real unit boundaries; target duration is semantic duration. Emit video/Motion natural-duration warnings, overlap takeover, same-canonical-start selection blocker, out-of-bounds rejection and frame-collision adjustment. Cap still Preview exposure at inherited 7 seconds, earlier next overlay, or structured user override while preserving semantic OUT. Derive 30fps ceil frames/timecodes only after seconds pass bounds. Never loop/stretch/move/clamp.

- [ ] **Step 4: Run green timing tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_duration_conflicts tests.test_preview_adjustments tests.test_canonical_time -v`

Expected: PASS for image/video/Motion natural/target duration, shorter/longer asset, overlap, same-start ambiguity, <=7/>7 still, earlier overlay, user override, 25/29.97/VFR sources and Preview frame collision.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/edit_bridge_planner.py tests/test_duration_conflicts.py tests/test_preview_adjustments.py
git commit -m "feat: derive visual timing and preview policy"
```

### Task 20: Edit Bridge builder, validator and canonical outputs

**Files:**
- Modify: `src/deeptalk_studio/edit_bridge_planner.py`
- Create: `src/deeptalk_studio/edit_bridge_validation.py`
- Create: `src/deeptalk_studio/edit_bridge_renderer.py`
- Test: `tests/test_edit_bridge_validation.py`
- Test: `tests/test_edit_bridge_outputs.py`

**Interfaces:**
- Consumes: all exact root artifacts, placements/conflicts/adjustments/profiles.
- Produces: `build_edit_bridge(...) -> dict`; `validate_edit_bridge(...) -> None`; `render_edit_bridge_markdown(bridge) -> str`; `render_edit_bridge_csv(bridge) -> bytes`（UTF-8 BOM）.

- [ ] **Step 1: Write failing Bridge/tamper/output tests**

```python
def test_csv_is_bom_rfc4180_and_marks_preview_columns(self):
    data = render_edit_bridge_csv(self.bridge)
    self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
    header = data.decode("utf-8-sig").splitlines()[0]
    self.assertIn("Preview IN frame", header)
    self.assertIn("canonical IN HH:MM:SS.mmm", header)
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_validation tests.test_edit_bridge_outputs -v`

Expected: FAIL because Bridge builder/validator/renderers are missing.

- [ ] **Step 3: Implement exact root binding and re-derivation**

Bind Media/Audio/Mapping/Transcript/Script/Research/Material/View/Production/Motion/Alignment/Profile IDs/revisions/digests. Re-run placement/timing and compare machine fields, asset bindings and package digest. CSV uses Python `csv` with RFC4180 quoting and the approved fixed columns. Markdown groups placed/warning/unplaced items by safe filename/caption/Beat context and excludes absolute paths, token matrices, Claim IDs, traceback and raw ffmpeg commands.

- [ ] **Step 4: Run green Bridge/output tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_validation tests.test_edit_bridge_outputs -v`

Expected: PASS for JSON/Markdown/CSV; fail for any root/status/timecode/profile/adjustment/asset/digest tamper and unready placement carrying Preview frames.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/edit_bridge_planner.py src/deeptalk_studio/edit_bridge_validation.py src/deeptalk_studio/edit_bridge_renderer.py tests/test_edit_bridge_validation.py tests/test_edit_bridge_outputs.py
git commit -m "feat: build and render canonical edit bridges"
```

### Task 21: Immutable Bridge revisions and natural-language user adjustments

**Files:**
- Create: `src/deeptalk_studio/edit_bridge_storage.py`
- Modify: `.gitignore`
- Create: `edit_bridge_packages/.gitkeep`
- Create: `edit_bridge_assets/.gitkeep`
- Create: `edit_bridge_projects/.gitkeep`
- Test: `tests/test_edit_bridge_storage.py`
- Test: `tests/test_edit_bridge_revisions.py`

**Interfaces:**
- Consumes: validated Bridge/QA/Preview; user feedback string.
- Produces: `save_edit_bridge(...) -> EditBridgePaths`; `resolve_adjustment_target(bridge, feedback) -> AdjustmentResolution`; `create_bridge_revision(previous, adjustment, *, created_at) -> dict`.

- [ ] **Step 1: Write failing revision tests**

```python
def test_shorter_screenshot_creates_bridge_revision_only(self):
    resolution = resolve_adjustment_target(self.bridge, "这张监管文件截图时间短一点")
    revised = create_bridge_revision(self.bridge, resolution.adjustment, created_at=NOW2)
    self.assertEqual(revised["revision"], self.bridge["revision"] + 1)
    self.assertEqual(revised["alignment_digest"], self.bridge["alignment_digest"])
    self.assertEqual(self.bridge["revision"], 1)
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_storage tests.test_edit_bridge_revisions -v`

Expected: FAIL because storage/revision resolver is missing.

- [ ] **Step 3: Implement immutable paths and unique-only resolver**

Save approved JSON/MD/CSV/QA filenames under Design directories with exclusive writes. Resolve “截图太长/短、一直留真人、视频晚一点、关系图早/晚一点” by safe filename, caption, Beat spoken text and time neighborhood; auto-create revision only for one match. Multiple matches return 2–3 readable candidates and never expose IDs/timestamps. New Clean A-roll requires a new root chain; profile revision changes do not rewrite old Bridge.

- [ ] **Step 4: Run green storage/revision tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_storage tests.test_edit_bridge_revisions -v`

Expected: PASS for immutability, unique resolution, ambiguous prompt, alignment preservation, new-media invalidation, profile tamper and no absolute path leakage.

- [ ] **Step 5: Commit**

```bash
git add .gitignore edit_bridge_packages/.gitkeep edit_bridge_assets/.gitkeep edit_bridge_projects/.gitkeep src/deeptalk_studio/edit_bridge_storage.py tests/test_edit_bridge_storage.py tests/test_edit_bridge_revisions.py
git commit -m "feat: preserve edit bridge revisions"
```

### Task 22: Renderer-neutral Aligned Preview adapter and staging Gate

**Files:**
- Create: `src/deeptalk_studio/aligned_preview/__init__.py`
- Create: `src/deeptalk_studio/aligned_preview/base.py`
- Create: `src/deeptalk_studio/aligned_preview/remotion.py`
- Test: `tests/test_aligned_preview_adapter.py`

**Interfaces:**
- Consumes: validated Bridge, Media, allowed asset roots, aligned-preview profile.
- Produces: `AlignedPreviewProject`, `AlignedPreviewRender`, `AlignedPreviewRenderer.prepare_project/validate_project/render_visual/mux_audio`.

- [ ] **Step 1: Write failing staging tests**

```python
def test_only_ready_placements_are_staged(self):
    project = self.renderer.prepare_project(self.bridge, self.media, self.roots, self.project_root)
    self.assertEqual(set(project.staged_placement_ids), {"VP0000", "VP0001"})
    self.assertNotIn("VP0002", project.payload_text)
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_aligned_preview_adapter -v`

Expected: FAIL because adapter is missing.

- [ ] **Step 3: Implement safe staging and typed command checks**

Revalidate each staged file root/path/MIME/codec/size/SHA and exact placement binding. Stage A-roll as layer 0 plus only ready overlays; skip coarse/needs_review/unplaced/missing/clip-selection/rejected. Reuse typed command/result patterns from `production_renderers/base.py`, sanitize command summaries and create exactly one Remotion project revision.

- [ ] **Step 4: Run green adapter tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_aligned_preview_adapter -v`

Expected: PASS for ready-only staging, tampered/unready rejection, path safety, Motion reuse without rerender and partial placement isolation.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/aligned_preview tests/test_aligned_preview_adapter.py
git commit -m "feat: stage aligned preview projects safely"
```

### Task 23: Remotion Aligned Preview composition

**Files:**
- Create: `renderer_templates/aligned_preview_remotion/package.json`
- Create: `renderer_templates/aligned_preview_remotion/package-lock.json`
- Create: `renderer_templates/aligned_preview_remotion/tsconfig.json`
- Create: `renderer_templates/aligned_preview_remotion/eslint.config.mjs`
- Create: `renderer_templates/aligned_preview_remotion/remotion.config.ts`
- Create: `renderer_templates/aligned_preview_remotion/src/index.ts`
- Create: `renderer_templates/aligned_preview_remotion/src/Root.tsx`
- Create: `renderer_templates/aligned_preview_remotion/src/AlignedPreview.tsx`
- Create: `renderer_templates/aligned_preview_remotion/src/index.css`
- Test: `tests/test_aligned_preview_remotion.py`

**Interfaces:**
- Consumes: staged `bridge.json` and assets from Task 22.
- Produces: `AlignedPreview` composition at 1920×1080, 30fps, media-duration frames, visual-only MP4.

- [ ] **Step 1: Write failing template contract test**

```python
def test_composition_uses_aroll_base_and_muted_ready_overlays(self):
    source = TEMPLATE.read_text(encoding="utf-8")
    self.assertIn("layer 0", source)
    self.assertIn("muted", source)
    self.assertNotIn("backgroundMusic", source)
```

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python3 -m unittest tests.test_aligned_preview_remotion -v`

Expected: FAIL because template does not exist.

- [ ] **Step 3: Implement frame-driven composition**

Render A-roll contain + neutral background for all frames. Overlay ready image/screenshot with contain, ready B-roll from explicit source clip frames muted, and ready Motion muted for Preview effective frame range. When overlay ends or asset is naturally shorter, expose A-roll; never loop/stretch. Do not render missing cards, subtitles, BGM, SFX, title or cover. Use `useCurrentFrame`, `Sequence`, `OffthreadVideo`/`Img`; no CSS timing.

- [ ] **Step 4: Run template lint/typecheck/composition tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_aligned_preview_remotion -v && npm --prefix renderer_templates/aligned_preview_remotion ci && npm --prefix renderer_templates/aligned_preview_remotion run lint && npm --prefix renderer_templates/aligned_preview_remotion run typecheck`

Expected: PASS and composition reports 1920×1080/30fps with duration from media presentation seconds.

- [ ] **Step 5: Commit**

```bash
git add renderer_templates/aligned_preview_remotion tests/test_aligned_preview_remotion.py
git commit -m "feat: compose aligned aroll visual preview"
```

### Task 24: Clean A-roll audio mux and Preview Manifest

**Files:**
- Modify: `src/deeptalk_studio/aligned_preview/remotion.py`
- Test: `tests/test_preview_audio_mux.py`
- Test: `tests/test_preview_manifest.py`

**Interfaces:**
- Consumes: visual-only render + immutable Clean A-roll + Bridge/Profile.
- Produces: `mux_clean_aroll_audio(visual_path, media, output_path) -> AudioMuxResult`; `build_aligned_preview_manifest(...) -> dict`.

- [ ] **Step 1: Write failing audio preservation tests**

```python
def test_mux_keeps_single_aroll_audio_without_edit_filters(self):
    result = mux_clean_aroll_audio(self.visual, self.media, self.output)
    self.assertEqual(result.audio_stream_count, 1)
    self.assertNotRegex(result.command_summary, r"trim|loudnorm|silenceremove|atempo")
    self.assertLessEqual(abs(result.duration_seconds - self.media_duration), 1 / 30)
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_preview_audio_mux tests.test_preview_manifest -v`

Expected: FAIL because mux/Manifest functions are missing.

- [ ] **Step 3: Implement copy-first mux boundary**

Map visual video + canonical Clean A-roll audio only. Attempt codec copy when MP4-compatible; otherwise convert audio only to AAC and record conversion. Never trim, normalize, time-stretch, mix source B-roll audio or add silence. Probe final H.264/1920×1080/30fps/audio stream/duration, calculate size/SHA, bind Bridge/Profile/renderer/command digest in Manifest.

- [ ] **Step 4: Run green real-media mux tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_preview_audio_mux tests.test_preview_manifest -v`

Expected: PASS for AAC copy, incompatible-codec conversion, single audio track, duration tolerance and Manifest tamper; source B-roll audio never appears.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/aligned_preview/remotion.py tests/test_preview_audio_mux.py tests/test_preview_manifest.py
git commit -m "feat: mux canonical aroll audio into preview"
```

### Task 25: Alignment + Edit Bridge QA and fail-closed Gate

**Files:**
- Create: `src/deeptalk_studio/edit_bridge_qa.py`
- Test: `tests/test_edit_bridge_qa.py`
- Test: `tests/test_edit_bridge_qa_tamper.py`

**Interfaces:**
- Consumes: every root artifact, Bridge, Preview Manifest/file and real assets.
- Produces: `run_edit_bridge_qa(inputs: EditBridgeQAInputs) -> dict`; `validate_edit_bridge_qa(qa, inputs) -> None`.

- [ ] **Step 1: Write failing check→issue→Gate tests**

```python
def test_unready_asset_used_by_preview_is_package_fail(self):
    qa = run_edit_bridge_qa(self.inputs_with_unready_preview_asset)
    self.assertEqual(qa["package_gate_status"], "fail")
    self.assertIn("preview_used_unready_asset", {i["issue_type"] for i in qa["issues"]})
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_qa tests.test_edit_bridge_qa_tamper -v`

Expected: FAIL because QA is missing.

- [ ] **Step 3: Implement five typed check groups and deterministic Gate**

Root checks re-probe Media and all exact revisions/digests. Transcript checks rederive Mapping/units. Alignment checks rerun normalization/DP/status. Placement checks re-read files and rebuild time/layout/audio/conflicts/adjustments. Preview checks ffprobe actual file and Manifest/binding/used placements. Map each failed check to stable issue type/scope/severity. Invalid root/mapping/transcript or tampered/unready asset actually used is fail; valid roots with isolated needs_review/coarse/missing/clip selection/timing/long-still is warnings; all ready/valid is pass.

- [ ] **Step 4: Run green QA/tamper tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_qa tests.test_edit_bridge_qa_tamper -v`

Expected: PASS for partial success and full pass; detect Mapping, Transcript binding, alignment status, placement status, timecode, adjustment, asset SHA, Preview Manifest and Gate/issue tamper.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/edit_bridge_qa.py tests/test_edit_bridge_qa.py tests/test_edit_bridge_qa_tamper.py
git commit -m "feat: gate alignment and edit bridge outputs"
```

### Task 26: Partial-success workflow orchestration

**Files:**
- Create: `src/deeptalk_studio/edit_bridge_workflow.py`
- Test: `tests/test_edit_bridge_workflow.py`
- Test: `tests/test_edit_bridge_partial_success.py`

**Interfaces:**
- Consumes: reviewed Script/Research/Material, Production Plan/Manifest/QA, Clean A-roll and configured provider.
- Produces: `EditBridgeWorkflowResult`; `run_edit_bridge_workflow(inputs, provider, roots, clock, id_factory) -> EditBridgeWorkflowResult`.

- [ ] **Step 1: Write failing E2E orchestration test with deterministic provider**

```python
def test_one_missing_image_keeps_other_placements_and_preview(self):
    result = run_edit_bridge_workflow(self.inputs, self.provider, self.roots, self.clock, self.ids)
    self.assertEqual(result.qa["package_gate_status"], "warnings")
    self.assertTrue(result.preview_path.is_file())
    self.assertEqual(result.summary.ready_count, 2)
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_workflow tests.test_edit_bridge_partial_success -v`

Expected: FAIL because workflow is missing.

- [ ] **Step 3: Implement orchestration without owning algorithms/Gate**

Call Tasks 3–25 in root order, persist every successful immutable artifact, isolate local material failures, render only when video A-roll and at least base layer are valid, and always write JSON/MD/CSV/QA when roots permit. Audio-only produces marker package + warning and no full Preview. A changed A-roll starts new downstream chain. No provider/renderer choice is exposed to ordinary user.

- [ ] **Step 4: Run green workflow tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_workflow tests.test_edit_bridge_partial_success -v`

Expected: PASS for video, audio-only, no-audio fail, partial material failure, segment-only no overlay, selection blocker and immutable rerun.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/edit_bridge_workflow.py tests/test_edit_bridge_workflow.py tests/test_edit_bridge_partial_success.py
git commit -m "feat: orchestrate aligned rough cut workflow"
```

### Task 27: CLI, Skill and ordinary-user UX

**Files:**
- Modify: `src/deeptalk_studio/cli.py`
- Create: `.agents/skills/align-video/SKILL.md`
- Create: `.agents/skills/align-video/references/edit-bridge-contract.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Create: `docs/EDIT_BRIDGE_CONTRACT.md`
- Test: `tests/test_edit_bridge_cli.py`
- Test: `tests/test_align_video_skill.py`

**Interfaces:**
- Consumes: Task 26 workflow and Task 21 revision resolver.
- Produces: internal `align-video`/`revise-edit-bridge` CLI commands and natural-language Skill routing.

- [ ] **Step 1: Write failing UX tests**

```python
def test_missing_real_aroll_stops_at_one_simple_user_action(self):
    result = run_cli("align-video", "--session", str(self.session))
    self.assertIn("把已经剪好口气的正式真人口播视频拖进来", result.stdout)
    self.assertNotIn("provider", result.stdout.casefold())
    self.assertNotIn("JSON", result.stdout)
```

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_cli tests.test_align_video_skill -v`

Expected: FAIL because CLI/Skill entrypoints are absent.

- [ ] **Step 3: Implement hidden-parameter entry and six semantic intents**

Skill recognizes “我视频剪好了 / 这是口播视频 / 帮我把素材卡进去 / 给我生成粗剪 / 这张截图时间太长 / 关系图晚一点”. It resolves current approved roots automatically and never asks for provider, algorithm, Beat/Cue/Scene ID, path or timestamp. When no real Clean A-roll exists, output exactly the Design Gate text; after output, ask only to watch rough cut. CLI remains technical test plumbing but catches domain errors without traceback.

- [ ] **Step 4: Run green CLI/Skill validation**

Run: `PYTHONPATH=src python3 -m unittest tests.test_edit_bridge_cli tests.test_align_video_skill tests.test_cli -v`

Run: `python3 /Users/hwang/.codex/skills/.system/skill-creator/scripts/quick_validate.py .agents/skills/align-video`

Expected: all PASS; ordinary text contains no internal IDs/paths/provider/JSON instruction.

- [ ] **Step 5: Commit**

```bash
git add src/deeptalk_studio/cli.py .agents/skills/align-video AGENTS.md README.md docs/ARCHITECTURE.md docs/EDIT_BRIDGE_CONTRACT.md tests/test_edit_bridge_cli.py tests/test_align_video_skill.py
git commit -m "feat: add ordinary user aligned video workflow"
```

### Task 28: Full A–AI eval, real provider smoke Gate and real-user E2E stop

**Files:**
- Create: `evaluations/audio-alignment-edit-bridge/run_full_eval.py`
- Create: `evaluations/audio-alignment-edit-bridge/case-manifest.json`
- Create: `evaluations/audio-alignment-edit-bridge/summary-schema.json`
- Create: `tests/test_alignment_media_eval.py`
- Create: `tests/test_alignment_transcript_eval.py`
- Create: `tests/test_alignment_material_eval.py`
- Create: `tests/test_alignment_placement_eval.py`
- Create: `tests/test_alignment_preview_eval.py`
- Create: `tests/test_alignment_revision_eval.py`
- Create: `tests/test_alignment_invariants.py`
- Create: `tests/test_openai_transcription_smoke.py`
- Modify: `PRD.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `HANDOFF.md`

**Interfaces:**
- Consumes: completed Tasks 1–27.
- Produces: deterministic A–AI result groups, provider smoke record, full verification record and real-user Gate; it does not claim real-user E2E pass.

- [ ] **Step 1: Write failing manifest coverage/invariant tests**

```python
def test_every_approved_case_has_one_owned_test_group(self):
    manifest = load_case_manifest()
    self.assertEqual(set(manifest), set(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI"]))
```

- [ ] **Step 2: Run red grouped eval tests**

Run: `PYTHONPATH=src python3 -m unittest tests.test_alignment_media_eval tests.test_alignment_transcript_eval tests.test_alignment_material_eval tests.test_alignment_placement_eval tests.test_alignment_preview_eval tests.test_alignment_revision_eval tests.test_alignment_invariants -v`

Expected: FAIL until every A–AI case and invariant has an executable owner.

- [ ] **Step 3: Complete grouped synthetic/adversarial evidence**

Assign A–AI across media/timebase, transcript/alignment, material bridge, placement, duration/conflict, preview/QA and revision files. Property tests assert stable digests, monotonic/in-bounds mapped time, fps-neutral canonical time, unplaced null timestamps, warning-ready orthogonality, selection-blocker exclusion, ready-only Preview back-links, long-still semantic preservation and single-field tamper detection. Run real ffmpeg fixtures for L/M/AA–AE and actual probe/decode; do not commit user media or large binaries.

- [ ] **Step 4: Define and run the explicit real-provider smoke only when authorized**

`tests/test_openai_transcription_smoke.py` is skipped unless `DEEPTALK_RUN_OPENAI_TRANSCRIPTION_SMOKE=1`, `OPENAI_API_KEY` exists and `DEEPTALK_TRANSCRIPTION_SMOKE_MEDIA` points to a local synthetic <25 MB WAV. It invokes `whisper-1` word timestamps, records provider/model/granularity/request metadata and validates Mapping → Timed Transcript; it never prints key/path/raw audio and never commits response/media. API/network/key failure is recorded as environment unavailable, distinct from product validation failure. Run during implementation:

`DEEPTALK_RUN_OPENAI_TRANSCRIPTION_SMOKE=1 PYTHONPATH=src python3 -m unittest tests.test_openai_transcription_smoke -v`

Expected: PASS before asking for real-user E2E; an unavailable environment blocks provider validation but does not falsify synthetic results.

- [ ] **Step 5: Run full implementation verification**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -v`

Run: `PYTHONPATH=src python3 evaluations/audio-alignment-edit-bridge/run_full_eval.py --verify-repeat`

Run: `npm --prefix renderer_templates/aligned_preview_remotion run lint && npm --prefix renderer_templates/aligned_preview_remotion run typecheck`

Run: `rg -n "silenceremove|pause shortening|filler-word removal|auto.*cleanup|backgroundMusic|subtitle|publish" src/deeptalk_studio renderer_templates/aligned_preview_remotion .agents/skills/align-video`

Expected: all tests/evals/lint/typecheck pass; scope scan shows only explicit prohibitions/docs, not implementation. Synthetic Preview render is evidence for renderer regression only.

- [ ] **Step 6: Stop at the real-user Gate and update records**

Do not create a Release or declare V1.0. `HANDOFF.md` must tell the user only:

```text
【现在你只需要做】

把已经剪好口气的正式真人口播视频拖进来。
mp4 / mov 都可以。

不需要另外录音。
不需要自己提取音轨。
不需要标记时间点。
```

Only after that real Clean A-roll + existing reviewed Material + existing Motion produce a QA-gated `ALIGNED_PREVIEW.mp4`, and the user watches it, may the user answer “对齐通过” or ordinary visual feedback.

- [ ] **Step 7: Commit implementation evidence, not private media**

```bash
git add evaluations/audio-alignment-edit-bridge tests PRD.md ROADMAP.md CHANGELOG.md HANDOFF.md
git commit -m "test: verify audio alignment edit bridge"
```

---

## Plan self-review checklist

- [ ] **Spec coverage:** map Design §§1–32 and review requirements A–AI to Tasks 1–28; no approved schema, Gate, source kind, output or recovery path lacks an owner.
- [ ] **Placeholder scan:** search the Plan with the repository text-search tool for the forbidden placeholder phrases listed by the Writing Plans workflow and require no implementation step to contain one.
- [ ] **Type/interface consistency:** run `rg -n "Produces:|Consumes:|def |->" docs/superpowers/plans/2026-08-13-audio-alignment-edit-bridge.md`; verify every consumed new function/type is produced by an earlier Task.
- [ ] **Test-first consistency:** each implementation Task has a failing-test step, exact red command/expected failure, minimal implementation, exact green command and commit boundary.
- [ ] **Dependency order:** no Task imports a module introduced later; renderer template follows validated Bridge/Profile and QA follows real Preview Manifest.
- [ ] **Scope:** no A-roll cleanup, subtitles, BGM/SFX, title/cover, auto publishing, NLE-specific exporter, auto B-roll selection or copyright approval UX.
- [ ] **Real E2E Gate:** synthetic, real-media fixture and provider smoke completion explicitly stop before real-user acceptance.
