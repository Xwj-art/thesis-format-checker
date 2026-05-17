from __future__ import annotations

from pathlib import Path
import unittest

from thesis_format_checker.model import CheckResult, DocumentInfo, Issue, RuleSet, Severity
from thesis_format_checker.report import render_markdown_report


class ReportTests(unittest.TestCase):
    def test_report_includes_skipped_items(self) -> None:
        document = DocumentInfo(path=Path("fixture.docx"))
        rules = RuleSet(source_path=Path("rules.md"), raw_markdown="")
        result = CheckResult(
            issues=(),
            checked_items=("PAGE_SETUP",),
            skipped_items=(
                "STRUCTURE_ABSTRACT_EN: not enabled by the active school rules",
                "TABLE_THREE_LINE: not enabled by the active school rules",
            ),
            unsupported_items=(),
        )

        report = render_markdown_report(document, rules, result)

        self.assertIn("## 已跳过项", report)
        self.assertIn("STRUCTURE_ABSTRACT_EN", report)
        self.assertIn("not enabled by the active school rules", report)

    def test_report_renders_error_section_when_errors_exist(self) -> None:
        document = DocumentInfo(path=Path("fixture.docx"))
        rules = RuleSet(source_path=Path("rules.md"), raw_markdown="")
        result = CheckResult(
            issues=(Issue(code="PDF_TEXT_EXTRACTOR", severity=Severity.ERROR, message="pdftotext failed."),),
            checked_items=("PDF_TEXT_EXTRACTOR",),
        )

        report = render_markdown_report(document, rules, result)

        self.assertIn("- 错误：1", report)
        self.assertIn("### 错误", report)
        self.assertIn("`PDF_TEXT_EXTRACTOR`", report)

    def test_report_checked_items_reflect_actual_execution_only(self) -> None:
        document = DocumentInfo(path=Path("fixture.docx"))
        rules = RuleSet(source_path=Path("rules.md"), raw_markdown="")
        result = CheckResult(
            issues=(),
            checked_items=("PAGE_SETUP",),
            skipped_items=("STRUCTURE_ABSTRACT_EN: not enabled by the active school rules",),
        )

        report = render_markdown_report(document, rules, result)
        checked_section = report.split("## 已检查项", 1)[1].split("## 已跳过项", 1)[0]

        self.assertIn("- PAGE_SETUP", checked_section)
        self.assertNotIn("STRUCTURE_ABSTRACT_EN", checked_section)


if __name__ == "__main__":
    unittest.main()
