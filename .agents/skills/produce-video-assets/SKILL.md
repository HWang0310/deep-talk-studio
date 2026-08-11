---
name: produce-video-assets
description: Use when the user says “生成视频素材”, “做一下动画”, “出一个粗剪预览”, asks to turn the latest reviewed DeepTalk Studio Material Package into motion assets, or requests Remotion / HyperFrames production, renderer comparison, production QA, or production gaps.
---

# Produce Video Assets

Turn one canonical V0.5.1 Material Package into real motion clips, a rough visual preview, a hero still, a Motion Asset Manifest and Production QA. Do not ask a normal user to find paths, choose technical settings, read JSON or run commands.

## Resolve Inputs

1. Read repository `AGENTS.md`, `HANDOFF.md` and `docs/PRODUCTION_CONTRACT.md`.
2. Find the newest immutable Material Package revision with status `reviewed` or `reviewed_with_warnings` under `material_packages/`.
3. Resolve its exact reviewed Script and approved Research Report from the package bindings. Use the existing canonical loaders; never trust a hand-edited status or reconstruct missing history.
4. Stop in plain Chinese if the package is blocked, requests a Research update, has invalid review linkage, or its saved asset SHA no longer matches.

## Produce

Run one ordinary production with the profile-selected renderer:

```bash
./scripts/deeptalk produce-assets <report.json> <reviewed-script.json> <reviewed-material-package.json> --renderer auto
```

Use only one renderer for a normal request. Use both renderers only when the user explicitly asks for comparison or when executing a formal cross-renderer evaluation. Never put reference-only, permission-required, rejected, missing or SHA-mismatched assets into a composition.

Allow the core workflow to create the Production Plan, renderer project, preview, real renders, Manifest and QA. Do not alter machine IDs, digests, file metadata or Gate outcomes by hand. Do not silently overwrite an earlier run.

## Inspect Results

1. Reopen the saved Production QA and Motion Asset Manifest.
2. Report an asset as usable only when it appears in the Manifest and its QA clip result is `ready`. Report rough preview success only when `MAPREVIEW` itself is present and ready.
3. Treat package Gate `fail` as blocked. Treat `warnings` as partial success and list the exact missing clips in ordinary language.
4. Mention Production gaps, especially missing real voice timing, missing lawful imagery or retained A-roll placeholders.

## Return to the User

Return only a short Chinese reading view:

- how many animation assets are ready;
- whether the rough visual preview exists;
- what still needs manual footage, permission or timing;
- which renderer was actually used;
- whether the run passed Production QA.

Provide clickable paths only for the rough preview and final readable QA if useful. Do not dump JSON, terminal logs, commands, IDs or dependency details unless asked.

## Hard Boundaries

- Produce auxiliary visuals, not a fake host, synthetic witness, fabricated event scene or fake document.
- Do not add TTS, final A-roll edit, subtitle system, BGM, title, cover, publishing or platform upload in V0.6.
- Except for the versioned machine-editorial allowlist, every displayed factual phrase must be semantically grounded in approved Research bindings even when it contains no number.
- Never stage or render raw PDF. Use only a V0.5-reviewed PNG/JPEG/WebP capture with capture provenance; otherwise return the fixed document screenshot gap.
- timeline/bar/comparison/diagram must animate independent elements from `scene_payload`; never animate the complete V0.5 SVG as one image.
- A failed typed renderer check must create a blocking package issue; never reinterpret it as pass.
- A renderer success message is not QA; real files must pass file, metadata, duration, size and digest checks.
- Preserve immutable storage and create a new Production run instead of replacing an old one.
