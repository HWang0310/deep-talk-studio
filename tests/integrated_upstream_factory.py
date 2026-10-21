"""Canonical reviewed roots with real image, ranged/unranged video and Motion."""
import hashlib,json,subprocess
from copy import deepcopy
from pathlib import Path

from deeptalk_studio.material_profile import load_material_profile
from deeptalk_studio.material_review import MATERIAL_REVIEW_CHECK_NAMES,prepare_material_review
from deeptalk_studio.material_storage import save_material_package,save_material_review_artifact
from deeptalk_studio.material_validation import material_package_digest,prepare_material_package,update_package_assets
from deeptalk_studio.models import MaterialPackage
from deeptalk_studio.production_planner import prepare_production_plan
from deeptalk_studio.production_profile import load_production_profile
from deeptalk_studio.production_qa import build_motion_asset_manifest,prepare_production_qa
from deeptalk_studio.production_renderers.base import RenderBatch,RenderOutput,RendererCheckResult
from deeptalk_studio.production_storage import save_production_artifact,save_production_plan
from deeptalk_studio.visual_renderer import render_visual_svg,visual_asset_record
from tests.material_fixtures import reviewed_inputs,valid_material_content
from tests.media_fixture_factory import MediaFixtureSpec,build_media_fixture

def _material(title,url,beat,anchor,asset_type,video_reference):
 return {"title":title,"source_url":url,"page_url":url,"publisher_creator":"Synthetic Official","asset_type":asset_type,"published_at":"2026-08-09","intended_role":"evidence","cue_numbers":[],"claim_ids":["C1"],"evidence_link_ids":["E1"],"suggested_usage":"集成测试画面。","caption":"事件在 2026 年 8 月 9 日发生。","illustrative_only":False,"claimed_rights_status":"unknown","claimed_rights_basis":"仅供集成测试核对。","claimed_license_url":"","relevance":5,"grounding_strength":5,"visual_clarity":5,"reuse_safety":2,"acquisition_effort":1,"ranking_reason":"完整生产入口回归。","capture":{"page_number":1,"capture_region":"完整画面","source_context":"集成测试原创素材","what_it_proves":"事件日期。","what_it_does_not_prove":"不证明事件原因。"},"video_reference":video_reference,"_beat":beat,"_anchor":anchor}

def _rights_entries(rows,mode):
 """Synthetic rights-manifest entries per mode; `verified` adds matching
  inspections.  IMPORTANT: this fixture is entirely simulated — no real web
  page is ever opened and no real third-party reuse license is granted.  The
  example.com URLs and the codex_web_open inspection records are stub data
  that exercise the canonical Rights Gate flow inside tests only; the
  `rights_basis` wording must stay clearly marked as simulated so the E2E
  evidence never reads as an actually verified public-domain license.

  `verified` clears the image (M001) through this simulated public-domain
  entry.  The ranged video clip deliberately stays uncleared: Production
  only renders image-based scenes, so a rights-cleared local video reference is
  exercised by the audio-delivery rights gate itself (it becomes an explicit
  visual gap with the reason recorded), never by silently entering the pack.
 """
 if mode=="unknown":return [],[]
 image_rights={"url":rows[0]["source_url"],"rights_status":"public_domain","rights_basis":"模拟权利数据（synthetic fixture）：未发生真实联网核验，非真实第三方复用许可，仅用于验证 Rights Gate 流程。","rights_evidence_url":"https://example.com/e2e-image-rights","license_url":"","verified_at":"2026-08-13T20:00:00+08:00","tool_reference":"open:rights-image"}
 if mode=="verified":
  extra=[
   {"url":"https://example.com/e2e-image-rights","inspected_at":"2026-08-13T20:00:00+08:00","inspection_method":"codex_web_open","tool_reference":"open:rights-image"},
  ]
  return extra,[image_rights]
 if mode=="permission_required":
  return [],[
   dict(image_rights,rights_status="permission_required",rights_basis="仅取得口头许可，未见书面授权。",rights_evidence_url=rows[0]["source_url"],license_url="",tool_reference="open:"+rows[0]["title"]),
   dict(image_rights,url=rows[1]["source_url"],rights_status="permission_required",rights_basis="仅取得口头许可，未见书面授权。",rights_evidence_url=rows[1]["source_url"],license_url="",tool_reference="open:"+rows[1]["title"]),
  ]
 raise ValueError("rights_mode 必须是 unknown / permission_required / verified")

def create_integrated_roots(root:Path,*,rights_mode:str="unknown"):
 report,script,script_review=reviewed_inputs();profile=load_material_profile();asset_root=root/"material_assets"/"MAT-INTEGRATED"
 image=asset_root/"acquired"/"M001.png";image.parent.mkdir(parents=True);subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i","color=c=navy:s=320x180:d=0.1","-frames:v","1",str(image)],check=True)
 ranged=build_media_fixture(asset_root/"acquired",MediaFixtureSpec(name="M002",duration="2"));unranged=build_media_fixture(asset_root/"acquired",MediaFixtureSpec(name="M003",duration="2"))
 rows=[
  _material("日期图片","https://example.com/e2e-image","B001","事件发生在八月九日","document_screenshot",{"title":"","start_seconds":0,"end_seconds":0,"usage_reason":""}),
  _material("已选范围视频","https://example.com/e2e-ranged","B002","问题来自流程故障","video_clip_reference",{"title":"公开片段","start_seconds":0.2,"end_seconds":1.2,"usage_reason":"展示公开片段"}),
  _material("未选范围视频","https://example.com/e2e-unranged","B004","网络上确实流传","video_clip_reference",{"title":"公开片段","start_seconds":0,"end_seconds":0,"usage_reason":"尚未选择具体片段"}),
 ]
 cues=[]
 for index,row in enumerate(rows,1):
  row["cue_numbers"]=[index];cues.append({"beat_id":row.pop("_beat"),"placement_anchor":row.pop("_anchor"),"visual_role":"evidence","suggested_duration_seconds":2,"preferred_asset_type":row["asset_type"],"priority":"high","reason":"集成测试画面。"})
 base=valid_material_content();visual_cue=deepcopy(base["cue_sheet"][1]);visual_cue["suggested_duration_seconds"]=2;cues.append(visual_cue)
 visual=deepcopy(base["visual_specs"][0]);visual["suggested_duration_seconds"]=2
 content={"cue_sheet":cues,"materials":rows,"visual_specs":[visual],"gaps":[],"research_update_signals":[],"warnings":[]}
 entries=[]
 for row in rows:
  entries.append({"url":row["source_url"],"inspected_at":"2026-08-13T20:00:00+08:00","inspection_method":"codex_web_open","tool_reference":"open:"+row["title"]})
 extra_inspections,rights_entries=_rights_entries(rows,rights_mode)
 entries.extend(extra_inspections)
 rights={"entries":rights_entries}
 package=prepare_material_package(content,script,report,profile,inspection_manifest={"entries":entries},rights_manifest=rights,created_at="2026-08-13T20:00:00+08:00",package_id="MAT-INTEGRATED")
 files=[image,ranged,unranged];data=package.to_dict()
 for item,path in zip(data["materials"],files):item.update(local_path=str(path.resolve()),byte_size=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 package=MaterialPackage(data);visual_path=render_visual_svg(package.generated_visuals[0],asset_root/"generated");package=update_package_assets(package,visual_records={package.generated_visuals[0]["visual_id"]:visual_asset_record(visual_path)})
 data=package.to_dict();data["package_digest"]=material_package_digest(data);package=MaterialPackage(data);packages=root/"material_packages";r1=save_material_package(package,packages)
 if rights_mode=="verified":
  # rights-verified positive fixture: independent review passes every check
  issues=[];checks=[{"check_name":name,"outcome":"pass","reason":"canonical 审查完成。"} for name in MATERIAL_REVIEW_CHECK_NAMES]
 else:
  issues=[{"issue_type":"permission_needed","material_ids":[item["material_id"]],"visual_ids":[],"cue_ids":list(item["cue_ids"]),"explanation":"无公开复用依据。","suggested_fix":"只保留编辑核对。"} for item in package.materials]
  checks=[{"check_name":name,"outcome":"fail" if name=="rights_reuse" else "pass","reason":"集成测试 canonical 审查完成。"} for name in MATERIAL_REVIEW_CHECK_NAMES]
 review=prepare_material_review({"issues":issues,"checks":checks,"overall_notes":"完整入口回归。"},package,script,report,profile,created_at="2026-08-13T20:01:00+08:00",review_id="MRV-INTEGRATED")
 save_material_review_artifact(review.artifact,package,packages);r2=save_material_package(review.package,packages)
 production_profile=load_production_profile();plan=prepare_production_plan(review.package,script,report,production_profile,asset_root,created_at="2026-08-13T20:02:00+08:00",production_id="PROD-INTEGRATED",renderer_mode="remotion")
 motion_dir=root/"production_assets"/"PROD-INTEGRATED"/"assets";motion_dir.mkdir(parents=True);outputs=[]
 for expected in plan["motion_assets"]:
  path=motion_dir/(expected["motion_asset_id"]+(".png" if expected["requested_format"]=="png" else ".mp4"));scene=next(s for s in plan["scenes"] if s["scene_id"]==expected["scene_id"])
  if expected["asset_kind"]=="hero_still":subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i","color=s=1920x1080:d=0.1","-frames:v","1",str(path)],check=True)
  else:
   duration=sum(float(s["duration_seconds"]) for s in plan["scenes"]) if expected["asset_kind"]=="rough_preview" else float(scene["duration_seconds"])
   subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",f"color=c=black:s=1920x1080:r=30:d={duration}","-an","-c:v","libx264","-pix_fmt","yuv420p",str(path)],check=True)
  outputs.append(RenderOutput(expected["motion_asset_id"],expected["scene_id"],expected["asset_kind"],path,"synthetic canonical render"))
 manifest_result=build_motion_asset_manifest(plan,"remotion",RenderBatch(tuple(outputs),()),created_at="2026-08-13T20:03:00+08:00",manifest_id="MAM-INTEGRATED")
 check=RendererCheckResult("synthetic_renderer_validation","remotion",0,"pass","validate","通过")
 qa=prepare_production_qa(plan,manifest_result,created_at="2026-08-13T20:04:00+08:00",qa_id="PQA-INTEGRATED",renderer_checks=[check])
 plan_path=save_production_plan(plan,root/"production_packages");save_production_artifact(manifest_result.manifest,plan_path,"motion-asset-manifest-r0001.json");save_production_artifact(qa,plan_path,"production-qa-r0001.json")
 report_dir=root/"reports"/"fixture";report_dir.mkdir(parents=True);(report_dir/f"research-report-r{report.revision:04d}.json").write_text(json.dumps(report.to_dict(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 script_dir=root/"script_drafts"/"fixture";script_dir.mkdir(parents=True);(script_dir/f"script-draft-r{script.revision:04d}.json").write_text(json.dumps(script.to_dict(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 reviewed_from=int(script.review_state["reviewed_from_revision"]);review_id=script.review_state["review_id"]
 (script_dir/f"script-review-for-r{reviewed_from:04d}-{review_id}.json").write_text(json.dumps(script_review,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return report,script,r2.json,asset_root,plan,manifest_result.manifest,qa
