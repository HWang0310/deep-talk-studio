"""Canonical Edit Bridge schema and complete rebuild comparison."""
from .edit_bridge_planner import build_edit_bridge
from .edit_bridge_schema import EDIT_BRIDGE_SCHEMA
from .validation import ReportValidationError,validate_json_schema

class EditBridgeValidationError(ValueError): pass

def validate_edit_bridge(bridge,root_bindings,placements,conflicts,adjustments,alignment_gaps):
    try: validate_json_schema(dict(bridge),EDIT_BRIDGE_SCHEMA)
    except (ReportValidationError,RuntimeError) as exc: raise EditBridgeValidationError(f"Edit Bridge schema 无效：{exc}") from exc
    expected=build_edit_bridge(root_bindings,placements,conflicts,adjustments,alignment_gaps,bridge_id=bridge["bridge_id"],created_at=bridge["created_at"],revision=bridge["revision"],previous_revision=bridge["previous_revision"])
    if dict(bridge)!=expected: raise EditBridgeValidationError("Edit Bridge 与受控根工件重建结果不一致")
