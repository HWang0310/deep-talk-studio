import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.renderer import render_markdown
from tests.fixtures import valid_report_data


class RendererTests(unittest.TestCase):
    def test_rendered_report_exposes_classifications_sources_and_handoff(self):
        report = ResearchReport.from_dict(valid_report_data())

        markdown = render_markdown(report)

        self.assertIn("# Research Report：示例公共事件", markdown)
        self.assertIn("已确认事实", markdown)
        self.assertIn("当事人 / 当事机构说法", markdown)
        self.assertIn("尚未证实", markdown)
        self.assertIn("[机构公告](https://example.com/official)", markdown)
        self.assertIn("## 给 Script Agent 的交接", markdown)
        self.assertIn("不要断言人为操纵已经得到证实", markdown)


if __name__ == "__main__":
    unittest.main()

