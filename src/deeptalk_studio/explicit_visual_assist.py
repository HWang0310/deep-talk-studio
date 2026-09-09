"""Explicit generated visual assistant: invocation-scoped single-plugin selection.

This module implements the v1.0 user-facing entry point for explicitly requesting
one named visual family (MG / 小黑漫画 / 手绘动画) without automatic family selection,
winner ranking, or overlap resolution.

It reuses the existing Contract V1 plugin runtime and Candidate Portfolio
orchestration.  The only new behaviour is:

1. Resolve a user-facing alias to a canonical plugin id.
2. Build a single-plugin subset of the configured plugin config.
3. Delegate to the existing ``orchestrate_candidate_portfolio``.
4. Summarise the result in a concise creator-facing structure.

No new plugin orchestration, no Contract changes, no pin changes, no auto-edit.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping, Sequence

from .candidate_portfolio import orchestrate_candidate_portfolio
from .visual_generation_policy import generation_policy_digest
from .visual_plugin_config import normalize_visual_plugin_config


# ---------------------------------------------------------------------------
# Alias → canonical plugin id
# ---------------------------------------------------------------------------
VISUAL_FAMILY_ALIASES: dict[str, str] = {
    "mg": "org.deeptalk.mg",
    "xiaohei": "org.deeptalk.illustrated-metaphor",
    "handdrawn": "org.deeptalk.handdrawn-animation",
}


class ExplicitVisualAssistError(ValueError):
    """The explicit visual-assist boundary was violated."""


def resolve_visual_family(alias: str) -> str:
    """Map a user-facing alias to a canonical plugin id.

    Raises ``ExplicitVisualAssistError`` for unknown aliases.
    """
    if not isinstance(alias, str) or not alias.strip():
        raise ExplicitVisualAssistError("visual family alias 不能为空")
    key = alias.strip().casefold()
    plugin_id = VISUAL_FAMILY_ALIASES.get(key)
    if plugin_id is None:
        raise ExplicitVisualAssistError(f"未知的视觉素材类型：{alias}")
    return plugin_id


# ---------------------------------------------------------------------------
# Single-plugin subset
# ---------------------------------------------------------------------------
def _single_plugin_subset(
    plugin_config: Mapping[str, Any], target_plugin_id: str,
) -> dict:
    """Return a config with only the target plugin enabled; all others disabled.

    This does NOT remove other plugins from the config (which would change
    ``config_digest`` and break lineage).  Instead it sets ``enabled: false``
    on every non-target plugin, so the existing orchestration runtime naturally
    skips them.
    """
    normalized = normalize_visual_plugin_config(plugin_config)
    found = False
    plugins = []
    for plugin in normalized["plugins"]:
        if str(plugin["plugin_id"]) == target_plugin_id:
            found = True
            if not plugin.get("enabled", False):
                raise ExplicitVisualAssistError(
                    f"插件 {target_plugin_id} 已被禁用 (disabled)，无法通过显式调用启用"
                )
            plugins.append(copy.deepcopy(plugin))
        else:
            cloned = copy.deepcopy(plugin)
            cloned["enabled"] = False
            plugins.append(cloned)
    if not found:
        raise ExplicitVisualAssistError(
            f"插件 {target_plugin_id} 未在当前配置中找到 (not configured)"
        )
    return {"config_version": normalized["config_version"], "plugins": plugins}


# ---------------------------------------------------------------------------
# Opportunity validation
# ---------------------------------------------------------------------------
def _validate_opportunity(opportunity: Any) -> Mapping[str, Any]:
    """Ensure the opportunity is a non-empty Mapping with required fields."""
    if opportunity is None:
        raise ExplicitVisualAssistError("缺少 Visual Opportunity")
    if isinstance(opportunity, list):
        if not opportunity:
            raise ExplicitVisualAssistError("Visual Opportunity 列表为空")
        opportunity = opportunity[0]
    if not isinstance(opportunity, Mapping):
        raise ExplicitVisualAssistError("Visual Opportunity 格式无效")
    required = ("opportunity_id", "a_roll_window", "visual_purpose")
    for field in required:
        if field not in opportunity:
            raise ExplicitVisualAssistError(f"Visual Opportunity 缺少必填字段：{field}")
    return opportunity


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------
def run_explicit_visual_assist(
    opportunity: Any,
    plugin_config: Mapping[str, Any],
    alias: str,
    *,
    production_profile: str,
    policy: Mapping[str, Any],
    job_root: Path,
    visual_opportunity_plan_digest: str,
    task_id: str = "UNSPECIFIED",
    request_namespace: str | None = None,
) -> dict:
    """Run exactly one explicitly selected visual plugin and return a summary.

    Parameters
    ----------
    opportunity
        A single Visual Opportunity dict (or a 1-element list).
    plugin_config
        The committed visual-asset-plugin config (``visual-asset-plugin-config/1``).
    alias
        User-facing family alias: ``mg``, ``xiaohei``, or ``handdrawn``.
    production_profile
        ``LEAN``, ``STANDARD``, or ``RICH``.
    policy
        Candidate generation policy artifact.
    job_root
        Working directory for plugin subprocess runs.
    visual_opportunity_plan_digest
        SHA-256 hex digest of the Visual Opportunity Plan.
    task_id
        Caller task identifier for audit trail.

    Returns
    -------
    dict with keys:
        - ``alias``: the original alias
        - ``plugin_id``: resolved canonical plugin id
        - ``portfolio``: the full ``candidate-portfolio/1`` artifact
        - ``summary``: creator-facing summary (status, reason, candidates)
    """
    # 1. Resolve alias
    plugin_id = resolve_visual_family(alias)

    # 2. Validate opportunity
    opp = _validate_opportunity(opportunity)

    # 3. Validate plan digest
    if not isinstance(visual_opportunity_plan_digest, str) or not visual_opportunity_plan_digest.strip():
        raise ExplicitVisualAssistError("visual_opportunity_plan_digest 不能为空")

    # 4. Build single-plugin subset
    subset_config = _single_plugin_subset(plugin_config, plugin_id)

    # 5. Delegate to existing orchestration
    opportunities = [opp] if isinstance(opp, Mapping) else list(opp)
    portfolio = orchestrate_candidate_portfolio(
        opportunities,
        subset_config,
        production_profile=production_profile,
        policy=policy,
        job_root=Path(job_root),
        visual_opportunity_plan_digest=visual_opportunity_plan_digest,
        task_id=task_id,
        request_namespace=request_namespace,
    )

    # 6. Summarise
    return {
        "alias": alias.strip().casefold(),
        "plugin_id": plugin_id,
        "portfolio": portfolio,
        "summary": _summarise(portfolio, plugin_id),
    }


def _summarise(portfolio: Mapping[str, Any], plugin_id: str) -> dict:
    """Build a concise creator-facing summary from the portfolio artifact."""
    all_candidates = []
    plugin_records_by_id: dict[str, dict] = {}

    for opp_entry in portfolio.get("opportunities", []):
        for candidate_entry in opp_entry.get("candidates", []):
            if candidate_entry.get("plugin_id") == plugin_id:
                acceptance = candidate_entry.get("core_acceptance", {})
                candidate = candidate_entry.get("plugin_candidate", {})
                all_candidates.append({
                    "candidate_id": candidate.get("candidate_id"),
                    "candidate_status": candidate.get("candidate_status"),
                    "core_acceptance": acceptance.get("status", "REJECTED"),
                    "plugin_id": candidate_entry.get("plugin_id"),
                    "duration_ms": candidate.get("duration_ms"),
                })

    ready_accepted = [c for c in all_candidates if c["candidate_status"] == "READY" and c["core_acceptance"] == "ACCEPTED"]

    # Check audit records for this plugin to determine overall status
    audit_for_plugin = [a for a in portfolio.get("audit_records", []) if a.get("plugin_id") == plugin_id]
    has_failed = any(
        (a.get("execution") and a["execution"].get("status") == "FAILED")
        or (a.get("raw_response") and a["raw_response"].get("operation_status") == "FAILED")
        for a in audit_for_plugin
    )
    has_abstain = any(
        a.get("raw_response") and a["raw_response"].get("suitability") == "ABSTAIN"
        for a in audit_for_plugin
        if a.get("operation") == "suitability"
    )

    if ready_accepted:
        status = "READY"
        reason = f"插件 {plugin_id} 已生成 {len(ready_accepted)} 个可用素材候选"
    elif has_abstain:
        status = "NO_CANDIDATE"
        reason = f"插件 {plugin_id} ABSTAIN：该插件判断此 Visual Opportunity 不适合其能力范围"
    elif has_failed:
        status = "FAILED"
        reason = f"插件 {plugin_id} 执行失败"
    else:
        status = "NO_CANDIDATE"
        reason = f"插件 {plugin_id} 未生成任何 READY 且通过 Core 验收的候选"

    return {
        "status": status,
        "reason": reason,
        "candidates": ready_accepted,
    }
