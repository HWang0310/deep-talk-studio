"""Opt-in live smoke test for the Phase 1 Bilibili reference discovery.

Never runs by default and must not run in CI. Enable with:

    DEEPTALK_LIVE_BILI_SMOKE=1 PYTHONPATH=src:. \
        python3 -m unittest tests.test_reference_discovery_live

The run is bounded: one topic, default query plan, default rate limits,
anonymous access only. It verifies real-world searchability, artifact
validation, and that no visitor identifier is ever serialized.
"""

import json
import os
import unittest

from deeptalk_studio.bilibili_reference_provider import BilibiliReferenceProvider
from deeptalk_studio.reference_discovery import (
    build_reference_candidate_set,
    validate_reference_candidate_set,
)

LIVE_ENV_FLAG = "DEEPTALK_LIVE_BILI_SMOKE"
SMOKE_TOPIC = "莫斯科大学留学生旭日旗事件"


@unittest.skipUnless(os.environ.get(LIVE_ENV_FLAG) == "1", "live smoke is opt-in only")
class LiveBilibiliDiscoverySmokeTests(unittest.TestCase):
    def test_real_topic_discovery_produces_valid_artifact(self):
        provider = BilibiliReferenceProvider()  # anonymous visitor bootstrap
        artifact = build_reference_candidate_set(
            SMOKE_TOPIC, (), provider=provider, aliases=("莫斯科大学 旭日旗 遣返",)
        )
        validate_reference_candidate_set(artifact)
        self.assertIn(artifact["status"], ("ok", "degraded", "blocked"))
        self.assertGreaterEqual(artifact["search"]["raw_result_count"], 0)

        serialized = json.dumps(artifact, ensure_ascii=False)
        # the anonymous visitor identifier must never be persisted or logged
        self.assertNotIn("buvid3=", serialized)
        self.assertNotIn("b_3", serialized)

        if artifact["status"] == "ok":
            self.assertGreaterEqual(len(artifact["candidates"]), 1)
            for candidate in artifact["candidates"]:
                self.assertIn(candidate["view_count_status"], ("verified", "unverified"))
            verified = [c for c in artifact["candidates"] if c["view_count_status"] == "verified"]
            views = [c["view_count"] for c in verified]
            self.assertEqual(views, sorted(views, reverse=True))
            print(f"[live-smoke] status={artifact['status']} "
                  f"candidates={len(artifact['candidates'])} "
                  f"raw={artifact['search']['raw_result_count']} "
                  f"dedup={artifact['search']['deduplicated_count']}")
            for candidate in artifact["candidates"]:
                print(f"[live-smoke] {candidate['bvid']} | "
                      f"{(candidate['title'] or '')[:40]} | "
                      f"views={candidate['view_count']} ({candidate['view_count_status']})")
        else:
            print(f"[live-smoke] status={artifact['status']} note={artifact['action_note']}")


if __name__ == "__main__":
    unittest.main()
