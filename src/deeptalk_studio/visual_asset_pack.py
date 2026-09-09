"""Package only QA-ready visual assets into creator-friendly folders."""
import hashlib
import json
from pathlib import Path


def build_manifest(assets):
    ready = [dict(x) for x in assets if x.get("qa_status") == "ready"]
    data = {"artifact_version": "visual-asset-manifest/1", "asset_count": len(ready), "assets": ready}
    data["manifest_digest"] = hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return data


def write_asset_pack(root, manifest):
    root = Path(root); edit = root / "09_剪辑表"; technical = root / "_DeepTalk记录"
    for name in ("06_真实素材", "07_MG动画", "08_高级动画", "09_剪辑表", "_DeepTalk记录"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (technical / "visual-asset-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"root": root, "edit_dir": edit, "technical_dir": technical}
