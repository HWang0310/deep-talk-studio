import unittest

from deeptalk_studio.migration import load_compatible_report, migrate_v01_to_v02
from deeptalk_studio.validation import ReportValidationError
from tests.fixtures import valid_v01_report_data


class MigrationTests(unittest.TestCase):
    def test_v01_migration_is_deterministic_and_keeps_history_safe(self):
        first = migrate_v01_to_v02(valid_v01_report_data())
        second = migrate_v01_to_v02(valid_v01_report_data())

        self.assertEqual(first["report_id"], second["report_id"])
        self.assertEqual(first["schema_version"], "0.2")
        self.assertEqual(first["revision"], 1)
        self.assertEqual(first["previous_revision"], 0)
        self.assertEqual(first["status"], "draft")
        self.assertEqual(first["research_mode"], "migration")
        self.assertEqual(first["fact_check"]["status"], "not_run")
        self.assertEqual(first["quality_summary"]["gate_status"], "fail")

    def test_v01_sources_and_claim_links_are_migrated_but_not_marked_verified(self):
        migrated = migrate_v01_to_v02(valid_v01_report_data())

        source = migrated["sources"][0]
        self.assertEqual(source["normalized_url"], "https://example.com/official")
        self.assertEqual(source["provenance_method"], "migration")
        self.assertEqual(source["provenance_status"], "unmatched")
        self.assertEqual(source["inspection_method"], "not_inspected")
        self.assertEqual(migrated["claims"][0]["verification_status"], "not_checked")
        self.assertEqual(migrated["evidence_links"][0]["relation"], "supports")
        self.assertFalse(migrated["evidence_links"][0]["verified_in_review"])

    def test_compatible_loader_reads_both_versions(self):
        report = load_compatible_report(valid_v01_report_data())

        self.assertEqual(report.schema_version, "0.2")
        self.assertEqual(report.research_mode, "migration")

    def test_invalid_v01_nested_source_is_rejected(self):
        data = valid_v01_report_data()
        del data["sources"][0]["publisher"]

        with self.assertRaisesRegex(ReportValidationError, "publisher"):
            migrate_v01_to_v02(data)


if __name__ == "__main__":
    unittest.main()
