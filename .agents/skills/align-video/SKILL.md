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

For a real run, call `resolve_real_edit_bridge_session(...)` and then the single `run_real_edit_bridge_session(...)` production entrypoint. It owns immutable import, evidence-preserving transcription audio, Mapping, Chunk Plan, timestamp-capable transcription, Alignment, Basic Subtitle V1 Artifact/SRT, Material projection, Placement timing, Edit Bridge, burned-in subtitled Preview, original Clean A-roll audio mux, Manifest and canonical QA. Never assemble stage lambdas, interpolate segment timestamps, disable the bound subtitles, mix B-roll audio, or modify reviewed history.

For natural-language timing feedback, call `load_real_edit_bridge_session_result(...)` and `revise_real_edit_bridge_session(...)`. Resolve by readable filename/caption/Beat neighborhood. Every new Preview revision must keep the exact current Subtitle Artifact/Transcript binding and burned-in subtitles. Shorter/longer/earlier/later feedback changes effective preview timing; “一直留真人” suppresses only that overlay. Always create new Bridge, Preview, Manifest and QA revisions for one unique match. If ambiguous, show 2–3 readable visual names and ask which picture; never expose internal IDs.
