# V1 Large-v3 Long-form Transcription Design

**Approval source:** ChatGPT Local Transcription Production Integration Review, 2026-08-14.

## Goal

Make full-precision `ggml-large-v3.bin` the sole V1 default local transcription model. Retain the no-key local production path and obtain truthful 272-second long-form evidence before allowing the real-user Clean A-roll Gate to open.

## Product decision

V1 optimizes recognition quality, not download size, storage, inference time, CPU/GPU use, or memory use. The production default is the official ggerganov/whisper.cpp full multilingual `large-v3` model only. `medium`, `large-v3-turbo`, quantized variants, cloud providers, VibeASR, forced alignment, dictionary correction, LLM correction, and model-selection UI are outside this scope. Historical medium Selection Gate artifacts remain immutable historical evidence.

## Runtime and provenance contract

The pinned runtime remains whisper.cpp v1.9.2 at source commit `306c88f4d1286aec1bf96e544632897886af5501`. The official v1.9.2 CLI source maps `--dtw large.v3` to `WHISPER_AHEADS_LARGE_V3`; therefore large-v3 runs must use exactly that preset. The bootstrap downloads `ggml-large-v3.bin` to the project-external production cache, recomputes its SHA-256 and file size, and refuses the file unless both are exactly pinned:

- URL: `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin`
- expected SHA-256: `64d182b440b98d5203c4f9bd541544d84c605196c4f7b845dfa11fb23594d1e2`
- expected bytes: `3095033483`
- model identity: `large-v3`
- DTW preset: `large.v3`

The existing medium cache stays untouched. Every installation and transcript binds runtime version, runtime build identity, source commit, model identity, model SHA/bytes, `dtw`, Apple Silicon Metal status, chunk-plan digest, raw response digests, timestamp provenance and runtime/RTF.

## Token timing and overlap policy

`ProviderTranscript.timestamp_granularity` remains `token`. Raw offsets from whisper.cpp full JSON are immutable evidence. The provider continues to reject missing, out-of-range, non-monotonic or overlapping token timing. No offset is clipped, averaged, interpolated, sorted, deleted or replaced with segment timing.

The long-form evidence runner first executes large-v3 with `--dtw large.v3` on the same 272-second non-private audio used by the Selection Gate. If no overlap is observed, it runs the full production chain unchanged. If overlap appears, it writes a versioned external evidence artifact for every pair: chunk/segment IDs, raw token texts/offsets, overlap duration, unit order, boundary status, control token status, model/DTW/runtime and raw JSON digest. The Gate remains blocked. A future canonicalization is explicitly out of scope unless a later ChatGPT-approved contract proves the official DTW semantics and defines a separately derived, re-computable timeline while retaining raw evidence.

## Long-form production evidence

Use non-private synthetic Clean A-roll only. Run the existing single formal entrypoint without API keys and without deterministic/cloud substitution:

```text
Clean A-roll → local large-v3 token transcription → Timed Transcript → Alignment
→ reviewed Material → Motion → Basic Subtitle → Edit Bridge
→ full-length Remotion Preview → canonical QA
```

The render monitor records PID, elapsed time, periodic output growth and process liveness. It does not stop a healthy slow renderer solely because it is quiet. A stopped run must record the stage, last progress and process evidence. The final preview must preserve original Clean A-roll audio; only ready placements enter it, and existing reference-only sources remain absent.

## Tests and acceptance

Tests make `large-v3`/`large.v3` the production default, reject medium as the default configured model, verify large-v3 bootstrap digest behavior, verify command construction, preserve direct token timestamps, retain no-key/no-cloud behavior and retain overlap fail-closed behavior. Medium-only Selection Gate tests remain historical and unchanged.

The real-user Gate remains blocked unless the 272-second large-v3 run passes token timing, Timed Transcript and Alignment; the complete full-length E2E renders; canonical QA has zero blocking failures; and the full regression suite has zero failures. All work remains on `agent/audio-alignment-edit-bridge`, `V1.0 Candidate — Unreleased`; main, v0.6.1 and Releases stay unchanged.
