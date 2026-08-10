import unittest

from deeptalk_studio.models import ResearchReport
from deeptalk_studio.renderer import render_markdown
from tests.fixtures import valid_report_data


class RendererTests(unittest.TestCase):
    def test_rendered_report_exposes_evidence_quality_risk_and_user_gate(self):
        report = ResearchReport.from_dict(valid_report_data())

        markdown = render_markdown(report)

        self.assertIn("# Research Report：示例公共事件", markdown)
        self.assertIn("报告 ID：RPT-20260810-example", markdown)
        self.assertIn("修订版：1", markdown)
        self.assertIn("## Evidence Ledger", markdown)
        self.assertIn("支持", markdown)
        self.assertIn("高风险", markdown)
        self.assertIn("## 研究质量 Gate", markdown)
        self.assertIn("主张来源覆盖率：100.0%", markdown)
        self.assertIn("## 用户审批 Gate", markdown)
        self.assertIn("C1", markdown)
        self.assertIn("[机构公告](https://example.com/official)", markdown)
        self.assertIn("不要断言人为操纵已经得到证实", markdown)


if __name__ == "__main__":
    unittest.main()
