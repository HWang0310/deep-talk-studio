---
name: write-script
description: Use when a DeepTalk Studio Research Report has passed its Quality Gate and the user explicitly says “确认，开始写稿”, “可以写了”, or “确认进入写稿”; also use when the user asks to revise, shorten, lengthen, tighten, clarify, or change the opening of an existing DeepTalk Script.
---

# Write Script

Turn one explicitly approved Research Report into an original Chinese oral script, challenge it in a separate Script Review pass, and return the clean Teleprompter version. Never search for new facts in this Skill.

## Required contract

Read `references/script-contract.md` completely before writing or revising. Load `config/script-profile.json`. Do not ask a normal user to edit JSON, provide paths, manage IDs, or run commands.

## Approval gate

1. Treat only an explicit instruction to start writing as approval, such as “确认，开始写稿”, “可以写了”, or “确认进入写稿”. “看看这个报告怎么样” is not approval.
2. Keep the user's exact confirmation text. In the background, create and save the next immutable Research revision with `approve-report`. Never overwrite the reviewed report and never route approval through an ordinary content revision.
3. Refuse to write unless the resulting report is `ready_for_script`, has a passing Quality Gate, completed Fact Check, approved approval Gate, non-empty confirmation, and `ready_for_script=true`.

## Writer pass

1. Read only the approved Research JSON and Script Profile. Do not browse, search, open external pages, or use Discovery Seeds as evidence.
2. Use `handoff_to_script_agent.recommended_angle` and `central_tension`. Cover every `must_keep_claim_id` where the structure allows. Never affirm an `avoid_claim`. Put unresolved `follow_up_research` in `research_gaps`; do not fill it from memory.
3. Write natural oral Chinese with a Research-grounded opening hook and value promise, a mid-script re-hook / information turn when needed, story movement, fair alternative explanation, original analysis, and a conclusion payoff that resolves the opening promise. Never invent or exaggerate facts for a hook. Avoid report prose and fixed “首先、其次、最后” templates.
4. Keep every Beat typed as `fact`, `attribution`, `analysis`, `transition`, or `question`. Facts use verified confirmed Claims. Statements, media reports, commentary, and unverified material use natural attribution. Analysis keeps its basis Claims and never masquerades as fact.
5. Never place Claim IDs, Evidence IDs, URLs, debug labels, or source numbers in narration. Never imitate a named creator; translate a style request into high-level traits such as shorter sentences, denser information, or stronger narrative movement.
6. Respect an explicit duration such as 8, 10, or 15 minutes. Default to about 12 minutes. This is an estimate, not measured playback time.
7. Save the model-owned content in an ignored working location and prepare Script Draft 0.4. If validation rejects grounding, fix the content rather than weakening the validator.

## Independent Script Review

1. Start a separate review pass after the Draft exists. Read only the approved Research Report and Script Draft. Do not browse or reuse the Writer's self-assessment.
2. Check the opening hook, value promise, necessary re-hook / information turn and conclusion payoff, plus unsupported facts, attribution, evidence-strength inflation, unverified-as-fact, avoid Claims, must-keep coverage, high-risk wording, uncertainty, analysis/fact separation, research-gap invention, perspective fairness, oral naturalness, repetition, density, AI report tone, originality risk, and usability. Missing Hook-aware structure must be a blocking `hook_structure` issue under `narrative_structure`.
3. Output only review content: issues, checks, reasons, and fixes. Every failed check needs its matching typed issue; factual safety failures need the matching blocking issue. Do not use `not_applicable` for factual safety checks. The Python core owns issue IDs, severity, blocking count, gate status, review linkage, and final Script status.
4. Apply and save the Review Artifact plus the next immutable Script revision. If blocking issues exist, keep `draft` and explain simply that the script still has factual-boundary problems. Do not present it as reviewed.

## Revisions

When the user says “更紧凑一点”, “开头换一个”, “缩到 8 分钟”, “做成 15 分钟”, or similar:

1. Load the latest Script and its exact approved `report_id + report_revision`.
2. Create new model-owned content from that same Research revision; never switch research underneath an existing script.
3. Create the next immutable Script revision with `revise-script`, then run a fresh independent Script Review. Do not ask the user to manage Beat IDs: the core preserves continuity automatically and uses an internal origin hint only when necessary.
4. Keep old revisions. Use `compare-script` internally when the user asks what changed.

## Return to the user

If Review passes, say the estimated duration and show the Teleprompter content directly. Mention material Research gaps only when they affect use. Do not expose commands, JSON, paths, IDs, or URLs to a normal user.

If Review fails, say how many factual-boundary issues remain and offer to revise from the Review. Do not show a Python traceback and do not call it ready.

## Boundaries

- Do not use Web Search in Writer or Reviewer.
- Do not create materials, images, video, charts, subtitles, editing plans, thumbnails, publishing titles, SEO, or publishing actions.
- Do not download creator scripts or subtitles, rewrite another script, imitate distinctive expression, or claim an internet-wide plagiarism score.
- Do not sacrifice factual completeness merely to hit an estimated duration.
