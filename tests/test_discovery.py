import json
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from deeptalk_studio.discovery import (
    build_research_handoff,
    calculate_total_score,
    load_channel_profile,
    prepare_codex_discovery,
    prepare_discovery,
)
from deeptalk_studio.discovery_renderer import render_discovery_markdown
from deeptalk_studio.discovery_storage import (
    DiscoveryStorageError,
    load_latest_discovery,
    save_discovery,
)
from deeptalk_studio.discovery_validation import DiscoveryValidationError
from deeptalk_studio.models import TopicCandidateSet
from tests.fixtures import valid_discovery_input


NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


class TopicDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.profile = load_channel_profile()

    @staticmethod
    def inspection_manifest(raw):
        return {
            "inspections": [
                {
                    "url": seed["url"],
                    "tool_reference": f"open-{index}",
                    "inspected_at": "2026-08-10T11:00:00+00:00",
                }
                for index, candidate in enumerate(raw["candidates"], 1)
                for seed in candidate["source_seeds"]
            ]
        }

    def test_candidate_artifact_rejects_unknown_and_missing_fields(self):
        raw = valid_discovery_input()
        raw["candidates"][0]["unexpected"] = "not allowed"

        with self.assertRaisesRegex(DiscoveryValidationError, "未知字段"):
            prepare_codex_discovery(raw, self.profile, now=NOW)

        raw = valid_discovery_input()
        raw["candidates"][0].pop("core_tension")
        with self.assertRaisesRegex(DiscoveryValidationError, "缺少必填字段"):
            prepare_codex_discovery(raw, self.profile, now=NOW)

    def test_total_score_uses_fixed_weighted_breakdown_not_payload_total(self):
        breakdown = {
            "researchability": {"score": 5, "reason": "多份可打开的一手和媒体资料。"},
            "depth_conflict": {"score": 4, "reason": "目标与利益有明确冲突。"},
            "freshness": {"score": 3, "reason": "近日出现新进展。"},
            "channel_fit": {"score": 2, "reason": "有一定长期讨论空间。"},
            "attention_signal": {"score": 2, "reason": "只有有限公开讨论信号。"},
        }

        self.assertEqual(calculate_total_score(breakdown), 72)
        raw = valid_discovery_input()
        raw["candidates"][0]["total_score"] = 100
        with self.assertRaisesRegex(DiscoveryValidationError, "未知字段"):
            prepare_codex_discovery(raw, self.profile, now=NOW)

        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=self.inspection_manifest(raw)
        )
        tampered = artifact.to_dict()
        tampered["candidates"][0]["total_score"] = 100
        with self.assertRaisesRegex(DiscoveryValidationError, "固定评分权重"):
            artifact.from_dict(tampered)

    def test_recent_and_ongoing_story_are_eligible_but_stale_story_is_not(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=self.inspection_manifest(raw)
        )
        candidates = {candidate["title"]: candidate for candidate in artifact.data["candidates"]}

        self.assertEqual(candidates["近 72 小时的科技政策新进展"]["eligibility_status"], "eligible")
        self.assertEqual(candidates["持续事件出现关键新进展"]["eligibility_status"], "eligible")
        self.assertEqual(candidates["已经没有新进展的旧话题"]["eligibility_status"], "rejected")

    def test_preflight_rejects_anonymous_rumor_and_invalid_seed_url(self):
        raw = valid_discovery_input()
        rumor = raw["candidates"][0]
        rumor["title"] = "匿名账号的严重指控"
        rumor["event_cluster_key"] = "anonymous-rumor"
        rumor["eligibility_signals"]["anonymous_rumor_only"] = True
        rumor["source_seeds"] = []
        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=self.inspection_manifest(raw)
        )
        candidate = next(item for item in artifact.data["candidates"] if item["title"] == "匿名账号的严重指控")
        self.assertEqual(candidate["eligibility_status"], "rejected")

        raw = valid_discovery_input()
        raw["candidates"][0]["source_seeds"][0]["url"] = "not-a-url"
        with self.assertRaisesRegex(DiscoveryValidationError, "有效 HTTP"):
            prepare_codex_discovery(raw, self.profile, now=NOW)

    def test_high_risk_weak_evidence_is_watch_not_top_five(self):
        raw = valid_discovery_input()
        candidate = raw["candidates"][0]
        candidate.update(
            title="快速事故但证据仍薄弱",
            event_cluster_key="weak-safety-event",
            risk_level="high",
            risk_notes="伤亡和责任归因仍在快速变化。",
            source_seeds=[candidate["source_seeds"][0]],
        )
        candidate["eligibility_signals"]["research_directions"] = 1
        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=self.inspection_manifest(raw)
        )
        weak = next(item for item in artifact.data["candidates"] if item["title"] == "快速事故但证据仍薄弱")

        self.assertEqual(weak["eligibility_status"], "watch")
        self.assertNotIn(weak["candidate_id"], artifact.data["display_candidate_ids"])

    def test_major_fast_event_without_sources_is_watch_but_not_anonymous_rumor(self):
        raw = valid_discovery_input()
        candidate = raw["candidates"][0]
        candidate.update(
            title="刚发生的重大公共安全事件",
            event_cluster_key="major-fast-event",
            risk_level="critical",
            source_seeds=[],
        )
        candidate["eligibility_signals"].update(
            public_evidence_available=False,
            major_fast_event=True,
            research_directions=0,
        )
        artifact = prepare_codex_discovery(raw, self.profile, now=NOW)
        item = next(item for item in artifact.data["candidates"] if item["title"] == "刚发生的重大公共安全事件")

        self.assertEqual(item["eligibility_status"], "watch")

    def test_event_dedup_category_diversity_ranking_and_creator_optional(self):
        raw = valid_discovery_input()
        duplicate = dict(raw["candidates"][0])
        duplicate.update(
            title="同一科技政策的另一种标题",
            event_cluster_key=raw["candidates"][0]["event_cluster_key"],
        )
        raw["candidates"].append(duplicate)
        raw["candidates"][1]["creator_attention_signal"] = {
            "available": False,
            "summary": "",
        }
        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=self.inspection_manifest(raw)
        )
        displayed = [
            next(item for item in artifact.data["candidates"] if item["candidate_id"] == candidate_id)
            for candidate_id in artifact.data["display_candidate_ids"]
        ]

        self.assertEqual(len(displayed), 5)
        self.assertEqual(
            len({item["candidate_id"] for item in artifact.data["candidates"]}),
            len(artifact.data["candidates"]),
        )
        self.assertEqual(sum(item["event_cluster_key"] == "tech-policy" for item in displayed), 1)
        self.assertLessEqual(sum(item["category"] == "technology" for item in displayed), 2)
        self.assertTrue(displayed[0]["is_primary"])
        self.assertGreaterEqual(displayed[0]["total_score"], displayed[-1]["total_score"])
        self.assertNotIn("播放量", json.dumps(artifact.to_dict(), ensure_ascii=False))

    def test_renderer_is_concise_and_only_shows_recommend_or_consider(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=self.inspection_manifest(raw)
        )
        markdown = render_discovery_markdown(artifact)

        self.assertIn("【首选】", markdown)
        self.assertIn("为什么现在值得讲", markdown)
        self.assertIn("只需回复编号", markdown)
        self.assertNotIn('"candidates"', markdown)
        self.assertNotIn("观察：", markdown)

    def test_history_never_overwrites_and_latest_selection_builds_research_handoff(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=self.inspection_manifest(raw)
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = save_discovery(artifact, root)
            self.assertTrue(first.json.exists())
            self.assertTrue(first.markdown.exists())
            with self.assertRaises(DiscoveryStorageError):
                save_discovery(artifact, root)

            latest = load_latest_discovery(root)
            handoff = build_research_handoff(latest, "研究 1")

        self.assertEqual(handoff["selected_position"], 1)
        self.assertIn("research_question", handoff)
        self.assertEqual(len(handoff["source_seeds"]), 2)
        with self.assertRaisesRegex(DiscoveryValidationError, "编号"):
            build_research_handoff(artifact, "9")

    def test_api_mode_marks_unmatched_seed_without_breaking_codex_mode(self):
        raw = valid_discovery_input()
        artifact = prepare_discovery(
            raw,
            self.profile,
            now=NOW,
            discovery_id="DISC-api-test",
            provenance_urls=("https://example.com/tech-official",),
        )
        api_seed_statuses = {
            seed["provenance_status"]
            for seed in artifact.data["candidates"][0]["source_seeds"]
        }
        codex = prepare_codex_discovery(raw, self.profile, now=NOW)

        self.assertIn("unmatched", api_seed_statuses)
        self.assertEqual(codex.data["discovery_mode"], "codex_skill")

    def test_codex_seed_without_manifest_is_unmatched(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(raw, self.profile, now=NOW)

        statuses = {
            seed["provenance_status"]
            for candidate in artifact.data["candidates"]
            for seed in candidate["source_seeds"]
        }
        self.assertEqual(statuses, {"unmatched"})

    def test_codex_seed_in_manifest_is_manual_open(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(
            raw,
            self.profile,
            now=NOW,
            inspection_manifest=self.inspection_manifest(raw),
        )

        statuses = {
            seed["provenance_status"]
            for candidate in artifact.data["candidates"]
            for seed in candidate["source_seeds"]
        }
        self.assertEqual(statuses, {"manual_open"})

    def test_inspection_manifest_allows_an_open_record_without_tool_reference(self):
        raw = valid_discovery_input()
        manifest = self.inspection_manifest(raw)
        manifest["inspections"][0].pop("tool_reference")

        artifact = prepare_codex_discovery(
            raw, self.profile, now=NOW, inspection_manifest=manifest
        )

        self.assertIn(
            "",
            [
                entry["tool_reference"]
                for entry in artifact.data["seed_provenance"]["codex_inspections"]
            ],
        )

    def test_candidate_validator_rejects_machine_owned_field_tampering(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(
            raw,
            self.profile,
            now=NOW,
            inspection_manifest=self.inspection_manifest(raw),
        )

        tampered = artifact.to_dict()
        stale = next(
            candidate
            for candidate in tampered["candidates"]
            if candidate["title"] == "已经没有新进展的旧话题"
        )
        stale["eligibility_status"] = "eligible"
        stale["eligibility_reasons"] = []
        stale["recommendation"] = "consider"
        tampered["rejected_candidate_count"] -= 1
        with self.assertRaisesRegex(DiscoveryValidationError, "机器字段|资格"):
            artifact.from_dict(tampered)

        tampered = artifact.to_dict()
        first, second = tampered["display_candidate_ids"][:2]
        tampered["display_candidate_ids"][:2] = [second, first]
        for candidate in tampered["candidates"]:
            candidate["is_primary"] = candidate["candidate_id"] == second
        with self.assertRaisesRegex(DiscoveryValidationError, "机器字段|展示"):
            artifact.from_dict(tampered)

        tampered = artifact.to_dict()
        first = next(
            candidate
            for candidate in tampered["candidates"]
            if candidate["candidate_id"] == tampered["display_candidate_ids"][0]
        )
        first["recommendation"] = "consider"
        with self.assertRaisesRegex(DiscoveryValidationError, "机器字段|recommendation"):
            artifact.from_dict(tampered)

        tampered = artifact.to_dict()
        tampered["watch_candidate_count"] += 1
        with self.assertRaisesRegex(DiscoveryValidationError, "Candidate Set 机器字段"):
            artifact.from_dict(tampered)

    def test_candidate_validator_rejects_manual_open_not_backed_by_manifest(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(raw, self.profile, now=NOW)
        tampered = artifact.to_dict()
        tampered["candidates"][0]["source_seeds"][0]["provenance_status"] = "manual_open"

        with self.assertRaisesRegex(DiscoveryValidationError, "source_seeds"):
            artifact.from_dict(tampered)

    def test_legacy_candidate_set_without_new_provenance_context_remains_readable(self):
        raw = valid_discovery_input()
        artifact = prepare_codex_discovery(
            raw,
            self.profile,
            now=NOW,
            inspection_manifest=self.inspection_manifest(raw),
        ).to_dict()
        artifact.pop("seed_provenance")
        id_map = {}
        for index, candidate in enumerate(artifact["candidates"], 1):
            old_id = candidate["candidate_id"]
            candidate["candidate_id"] = f"TPC-{index}"
            id_map[old_id] = candidate["candidate_id"]
        artifact["display_candidate_ids"] = [
            id_map[candidate_id] for candidate_id in artifact["display_candidate_ids"]
        ]
        for candidate in artifact["candidates"]:
            candidate["is_primary"] = candidate["candidate_id"] == artifact["display_candidate_ids"][0]

        self.assertEqual(TopicCandidateSet.from_dict(artifact).artifact_version, "0.3")

    def test_preflight_counts_only_distinct_qualifying_checked_directions(self):
        raw = valid_discovery_input()
        candidate = raw["candidates"][0]
        first = deepcopy(candidate["source_seeds"][0])
        second = deepcopy(first)
        second["url"] = first["url"] + "?utm_source=duplicate"
        second["publisher"] = "另一段发布者文本"
        candidate["source_seeds"] = [first, second]
        candidate["eligibility_signals"]["research_directions"] = 2
        artifact = prepare_discovery(
            raw,
            self.profile,
            now=NOW,
            provenance_urls=(first["url"], second["url"]),
            discovery_mode="fixture",
        )
        self.assertEqual(artifact.data["candidates"][0]["eligibility_status"], "rejected")

        raw = valid_discovery_input()
        candidate = raw["candidates"][0]
        candidate["source_seeds"][1]["publisher"] = candidate["source_seeds"][0]["publisher"]
        artifact = prepare_discovery(
            raw,
            self.profile,
            now=NOW,
            provenance_urls=tuple(
                seed["url"] for seed in candidate["source_seeds"]
            ),
            discovery_mode="fixture",
        )
        self.assertEqual(artifact.data["candidates"][0]["eligibility_status"], "rejected")

        raw = valid_discovery_input()
        candidate = raw["candidates"][0]
        candidate["source_seeds"][1]["source_type"] = "social"
        artifact = prepare_discovery(
            raw,
            self.profile,
            now=NOW,
            provenance_urls=tuple(
                seed["url"] for seed in candidate["source_seeds"]
            ),
            discovery_mode="fixture",
        )
        self.assertEqual(artifact.data["candidates"][0]["eligibility_status"], "rejected")

    def test_preflight_accepts_two_distinct_checked_qualifying_directions(self):
        raw = valid_discovery_input()
        candidate = raw["candidates"][0]
        artifact = prepare_discovery(
            raw,
            self.profile,
            now=NOW,
            provenance_urls=tuple(
                seed["url"] for seed in candidate["source_seeds"]
            ),
            discovery_mode="fixture",
        )

        self.assertEqual(artifact.data["candidates"][0]["eligibility_status"], "eligible")

    def test_time_rules_reject_inverted_and_future_events(self):
        raw = valid_discovery_input()
        raw["candidates"][0]["event_started_at"] = "2026-08-10T10:00:00+00:00"
        raw["candidates"][0]["latest_update_at"] = "2026-08-10T09:00:00+00:00"
        with self.assertRaisesRegex(DiscoveryValidationError, "开始时间"):
            prepare_codex_discovery(raw, self.profile, now=NOW)

        raw = valid_discovery_input()
        raw["candidates"][0]["latest_update_at"] = "2026-08-11T08:00:00+00:00"
        artifact = prepare_codex_discovery(raw, self.profile, now=NOW)
        self.assertEqual(artifact.data["candidates"][0]["eligibility_status"], "rejected")

    def test_category_diversity_falls_back_to_single_category(self):
        raw = valid_discovery_input()
        for index, candidate in enumerate(raw["candidates"], 1):
            candidate["category"] = "technology"
            candidate["event_cluster_key"] = f"technology-{index}"
        artifact = prepare_codex_discovery(
            raw,
            self.profile,
            now=NOW,
            inspection_manifest=self.inspection_manifest(raw),
        )

        self.assertEqual(len(artifact.data["display_candidate_ids"]), 5)
        displayed = [
            next(
                candidate
                for candidate in artifact.data["candidates"]
                if candidate["candidate_id"] == candidate_id
            )
            for candidate_id in artifact.data["display_candidate_ids"]
        ]
        self.assertEqual(len({item["event_cluster_key"] for item in displayed}), 5)

    def test_raw_candidate_pool_requires_at_least_seven_items(self):
        raw = valid_discovery_input()
        raw["candidates"] = raw["candidates"][:2]

        with self.assertRaisesRegex(DiscoveryValidationError, "至少需要 7"):
            prepare_codex_discovery(raw, self.profile, now=NOW)


if __name__ == "__main__":
    unittest.main()
