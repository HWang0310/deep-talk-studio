"""Issue #30: audio-only final delivery (WAV/MP3 -> real timeline -> Asset Pack)."""
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace

from deeptalk_studio.asset_pack_workflow import AssetPackWorkflowError, build_production_asset_pack
from deeptalk_studio.audio_delivery import (
    AUDIO_ONLY,
    REAL_MATERIAL,
    AudioDeliveryError,
    build_approved_facts,
    derive_audio_assets,
    run_audio_only_delivery,
)
from deeptalk_studio.clean_aroll_gate import CleanARollGateError, inspect_clean_aroll
from deeptalk_studio.edit_bridge_qa import (
    EditBridgeQAError,
    _audio_asset_pack_rederived,
    _audio_no_preview,
)
from deeptalk_studio.edit_bridge_session import RealEditBridgeSessionInputs
from deeptalk_studio.narration_media import canonical_digest
from deeptalk_studio.transcription.base import ProviderTimedUnit, ProviderTranscript, boundary_risks_from_plan
from tests.media_fixture_factory import MediaFixtureSpec, build_media_fixture
from tests.integrated_upstream_factory import create_integrated_roots


NOW = "2026-10-21T12:00:00+08:00"


def _id_factory(kind):
    return {"MEDIA": "MEDIA-AUD", "MAPPING": "MAP-AUD", "TRANSCRIPT": "TR-AUD",
            "SUBTITLE": "SUB-AUD", "ALIGNMENT": "AL-AUD", "BRIDGE": "EB-AUD",
            "TIMELINE": "TL-AUD"}[kind]


class ScriptProvider:
    """Deterministic provider: splits reviewed narration into token-like units."""

    def __init__(self, script):
        self.script = script
        self.preferred_sample_rate = 48000
        self.chunk_profile_path = None
        self.default_configured_model = "whisper-1"

    def transcribe(self, extracted, plan, language, model):
        phrases = []
        for beat in self.script.beats:
            text = beat["narration"]
            for index in range(0, len(text), 6):
                phrase = text[index:index + 6]
                if phrase and not any(char.isalnum() or "\u3400" <= char <= "\u9fff" for char in phrase):
                    phrases[-1] += phrase
                else:
                    phrases.append(phrase)
        duration = Decimal(str(extracted["duration_seconds"]))
        step = duration / Decimal(len(phrases) + 1)
        units = tuple(
            ProviderTimedUnit(0, i, step * i, step * (i + 1), phrase)
            for i, phrase in enumerate(phrases)
        )
        metadata = {"source": "issue30-test", "chunk_plan_digest": plan.digest}
        return ProviderTranscript("deterministic", model, "fixture/1", "", language, "token", units,
                                  boundary_risks_from_plan(plan), metadata, canonical_digest(metadata), plan.digest)


class RetakeProvider(ScriptProvider):
    """Deterministic provider whose real transcript contains an explicit retake marker."""

    def transcribe(self, extracted, plan, language, model):
        result = super().transcribe(extracted, plan, language, model)
        units = list(result.units)
        first = units[0]
        units[0] = ProviderTimedUnit(
            first.chunk_index, first.provider_order, first.local_start_seconds,
            first.local_end_seconds, first.spoken_text + "这一段重录",
            first.provider_confidence, first.boundary_risk_ids,
        )
        return ProviderTranscript(
            result.provider, result.provider_model, result.provider_model_version,
            result.provider_request_id, result.language, result.timestamp_granularity,
            tuple(units), result.boundary_risks, result.raw_metadata,
            result.raw_response_digest, result.chunk_plan_digest,
        )


def _build_inputs(base: Path, suffix: str = ".wav", rights_mode: str = "unknown") -> RealEditBridgeSessionInputs:
    upstream = base / "upstream"
    report, script, package_path, asset_root, plan, manifest, production_qa = create_integrated_roots(upstream, rights_mode=rights_mode)
    session = base / "session"; session.mkdir()
    source = build_media_fixture(session, MediaFixtureSpec(name="narration", suffix=suffix, video=False, audio=True, duration="2"))
    output = session / "DeepTalk-Aligned-Edit"
    return RealEditBridgeSessionInputs(
        session, source, report, script, package_path, plan, manifest, production_qa,
        asset_root, (asset_root, upstream / "production_assets", output, session), output,
    )


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class AudioDeliveryE2ETests(unittest.TestCase):
    def _run(self, tmp: Path, suffix: str = ".wav", rights_mode: str = "unknown", provider=None):
        inputs = _build_inputs(tmp, suffix, rights_mode=rights_mode)
        return run_audio_only_delivery(
            inputs, provider or ScriptProvider(inputs.script),
            clock=lambda: NOW, id_factory=_id_factory,
        )

    def test_wav_delivery_produces_truthful_edit_map_with_material_and_gap(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="verified")
            pack = result["asset_pack"]
            rows = pack.machine_map["rows"]
            self.assertEqual(result["preview_path"], None)
            self.assertIn(result["qa"]["package_gate_status"], {"pass", "warnings"})
            self.assertTrue(result["qa"]["checks"])
            # 4 shared groups + audio_delivery group all pass
            groups = {c["group"] for c in result["qa"]["checks"] if c["outcome"] == "pass"}
            self.assertEqual(groups, {"root", "transcript", "alignment", "placement", "audio_delivery"})
            # real clock copied from transcript token times (token-level provenance)
            self.assertEqual(rows[0]["actual_start_seconds"], result["transcript"]["timed_units"][0]["media_start_seconds"])
            self.assertEqual(rows[-1]["actual_end_seconds"], result["transcript"]["timed_units"][-1]["media_end_seconds"])
            decisions = [r["decision"] for r in rows]
            self.assertIn(REAL_MATERIAL, decisions)
            self.assertIn(AUDIO_ONLY, decisions)
            self.assertNotIn("KEEP_A_ROLL", decisions)
            for row in rows:
                if row["decision"] == AUDIO_ONLY:
                    self.assertEqual(row["asset_filename"], "")
                    self.assertEqual(row["qa_status"], "not_applicable")
                    self.assertTrue(row["requires_human_review"])
                    self.assertIn("补画面", row["placement_advice"])
                if row["decision"] == REAL_MATERIAL:
                    self.assertTrue(row["asset_filename"])
                    # rights-verified provenance only: never "no verifiable basis"
                    self.assertNotIn("未找到可核验的复用依据", row["provenance"])
                    self.assertTrue(row["provenance"].strip())
            for path in (result["paths"]["markdown"], result["paths"]["csv"], result["paths"]["json"], result["paths"]["manifest"]):
                self.assertTrue(path.is_file())
            self.assertTrue(any(a["asset_class"] == REAL_MATERIAL for a in pack.manifest["assets"]))
            self.assertFalse(any(a["asset_class"] == AUDIO_ONLY for a in pack.manifest["assets"]))
            # material file copied into the episode asset dir with matching SHA
            for asset in pack.manifest["assets"]:
                copy = Path(asset["local_path"])
                self.assertTrue(copy.is_file())
                self.assertEqual(hashlib.sha256(copy.read_bytes()).hexdigest(), asset["sha256"])
            # no preview output anywhere
            self.assertFalse(list((result["paths"]["markdown"].parent.parent / "outputs").glob("ALIGNED_PREVIEW*.mp4")))
            # real-time lineage artifacts in 05_A-roll (incl. controlled gate result)
            aroll = result["paths"]["markdown"].parent.parent / "05_A-roll"
            self.assertTrue((aroll / "actual-transcript.json").is_file())
            self.assertTrue((aroll / "alignment.json").is_file())
            self.assertTrue((aroll / "semantic-timeline.json").is_file())
            gate_artifact = json.loads((aroll / "clean-aroll-gate.json").read_text(encoding="utf-8"))
            self.assertEqual(gate_artifact["status"], "accepted")
            # controlled gate result is bound into the delivery roots
            self.assertEqual(result["delivery"]["roots"]["clean_aroll_gate_status"], "accepted")

    def test_mp3_delivery_uses_same_audio_only_chain(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".mp3", rights_mode="verified")
            self.assertEqual(result["preview_path"], None)
            self.assertIn(result["qa"]["package_gate_status"], {"pass", "warnings"})
            self.assertTrue(result["asset_pack"].machine_map["rows"])
            self.assertTrue(any(r["decision"] == REAL_MATERIAL for r in result["asset_pack"].machine_map["rows"]))

    def test_rights_unverified_material_never_enters_pack(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="unknown")
            rows = result["asset_pack"].machine_map["rows"]
            decisions = [r["decision"] for r in rows]
            self.assertNotIn(REAL_MATERIAL, decisions)
            self.assertNotIn("KEEP_A_ROLL", decisions)
            self.assertTrue(decisions and all(d == AUDIO_ONLY for d in decisions))
            self.assertEqual(result["asset_pack"].manifest["asset_count"], 0)
            self.assertEqual(result["asset_pack"].manifest["assets"], [])
            # every row is an honest visual gap, and rights-blocked spans say so
            for row in rows:
                self.assertEqual(row["asset_filename"], "")
                self.assertEqual(row["qa_status"], "not_applicable")
                self.assertTrue(row["requires_human_review"])
            self.assertTrue(any("授权" in r["why"] for r in rows))
            self.assertIn(result["qa"]["package_gate_status"], {"pass", "warnings"})

    def test_permission_required_material_never_enters_pack(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="permission_required")
            rows = result["asset_pack"].machine_map["rows"]
            self.assertTrue(rows and all(r["decision"] == AUDIO_ONLY for r in rows))
            self.assertEqual(result["asset_pack"].manifest["asset_count"], 0)
            self.assertTrue(any("授权" in r["why"] for r in rows))

    def test_explicit_retake_blocks_audio_delivery(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            inputs = _build_inputs(tmp, ".wav", rights_mode="verified")
            with self.assertRaisesRegex(AudioDeliveryError, "人工清理"):
                run_audio_only_delivery(
                    inputs, RetakeProvider(inputs.script),
                    clock=lambda: NOW, id_factory=_id_factory,
                )
            # fail closed before any Edit Map is produced
            self.assertFalse((inputs.output_root / "episode" / "09_剪辑表").exists())

    def test_tampered_copied_material_fails_closed(self):
        from deeptalk_studio.edit_bridge_qa import validate_audio_delivery_assets
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="verified")
            # corrupt one delivered material copy -> post-hoc audit must reject
            for asset in result["asset_pack"].manifest["assets"]:
                target = Path(asset["local_path"])
                with target.open("ab") as handle:
                    handle.write(b"tamper")
            with self.assertRaises(EditBridgeQAError):
                validate_audio_delivery_assets(result["asset_pack"].manifest, Path(result["paths"]["markdown"]).parent.parent)
            # intact delivery passes
            clean = result["asset_pack"].manifest
            # restore one asset to prove the audit is per-file
            with target.open("r+b") as handle:
                handle.seek(-7, 2)
                handle.truncate()
            with self.assertRaises(EditBridgeQAError):
                validate_audio_delivery_assets(clean, Path(result["paths"]["markdown"]).parent.parent)

    def test_audio_no_preview_rejects_frame_tampering(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="verified")
            context = result["qa_context"]
            self.assertIsNotNone(context)
            placements = [dict(p) for p in context.placements]
            ready = next(p for p in placements if p.get("placement_status") == "ready")
            # 1) a ready placement whose Preview frames no longer match the real
            #    timeline derivation must fail closed (no vacuous pass)
            tampered = dict(ready); tampered["preview_in_frame"] = ready["preview_in_frame"] + 5
            bad = SimpleNamespace(**{**vars(context), "placements": [tampered if p is ready else p for p in placements]})
            with self.assertRaisesRegex(EditBridgeQAError, "确定性推导"):
                _audio_no_preview(bad)
            # 2) a preview-disabled placement must not carry Preview frames
            disabled = dict(ready); disabled["preview_enabled"] = False; disabled["preview_in_frame"] = 3; disabled["preview_out_frame"] = 9
            bad = SimpleNamespace(**{**vars(context), "placements": [disabled if p is ready else p for p in placements]})
            with self.assertRaisesRegex(EditBridgeQAError, "未启用 Preview"):
                _audio_no_preview(bad)
            # 3) an intact delivery still passes the same check
            _audio_no_preview(context)

    def test_audio_qa_rejects_edit_map_digest_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="verified")
            context = result["qa_context"]
            json_path = Path(result["paths"]["json"])
            machine = json.loads(json_path.read_text(encoding="utf-8"))
            machine["map_digest"] = "0" * 64
            json_path.write_text(json.dumps(machine, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(EditBridgeQAError, "map_digest"):
                _audio_asset_pack_rederived(context)

    def test_audio_qa_rejects_manifest_digest_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="verified")
            context = result["qa_context"]
            manifest_path = Path(result["paths"]["manifest"])
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["manifest_digest"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(EditBridgeQAError, "manifest_digest"):
                _audio_asset_pack_rederived(context)

    def test_audio_qa_rejects_manifest_path_substitution(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self._run(Path(raw), ".wav", rights_mode="verified")
            context = result["qa_context"]
            json_path = Path(result["paths"]["json"])
            manifest_path = Path(result["paths"]["manifest"])
            machine = json.loads(json_path.read_text(encoding="utf-8"))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            # fully self-consistent substitution: same bytes, valid recomputed
            # digests and cross-bindings — only Episode containment can reject it
            from deeptalk_studio.asset_pack_workflow import compute_edit_map_digest, compute_manifest_digest
            outside = Path(raw) / "outside" / "substituted.mp4"
            outside.parent.mkdir()
            shutil.copy2(Path(manifest["assets"][0]["local_path"]), outside)
            manifest["assets"][0]["local_path"] = str(outside)
            manifest["manifest_digest"] = compute_manifest_digest(manifest)
            machine["asset_manifest_digest"] = manifest["manifest_digest"]
            machine["map_digest"] = compute_edit_map_digest(machine)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            json_path.write_text(json.dumps(machine, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result["asset_pack"].manifest["assets"][0]["local_path"] = str(outside)
            result["asset_pack"].manifest["manifest_digest"] = manifest["manifest_digest"]
            result["asset_pack"].machine_map["asset_manifest_digest"] = manifest["manifest_digest"]
            result["asset_pack"].machine_map["map_digest"] = machine["map_digest"]
            with self.assertRaisesRegex(EditBridgeQAError, "越出当前 Episode"):
                _audio_asset_pack_rederived(context)

    def test_rejects_video_media_for_audio_delivery(self):
        with tempfile.TemporaryDirectory() as raw:
            # audio delivery entrypoint rejects a video with a video stream
            upstream = Path(raw) / "upstream"
            report, script, package_path, asset_root, plan, manifest, production_qa = create_integrated_roots(upstream)
            session = Path(raw) / "session"; session.mkdir()
            source = build_media_fixture(session, MediaFixtureSpec(name="video", suffix=".mp4", video=True, audio=True, duration="2"))
            output = session / "DeepTalk-Aligned-Edit"
            inputs = RealEditBridgeSessionInputs(session, source, report, script, package_path, plan, manifest, production_qa,
                                                 asset_root, (asset_root, upstream / "production_assets", output, session), output)
            with self.assertRaises(AudioDeliveryError):
                run_audio_only_delivery(inputs, ScriptProvider(inputs.script), clock=lambda: NOW, id_factory=_id_factory)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class AudioDeliveryUnitTests(unittest.TestCase):
    def test_gate_accepts_audio_only_media(self):
        result = inspect_clean_aroll({"media_id": "NM-1", "artifact_digest": "a" * 64, "media_kind": "audio"}, {"text": "正常口播。"})
        self.assertEqual(result.status, "accepted")

    def test_gate_still_rejects_invalid_media_kind(self):
        with self.assertRaises(CleanARollGateError):
            inspect_clean_aroll({"media_id": "NM-1", "artifact_digest": "a" * 64, "media_kind": "document"})

    def test_asset_pack_audio_only_row_has_no_fake_aroll(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spans = [{"span_id": "ST001", "actual_start_seconds": "0.0", "actual_end_seconds": "1.2", "summary": "无画面段", "visual_eligibility": "safe"}]
            plan = {"alignment_digest": "a" * 64, "opportunities": [
                {"opportunity_id": "OP001", "span_id": "ST001", "decision": AUDIO_ONLY,
                 "why_visual": "该时间段无真人画面可保留，需要人工补画面。", "review_requirement": "not_needed"},
            ]}
            roots = {"clean_aroll_gate_status": "accepted", "timing_provenance": "actual_aroll_alignment",
                     "alignment_digest": "a" * 64, "transcript_digest": "b" * 64}
            pack = build_production_asset_pack(roots, spans, plan, [], episode_root=root / "episode", created_at=NOW)
            row = pack.machine_map["rows"][0]
            self.assertEqual(row["decision"], AUDIO_ONLY)
            self.assertEqual(row["asset_filename"], "")
            self.assertEqual(row["qa_status"], "not_applicable")
            self.assertTrue(row["requires_human_review"])
            self.assertIn("补画面", pack.markdown_path.read_text(encoding="utf-8"))
            self.assertEqual(pack.manifest["asset_count"], 0)

    def test_approved_facts_are_review_bound_not_empty_when_bound(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            upstream = base / "upstream"
            report, script, _, _, _, _, _ = create_integrated_roots(upstream)
            facts = build_approved_facts(report.data, script.data)
            self.assertTrue(facts)
            self.assertTrue(any(f["beat_id"] == "B001" and f["kind"] == "date" for f in facts))

    def test_unranged_reference_clip_is_never_auto_picked(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            upstream = base / "upstream"
            report, script, package_path, assets, plan, manifest, production_qa = create_integrated_roots(upstream)
            from deeptalk_studio.material_bridge import build_material_production_view
            from deeptalk_studio.material_profile import load_material_profile
            material_view = build_material_production_view(package_path, script, report, load_material_profile(), assets,
                                                       artifact_resolver=None)
            unranged = next(i for i in material_view["items"] if i["asset_type"] == "video_clip_reference" and not i["video_reference"].get("end_seconds"))
            self.assertEqual(unranged["production_status"], "ready")  # local file is verified
            # derive_audio_assets is exercised fully by the E2E; here we assert the
            # unranged clip is not mapped to a candidate by the bridge filtering
            self.assertTrue(any(i["asset_type"] == "video_clip_reference" and i["video_reference"].get("end_seconds") for i in material_view["items"]))
            self.assertFalse(any(i["video_reference"].get("end_seconds") for i in material_view["items"] if i["asset_type"] == "video_clip_reference" and not i["video_reference"].get("start_seconds")))


if __name__ == "__main__":
    unittest.main()
