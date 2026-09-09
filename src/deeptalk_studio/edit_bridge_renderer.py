"""Human-readable Markdown and RFC4180/BOM marker outputs."""
import csv,io

CSV_COLUMNS=("canonical IN seconds","canonical OUT seconds","canonical IN HH:MM:SS.mmm","canonical OUT HH:MM:SS.mmm","semantic duration","natural duration","target duration","Preview effective IN seconds","Preview effective OUT seconds","Preview IN frame","Preview OUT frame","Preview IN frame timecode","Preview OUT frame timecode","Beat","Cue","Scene","visual role","source kind","asset type","safe filename/motion asset","layout mode","anchor","placement status","timing status","duration status","confidence","notes")
FIELDS=("semantic_in_seconds","semantic_out_seconds","canonical_in_timecode","canonical_out_timecode","semantic_duration_seconds","natural_duration_seconds","target_duration_seconds","preview_effective_in_seconds","preview_effective_out_seconds","preview_in_frame","preview_out_frame","preview_in_frame_timecode","preview_out_frame_timecode","beat_id","cue_id","scene_id","visual_role","source_kind","asset_type","safe_filename","layout_mode","placement_anchor","placement_status","timing_status","duration_status","confidence","notes")

def render_edit_bridge_csv(bridge):
 stream=io.StringIO(newline=""); writer=csv.writer(stream,lineterminator="\r\n"); writer.writerow(CSV_COLUMNS)
 for p in bridge["visual_placements"]: writer.writerow(["、".join(p.get(f,[])) if isinstance(p.get(f),list) else p.get(f,"") for f in FIELDS])
 return b"\xef\xbb\xbf"+stream.getvalue().encode("utf-8")

def render_edit_bridge_markdown(bridge):
 ready=[p for p in bridge["visual_placements"] if p["placement_status"]=="ready"]
 other=[p for p in bridge["visual_placements"] if p["placement_status"]!="ready"]
 lines=["# 视觉粗剪交接","",f"- 可直接进入粗剪：{len(ready)} 项",f"- 保留但需处理：{len(other)} 项","", "## 可用画面",""]
 for p in ready: lines.append(f"- {p.get('safe_filename') or p.get('source_kind')}：{p.get('canonical_in_timecode','')} → {p.get('canonical_out_timecode','')}")
 if other:
  lines.extend(["","## 需要处理的画面",""])
  for p in other: lines.append(f"- {p.get('safe_filename') or p.get('source_kind')}：{p.get('placement_status')}")
 if bridge.get("timing_conflicts") or bridge.get("alignment_gaps"): lines.extend(["","所有时长警告和对齐差异已保留在机器工件中，未被摘要隐藏。"])
 return "\n".join(lines)+"\n"
