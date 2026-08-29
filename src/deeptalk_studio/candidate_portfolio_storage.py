"""Immutable JSON storage for minimal Candidate Portfolio artifacts."""
from __future__ import annotations
import json, os, re
from pathlib import Path
from typing import Any, Mapping

class CandidatePortfolioStorageError(ValueError): pass

def save_candidate_portfolio(value: Mapping[str, Any], root: Path) -> Path:
    _validate(value); identity = str(value["portfolio_id"])
    path = Path(root) / identity / "candidate-portfolio.json"; path.parent.mkdir(parents=True, exist_ok=True)
    try: fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc: raise CandidatePortfolioStorageError("不会覆盖已有工件") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle: handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)+"\n")
    return path

def load_candidate_portfolio(path: Path) -> dict:
    try: value=json.loads(Path(path).read_text(encoding="utf-8")); _validate(value)
    except (OSError,json.JSONDecodeError,CandidatePortfolioStorageError) as exc: raise CandidatePortfolioStorageError("portfolio 工件无效") from exc
    if Path(path).parent.name != value["portfolio_id"]: raise CandidatePortfolioStorageError("portfolio 路径无效")
    return value

def _validate(value: Any) -> None:
    if not isinstance(value, Mapping) or value.get("artifact_version") != "candidate-portfolio/1" or not re.fullmatch(r"CP-[0-9a-f]{24}", str(value.get("portfolio_id",""))) or not value.get("opportunity_id") or not value.get("proposal") or len(str(value.get("portfolio_digest",""))) != 64: raise CandidatePortfolioStorageError("portfolio schema 无效")
