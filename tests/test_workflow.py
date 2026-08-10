import tempfile
import unittest
from pathlib import Path

from deeptalk_studio.workflow import run_research
from tests.fixtures import valid_report_data


class FakeProvider:
    def __init__(self):
        self.received_topic = None

    def research(self, topic, schema):
        self.received_topic = topic
        data = valid_report_data()
        data["topic"] = topic
        return data


class WorkflowTests(unittest.TestCase):
    def test_topic_runs_provider_validation_and_storage(self):
        provider = FakeProvider()

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = run_research("人工智能就业影响", provider, Path(temp_dir))

            self.assertEqual(provider.received_topic, "人工智能就业影响")
            self.assertTrue(paths.markdown.exists())
            self.assertTrue(paths.json.exists())

    def test_empty_topic_is_rejected_before_provider_call(self):
        provider = FakeProvider()

        with self.assertRaisesRegex(ValueError, "主题不能为空"):
            run_research("   ", provider, Path("reports"))

        self.assertIsNone(provider.received_topic)


if __name__ == "__main__":
    unittest.main()

