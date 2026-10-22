"""Workbench script profile: the V1 content-driven profile (Issue #21).

The unified workbench always writes thesis-bound, content-driven scripts, so
it pins ``config/script-profile-v1.json`` instead of the legacy 0.4 default.
"""

from pathlib import Path
from typing import Dict, Optional

from ..script_profile import load_script_profile

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_SCRIPT_PROFILE = REPO_ROOT / "config" / "script-profile-v1.json"


def load_workbench_script_profile(path: Optional[Path] = None) -> Dict[str, object]:
    profile = load_script_profile(path or WORKBENCH_SCRIPT_PROFILE)
    if str(profile["profile_version"]) != "1":
        raise ValueError("工作台写稿必须使用 V1 内容驱动档位")
    return profile
