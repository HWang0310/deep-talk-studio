# Relocation-Safe Runtime Artifact Resolution Design

## Status and scope

This design implements the approved C1-PATH repair for Core-owned V1 artifact readers. It covers Motion Asset Manifest outputs, reviewed Material Package files, Material Capture Manifest records, and the current production chain consumed by `align-video`. It does not modify historical artifacts, plugin runners, visual-family implementations, release state, tags, or `main`.

## Root cause

V1 manifests record absolute paths as part of their digest-covered historical evidence. `resolve_real_edit_bridge_session()` currently chooses a qualifying Production Plan by filesystem mtime and immediately calls `validate_motion_manifest()`, which opens each recorded `output_path`. After moving the repository, those recorded paths correctly continue to describe the original workspace, but the files now exist under a different canonical repository root. Material Package generated-visual paths and Material Capture Manifest paths have the same historical/runtime mismatch.

## Runtime configuration and selection

Core reads an optional ignored machine-local `config/artifact-runtime.local.json`. The strict configuration names:

- the current canonical repository root;
- an allowlist of trusted historical repository roots; and
- an optional explicit `current_production_id`.

The configured canonical root must match the repository root supplied by the caller. The local file is not an artifact and is not committed. If an explicit production ID is present, `align-video` resolves exactly that qualifying plan. Without one, compatibility fallback orders qualifying plans by digest-covered artifact time/revision/identity/path, never filesystem mtime. A future immutable current-production index remains a separate architecture phase.

## Artifact identity and resolution

The resolver receives a historical recorded path plus a consumer-derived artifact-relative identity. It accepts the recorded path only when it is exactly beneath the configured canonical root or one configured historical root and exactly matches the required lineage:

- Motion: `production_assets/<production_id>/assets/<motion_asset_id>.<format>`;
- generated Material: `material_assets/<package_id>/generated/<visual_id>.<format>`;
- captured Material: `material_assets/<package_id>/captures/registered/<material_id>-capture.<format>`;
- acquired Material: `material_assets/<package_id>/acquired/<material_id>.<format>`.

The resolver then constructs the same controlled relative identity beneath the canonical root. It does not replace arbitrary string prefixes and does not write the resolved path into the historical artifact.

## Security and validation

Configuration, recorded paths, relative identities, and resolved paths fail closed. Core rejects relative recorded paths, `.`/`..`, unknown roots, wrong lineage or filename identity, absolute relative identities, missing files, non-files, symlinks in any canonical-path component, canonical-root escape, byte-size mismatch, and SHA-256 mismatch. Existing MIME/type and artifact digest validators continue to run.

Runtime consumers may expose a separate resolved-location observation in ephemeral production views or placements. Historical JSON bytes, manifest digests, package digests, capture-manifest digests, and plan/QA bindings remain calculated over their original recorded content.

## Consumer integration

- Motion validation accepts a resolver and validates each output through it while keeping `manifest_digest` unchanged.
- Material Capture loading validates original records and uses the resolver only as a runtime observation.
- Material Production View emits the verified canonical `local_path` plus the historical recorded path, and its own ephemeral digest covers that observation.
- Production asset validation/planning/staging can use the same resolver for reviewed Material packages after a workspace move.
- Edit Bridge planning and canonical QA use the resolver consistently so no later stage reopens the stale historical path.

## Testing

Sanitized temp-root tests first create immutable artifacts under a historical root, copy the workspace data to a new canonical root, remove the historical root, and prove successful replay without changing artifact bytes or historical digests. Negative coverage includes unknown roots, traversal, unexpected absolute paths, symlink escape, missing files, byte-size mismatch, SHA mismatch, identity mismatch, and manifest tampering. A local ignored configuration is used separately to replay the existing current production chain; no private Episode data is committed.
