---
name: align-video
description: Use when the user says their Clean A-roll is ready, asks to align reviewed materials/Motion to the real narration, generate an aligned rough cut, or revise one visual's timing in ordinary language.
---

# Align Video

Use this Skill for these ordinary intents: “我视频剪好了”, “这是口播视频”, “帮我把素材卡进去”, “给我生成粗剪”, “这张截图时间太长”, “关系图晚一点”.

Read `AGENTS.md`, `HANDOFF.md` and `docs/EDIT_BRIDGE_CONTRACT.md`. Resolve the newest approved Research, reviewed Script, reviewed Material Package, Production Plan/Manifest/QA and current Clean A-roll automatically. Do not ask a normal user for paths, timestamps, model names, algorithms, renderer choices, Beat/Cue/Scene IDs or machine files.

If no real Clean A-roll video exists, stop with exactly one ordinary action:

```
把已经剪好口气的正式真人口播视频拖进来。
mp4 / mov 都可以。
不需要另外录音。
不需要自己提取音轨。
不需要标记时间点。
```

For a real run, import the video immutably, extract evidence-preserving transcription audio, build/revalidate Mapping and Chunk Plan, transcribe through the configured timestamp-capable adapter, build and validate Alignment/Edit Bridge, create a visual-only Preview, mux the original Clean A-roll audio presentation timeline, then run QA. Never clean pauses, interpolate segment timestamps, fabricate ready placements, mix B-roll audio, or modify reviewed Script/Research/Material history.

For natural-language timing feedback, resolve by readable filename/caption/Beat neighborhood. Create a Bridge revision only for one unique match. If ambiguous, show 2–3 readable visual names and ask which picture; never expose internal IDs.
