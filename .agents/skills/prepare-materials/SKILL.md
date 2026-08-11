---
name: prepare-materials
description: Use when the user says “给这期配素材”, “把画面准备一下”, asks for fewer or more visuals for a reviewed DeepTalk Script, or wants a source-backed Material Package, cue sheet, rights check, screenshots, public assets, or original charts before video production.
---

# Prepare Materials

Turn the latest genuinely reviewed Script into a source-backed Material Package and independently review it. Read `references/material-contract.md` completely before starting. Do not ask a normal user to manage paths, JSON, IDs, commands, copyright terminology, or render settings.

## Input Gate

1. Find the latest Script whose V0.4.1 Review linkage can be reopened and validated. Load its exact `report_id + report_revision` Research Report.
2. Run the existing validator before any search or file write. Reject draft scripts, hand-edited `reviewed` fields, missing/fake Review Artifacts, digest mismatches and wrong Research revisions.
3. Interpret “少一点素材”“只配关键段落” as fewer high-priority Cues. Interpret “多一点画面”“信息密一点” as more useful Cues, not one forced Cue per Beat or duplicate candidates.

## Search and Inspection

1. Build short exact narration anchors, not audio timecodes. Give a Cue only where an auxiliary visual materially helps.
2. Search official documents, public datasets, press assets, pages, photos, video references and archives. Open every page used in the Package. A search result summary is not inspection.
   必须实际打开页面；只看到搜索摘要不能登记为 inspection。
3. In the background, write a separate inspection manifest containing only actually opened URLs, inspection time, method and tool reference. Record a separate rights manifest only after opening the page that provides the reuse basis.
4. Keep evidence, context, illustration and transition distinct. Evidence materials bind valid Claim and Evidence Link IDs. Illustration is always `illustrative_only` and cannot prove a factual claim.
5. If a page contradicts, updates or materially changes the approved Research, add a `research_update_signal` with affected Beat/Claim/reason/URL. Stop silent updating: do not change the script, Research or chart data.
6. Treat ordinary news pages, videos and creator content as `reference_only` unless explicit reuse terms say otherwise. Never infer permission from a publisher name.

## Acquisition and Original Visuals

1. Automatically save only files whose real inspection and rights records produce `ready_to_use`. Do not bulk-download news/video/creator materials. Do not bypass login, paywall, DRM, anti-bot, rate limits or platform restrictions.
2. For a webpage/PDF screenshot, capture only the useful region or relevant page. Record page/context/crop/caption, what it proves and what it does not prove. Register the static local capture through the project acquisition boundary.
3. Keep video as a reference with page, publisher, title, suggested start/end and reason unless reuse permission clearly allows download.
4. Generate timeline, bar, comparison or diagram Visual Specs only from the exact approved Research. Run the grounding validator, then render actual 1920×1080 SVG files. Never invent numbers, events, documents, chats, UI, news imagery, people or event scenes.
5. Keep Remotion / HyperFrames as future target hints. Do not create a full composition, video, edit timeline, subtitle, music, cover or publishing task.

## Independent Material Review

Start a separate Review pass after the Package and SVG files exist. Reopen listed URLs if needed, but do not expand Research or add candidates. Check provenance, Claim alignment, rights, crop context, freshness, identity, generated data, AI/real confusion, duplicates and usefulness. Every failed check needs its typed issue. Let the Python core derive severity, isolate unsafe items and decide the package status.

这是独立 Material Review，不能扩展 Research。

Use:

```bash
./scripts/deeptalk prepare-materials <report.json> <reviewed-script.json> <material-content.json> --inspection-manifest <inspection.json> --rights-manifest <rights.json>
./scripts/deeptalk review-materials <report.json> <reviewed-script.json> <material-package.json> <material-review.json>
```

## Return to the User

Show only the short reading view: number of Cues, how many items are ready, reference-only or permission-required, how many original visuals were generated, important gaps, and whether Research must be updated. Do not expose raw JSON, machine IDs, internal paths or commands. If usable, say the画面准备单已完成；if blocked, explain in plain Chinese what category of source or permission is missing.

## Hard Boundaries

- Material Search cannot become a new Research pass.
- A model cannot self-certify provenance, rights, ranking, local files or Review Gate.
- Unknown rights never means ready to use.
- Search snippets, thumbnails and mirrored URLs do not prove page inspection or independent alternatives.
- Do not imitate another creator’s visual language or collect their script/subtitles.
- Do not present AI-generated visuals as real evidence.
