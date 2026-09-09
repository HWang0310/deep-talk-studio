---
name: align-video
description: Use when the user says their Final Clean A-roll is ready, asks to align reviewed materials/Motion to the real narration, generate an Asset Pack + Edit Map, or revise one compatibility preview visual in ordinary language.
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

For a real run, first enforce the Final Clean A-roll Gate. If it clearly contains whole retakes/multiple takes, ask only for manual cleanup and stop; never choose a take, produce a cut list, or change the media. V1 automatically prepares and uses repository-owned local `whisper.cpp` v1.9.2 full multilingual `large-v3` with `--dtw large.v3`; no API Key, provider, model or renderer choice is exposed to the normal user. The primary delivery is `Actual Transcript → global Alignment → Semantic Timeline → Visual Director → individual asset QA → Asset Pack + Markdown/CSV/machine Edit Map`; all formal timing derives from Final Clean A-roll, never estimated Script timing. Full Remotion Preview remains a compatibility/QA route only. Facts remain bound to approved Research/reviewed Script; a `FACT_CONFLICT` records real time and blocks wrong display content without changing audio. Never assemble stage lambdas, interpolate segment timestamps, modify reviewed history, mix B-roll audio into A-roll, or create a final edited video/NLE project.

For natural-language timing feedback, call `load_real_edit_bridge_session_result(...)` and `revise_real_edit_bridge_session(...)`. Resolve by readable filename/caption/Beat neighborhood. Every new Preview revision must keep the exact current Subtitle Artifact/Transcript binding and burned-in subtitles. Shorter/longer/earlier/later feedback changes effective preview timing; “一直留真人” suppresses only that overlay. Always create new Bridge, Preview, Manifest and QA revisions for one unique match. If ambiguous, show 2–3 readable visual names and ask which picture; never expose internal IDs.
