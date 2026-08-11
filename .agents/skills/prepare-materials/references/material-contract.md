# Material Package 0.5 operating contract

The complete public contract is `docs/MATERIAL_CONTRACT.md`. Before a run, enforce these machine boundaries:

- Input: reviewed Script 0.4 with valid V0.4.1 Review Artifact, exact bound Research revision, Material Profile 0.5.
- Runtime records: separate inspection and rights manifests. Only actual page opens enter inspection. Only actual reuse terms enter rights.
- Output: immutable Material Package JSON plus derived Markdown, local static assets, generated SVGs and independent Material Review Artifact.
- Roles: `evidence`, `context`, `illustration`, `transition`. Illustration always has `illustrative_only=true`.
- Eligibility: `ready_to_use`, `reference_only`, `permission_required`, `rejected`; code derives it from provenance and rights.
- New facts: set `research_update_required`; never update Script, Research or Visual data silently.
- Original visuals: timeline/bar/comparison/diagram, 1920×1080, source-backed IDs, attribution, safe area, duration, animation intent and future render hints.
- Review: inspect the existing package only; do not expand research. Unsafe items can be isolated if safe alternatives remain.

Runtime directories `material_packages/` and `material_assets/` are private and ignored by Git. Never publish full real packages or potentially restricted assets to the repository.

