"""Renderer-neutral aligned preview project/result contracts."""
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

@dataclass(frozen=True)
class AlignedPreviewProject:
 project_dir:Path; payload_path:Path; staged_placement_ids:Tuple[str,...]; staged_assets:Tuple[Path,...]; payload_text:str
@dataclass(frozen=True)
class AlignedPreviewRender:
 output_path:Path; command_summary:str; sha256:str; byte_size:int
