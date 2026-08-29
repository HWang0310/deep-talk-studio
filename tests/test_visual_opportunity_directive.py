import copy
import json
import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.visual_opportunity_directive import (
    VisualOpportunityDirectiveError,
    directive_digest,
    normalize_visual_opportunity_directives,
)
from deeptalk_studio.visual_opportunity_directive_storage import (
    VisualOpportunityDirectiveStorageError,
    load_visual_opportunity_directives,
    save_visual_opportunity_directives,
)


def directives():
    return {
        "artifact_version": "visual-opportunity-directives/1",
        "directives_id": "VOD-synthetic-01",
        "revision": 1,
        "semantic_timeline_digest": "a" * 64,
        "reviewed_script_digest": "b" * 64,
        "directives": [{
            "directive_id": "vod-synthetic-01",
            "span_id": "ST001",
            "visual_purpose": "Explain the synthetic sequence.",
            "why_opportunity": "The causal sequence benefits from an illustration.",
            "semantic_context_selector": {"include_neighboring_spans": 1},
            "factual_context_refs": [{"claim_id": "claim-01", "evidence_id": "evidence-01"}],
        }],
    }


class VisualOpportunityDirectiveTests(unittest.TestCase):
    def test_normalizes_valid_clock_free_directives_deterministically(self):
        source = directives()
        self.assertEqual(normalize_visual_opportunity_directives(source), source)
        self.assertEqual(directive_digest(source), directive_digest(copy.deepcopy(source)))

    def test_rejects_wrong_version_duplicate_ids_and_duplicate_span_scope(self):
        wrong = directives(); wrong["artifact_version"] = "visual-opportunity-directives/2"
        with self.assertRaisesRegex(VisualOpportunityDirectiveError, "artifact_version"):
            normalize_visual_opportunity_directives(wrong)
        duplicate_id = directives(); duplicate_id["directives"].append(copy.deepcopy(duplicate_id["directives"][0]))
        duplicate_id["directives"][1]["span_id"] = "ST002"
        with self.assertRaisesRegex(VisualOpportunityDirectiveError, "directive_id"):
            normalize_visual_opportunity_directives(duplicate_id)
        duplicate_span = directives(); duplicate_span["directives"].append(copy.deepcopy(duplicate_span["directives"][0]))
        duplicate_span["directives"][1]["directive_id"] = "vod-synthetic-02"
        with self.assertRaisesRegex(VisualOpportunityDirectiveError, "span_id"):
            normalize_visual_opportunity_directives(duplicate_span)

    def test_recursively_rejects_clocks_and_v1_or_plugin_selection_leakage(self):
        for forbidden in (
            "start_ms", "end_ms", "start_seconds", "end_seconds", "duration_ms", "duration_seconds",
            "a_roll_window", "suggested_placement", "decision", "visual_kind", "asset_class", "candidate",
            "candidate_id", "plugin_id", "plugin_context", "generation_policy",
        ):
            value = directives()
            value["directives"][0]["semantic_context_selector"][forbidden] = "KEEP_A_ROLL"
            with self.subTest(forbidden=forbidden), self.assertRaisesRegex(VisualOpportunityDirectiveError, forbidden):
                normalize_visual_opportunity_directives(value)

    def test_storage_is_immutable_and_revalidates_loaded_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = save_visual_opportunity_directives(directives(), root)
            self.assertEqual(load_visual_opportunity_directives(path), directives())
            with self.assertRaisesRegex(VisualOpportunityDirectiveStorageError, "不会覆盖"):
                save_visual_opportunity_directives(directives(), root)
            path.write_text(json.dumps({"artifact_version": "wrong"}), encoding="utf-8")
            with self.assertRaises(VisualOpportunityDirectiveStorageError):
                load_visual_opportunity_directives(path)


if __name__ == "__main__":
    unittest.main()
