# Topic Candidate Set 0.3 Contract

The executable contracts are `DISCOVERY_RAW_JSON_SCHEMA`, `TOPIC_CANDIDATE_SET_JSON_SCHEMA`, and `RESEARCH_HANDOFF_BRIEF_JSON_SCHEMA` in `src/deeptalk_studio/schema.py`.

## Boundary

Discovery determines whether a topic is worth *researching*. It does not determine final facts, complete a Fact Check, or produce a Research Report. A Source Seed is a short public URL entry point for later research, not evidence that a claim is true.

## Raw input owned by the searching agent

The raw input has a `query`, `time_window_hours=72`, and `candidates`. Each candidate must include:

- editorial content: title, category, topic summary, why now, core tension, research question, shelf life;
- time: `event_started_at` and `latest_update_at` in ISO 8601;
- risk: `risk_level` and concrete `risk_notes`;
- deduplication: a stable `event_cluster_key` for the same underlying event;
- Preflight signals: anonymous rumor, public evidence, unsupported allegation, emotion-only, imitation dependency, fast-event flag and independent research direction count;
- five score assessments (0–5 plus explanation): researchability, depth conflict, freshness, channel fit, attention signal;
- 2–4 Source Seeds where possible: URL, publisher, date, source type and why useful;
- warnings and optional Creator attention summary.

Do not output a candidate ID, total score, eligibility decision, recommendation label, primary marker, generated timestamp, provenance status or Artifact identity. The core generates and validates them.

## Deterministic rules

- Weights: researchability 30, depth conflict 25, freshness 20, channel fit 15, attention signal 10. The core alone calculates `total_score`.
- Eligible stories start in the last 72 hours, or start within the last 14 days and have a substantive update in the last 72 hours.
- Recommendable candidates need public HTTP(S) Seeds from at least two distinct directions, including at least two qualified source types/directions such as official, primary, reliable media, academic or expert material.
- High/critical risk plus weak evidence is `watch`; it cannot be displayed in Top 5. Unsupported rumors and allegations are `rejected`.
- One event cluster occupies one display position. A category normally occupies no more than two positions. The top display candidate is the single primary recommendation.
- Creator signal is secondary and optional. It is never an Evidence Ledger source or a reason to imitate an individual creator.

## Research handoff

`select-topic` accepts `1` or `研究 1` against `discoveries/latest.json`. Its handoff contains title, research question, core tension, why now, risk notes, warnings and Source Seeds. Feed those into `research-topic` without asking the user to repeat a title. Start a fresh V0.2 Research Draft and independent Fact Check; do not reuse the discovery card as evidence.
