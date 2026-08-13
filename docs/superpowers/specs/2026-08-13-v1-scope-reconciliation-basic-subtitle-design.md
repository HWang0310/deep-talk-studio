# V1 Scope Reconciliation + Basic Subtitle Design

**Status:** Approved product direction, Unreleased implementation design

**Starting branch:** `agent/audio-alignment-edit-bridge`

**Starting HEAD:** `20da05231520aafe1b4d89fb2c95b9143521c9df`

## Goal

Preserve the reviewed Audio Alignment + Visual Edit Bridge architecture while restoring the confirmed V1 outcome: a Clean A-roll-led rough cut that already contains real Material, Original Motion and burned-in basic subtitles. The same internal Bridge remains the editable source for ordinary-language visual revisions.

## Scope

This change contains two bounded parts:

1. Reconcile the existing Script contract with the V1 Hook requirement.
2. Add Basic Subtitle V1 from the canonical Timed Transcript through renderer, immutable outputs and repository-owned QA.

It does not add A-roll cleanup, BGM, SFX, title/cover, publishing, karaoke, retention prediction, NLE-specific export or a real-user run.

## Hook-aware Script decision

The existing Script artifact already has the necessary stable representation: `audience_promise`, ordered Beats with `purpose`, narration content and `closing`. A second Hook schema would duplicate those fields and invalidate mature Script history.

The gap is semantic enforcement. The Script Profile, Writer instructions and independent `narrative_structure` review will explicitly require:

- an opening hook grounded in a real question, evidence contrast or consequence;
- a clear value promise or curiosity gap;
- an evidence-grounded mid-script re-hook / information turn when the length needs it;
- a conclusion payoff that answers or productively resolves the opening promise.

The existing `narrative_structure` check remains the review dimension. A new typed `hook_structure` finding under that check is blocking for newly reviewed scripts. Existing reviewed Script artifacts using consistency mapping `0.4.1` remain loadable; new reviews use `0.4.2`. No Script Draft schema or artifact version changes.

## Subtitle artifact

Create `subtitle-artifact/1`, derived only from one validated `timed-transcript/1` and `subtitle-profile/1`. It binds the exact Media ID/SHA, Transcript ID/revision/digest and profile digest. Each cue contains machine-owned ID/order, exact media IN/OUT, normalized display text, source unit IDs and honest precision (`word` or `segment`). The artifact has a deterministic digest and an SRT reading/export representation.

Word/token transcripts may group consecutive real units by punctuation, pause, duration and capacity. Cue boundaries must remain the first and last real unit timestamps. Segment transcripts remain one cue per real segment and are marked coarse; no word interpolation or karaoke precision is created.

Display normalization is intentionally narrow: Unicode normalization, whitespace cleanup, Chinese/Latin spacing and punctuation typography. It may not paraphrase, add words or repair meaning.

## Subtitle profile and safe area

`subtitle-profile/1` is a single versioned 1920x1080 Bilibili profile. It reserves a global lower region for at most two centered lines, with a high-contrast plate, readable mobile size and no per-word animation. All visual overlays are confined to the content region above that reservation. Clean A-roll remains full frame beneath the subtitle layer.

The renderer consumes the same subtitle artifact and profile for A-roll, image, video and Original Motion periods, so narration subtitles continue across visual switches. Motion and other overlays cannot independently reposition subtitles or occupy the reserved subtitle information area.

## Formal production integration

The single `run_real_edit_bridge_session` owner builds and validates subtitles immediately after Timed Transcript construction. Subtitle and profile digests enter Edit Bridge root bindings. The Remotion project receives controlled subtitle JSON/profile data, burns the active cue over the whole composition and reports `subtitles_enabled=true`.

Aligned Preview Manifest binds the subtitle artifact digest, transcript digest, profile digest and renderer-enabled state. Immutable subtitle JSON and SRT are saved with the other session artifacts.

Natural-language Bridge revisions do not regenerate transcript-derived wording. They revalidate the bound subtitle artifact and render the new visual Bridge with the same current subtitle artifact. A changed Transcript revision/digest invalidates the old subtitle and all downstream Preview binding.

## Canonical QA

Repository-owned QA adds subtitle validation without accepting caller-owned pass flags. It checks:

- exact Media and Transcript binding;
- profile binding and artifact digest;
- non-empty text, monotonic timestamps, `IN < OUT`, and bounds within Clean A-roll;
- segment transcripts cannot claim word precision;
- Bridge root binding and Preview Manifest binding;
- renderer project actually enables the current subtitle artifact;
- final video retains one unchanged Clean A-roll primary audio presentation.

Binding, timing, digest, tamper or renderer-disable failures are blocking. Purely local visual readability observations may remain warnings during real-user review.

## Verification

Targeted tests cover word timing, segment fallback, continuous subtitles across A-roll/image/Motion, reserved Motion area, changed Transcript invalidation, tampering, real renderer enablement, natural-language revision persistence, unchanged audio and existing Placement regression. The exact production entrypoint then runs a real synthetic Remotion render, ffprobe and canonical QA. Real provider and real-user E2E remain separately reported.

