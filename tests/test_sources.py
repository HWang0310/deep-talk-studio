import unittest

from deeptalk_studio.provenance import ProviderProvenance, SearchCall, UrlCitation, reconcile_provenance
from deeptalk_studio.sources import normalize_and_group_sources, normalize_url
from tests.fixtures import valid_report_data


class SourceNormalizationTests(unittest.TestCase):
    def test_normalize_url_removes_tracking_fragment_and_sorts_query(self):
        url = "HTTPS://Example.COM/news/?utm_source=x&b=2&a=1&fbclid=y#section"

        self.assertEqual(normalize_url(url), "https://example.com/news?a=1&b=2")

    def test_duplicate_canonical_urls_share_one_independence_group(self):
        sources = valid_report_data()["sources"]
        duplicate = dict(sources[0])
        duplicate.update(
            id="S3",
            url="https://example.com/official?utm_campaign=repost",
            normalized_url="https://incorrect.invalid",
            publisher="另一个页面名",
        )

        normalized = normalize_and_group_sources(sources + [duplicate])

        self.assertEqual(normalized[0]["independence_group"], normalized[2]["independence_group"])
        self.assertEqual(normalized[2]["independence_status"], "duplicate")
        self.assertEqual(normalized[2]["syndication_of"], "S1")

    def test_same_publisher_does_not_count_as_independent(self):
        sources = valid_report_data()["sources"]
        repeated = dict(sources[1])
        repeated.update(id="S3", url="https://example.org/follow-up", title="另一篇后续报道")

        normalized = normalize_and_group_sources(sources + [repeated])

        self.assertEqual(normalized[1]["independence_group"], normalized[2]["independence_group"])
        self.assertEqual(normalized[2]["independence_status"], "related")

    def test_same_title_across_publishers_is_marked_syndicated(self):
        sources = valid_report_data()["sources"]
        repost = dict(sources[1])
        repost.update(
            id="S3",
            url="https://mirror.example.net/copied-report",
            normalized_url="https://mirror.example.net/copied-report",
            publisher="转载站",
        )

        normalized = normalize_and_group_sources(sources + [repost])

        self.assertEqual(normalized[2]["independence_status"], "syndicated")
        self.assertEqual(normalized[2]["syndication_of"], "S2")
        self.assertEqual(normalized[1]["independence_group"], normalized[2]["independence_group"])

    def test_unresolved_independence_stays_unknown(self):
        source = dict(valid_report_data()["sources"][0])
        source["independence_status"] = "unknown"

        normalized = normalize_and_group_sources([source])

        self.assertEqual(normalized[0]["independence_status"], "unknown")


class ProvenanceReconciliationTests(unittest.TestCase):
    def test_api_sources_match_real_tool_sources_and_citations(self):
        data = valid_report_data()
        provenance = ProviderProvenance(
            search_calls=(
                SearchCall(
                    call_id="ws_1",
                    action_type="search",
                    queries=("示例公共事件",),
                    source_urls=("https://example.com/official?utm_source=search",),
                ),
            ),
            citations=(
                UrlCitation(
                    url="https://example.org/report",
                    title="媒体核查报道",
                    output_item_id="msg_1",
                    start_index=10,
                    end_index=20,
                ),
            ),
        )

        reconciled = reconcile_provenance(data, provenance)

        self.assertEqual(reconciled["sources"][0]["provenance_status"], "matched")
        self.assertIn("web_search_call:ws_1", reconciled["sources"][0]["provenance_refs"])
        self.assertEqual(reconciled["sources"][1]["provenance_method"], "url_citation")
        self.assertIn("url_citation:msg_1:10-20", reconciled["sources"][1]["provenance_refs"])

    def test_unmatched_api_source_is_downgraded_not_trusted(self):
        data = valid_report_data()
        provenance = ProviderProvenance(search_calls=(), citations=())

        reconciled = reconcile_provenance(data, provenance)

        self.assertTrue(all(source["provenance_status"] == "unmatched" for source in reconciled["sources"]))
        claim = next(item for item in reconciled["claims"] if item["id"] == "C1")
        self.assertEqual(claim["classification"], "unverified")
        self.assertEqual(claim["verification_status"], "unverified")


if __name__ == "__main__":
    unittest.main()
