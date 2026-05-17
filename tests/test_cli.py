from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path
import unittest

from .helpers import build_minimal_docx

from thesis_format_checker.cli import _print_summary, main
from thesis_format_checker.model import CheckResult, Issue, Severity


class CliSmokeTests(unittest.TestCase):
    def test_main_writes_report_for_minimal_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            rules_path = tmpdir_path / "rules.md"
            rules_path.write_text("# Requirements\n\n- Check the thesis.\n", encoding="utf-8")
            docx_path = build_minimal_docx(tmpdir_path / "thesis.docx")
            output_path = tmpdir_path / "reports" / "report.md"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main([str(rules_path), str(docx_path), "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("Report written to", stdout.getvalue())
            self.assertTrue(output_path.exists())

            report = output_path.read_text(encoding="utf-8")
            self.assertIn("# 毕业论文格式检查报告", report)
            self.assertIn(f"- 论文文件：`{docx_path}`", report)
            self.assertIn(f"- 规则文件：`{rules_path}`", report)
            self.assertNotIn("错误：", report)
            self.assertNotIn("### 错误", report)

    def test_json_summary_includes_error_and_skipped_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            rules_path = tmpdir_path / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["PAGE_SETUP"]},
  "page": {"margin_top_cm": 2.5}
}
```
""",
                encoding="utf-8",
            )
            docx_path = build_minimal_docx(tmpdir_path / "thesis.docx")
            output_path = tmpdir_path / "reports" / "report.md"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main(
                    [str(rules_path), str(docx_path), "--output", str(output_path), "--json-summary"]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            summary = json.loads(stdout.getvalue())
            self.assertIn("error", summary)
            self.assertIn("warning", summary)
            self.assertIn("info", summary)
            self.assertIn("skipped_items", summary)
            self.assertGreater(summary["skipped_items"], 0)

    def test_json_summary_total_includes_error_warning_info(self) -> None:
        output_path = Path("reports/report.md")
        result = CheckResult(
            issues=(
                Issue(code="ERR", severity=Severity.ERROR, message="error"),
                Issue(code="WARN", severity=Severity.WARNING, message="warning"),
                Issue(code="INFO", severity=Severity.INFO, message="info"),
            ),
            checked_items=("ERR",),
            skipped_items=("SKIP: disabled by the active school rules",),
        )

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            _print_summary(output_path, result, json_summary=True)

        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["error"], 1)
        self.assertEqual(summary["warning"], 1)
        self.assertEqual(summary["info"], 1)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["skipped_items"], 1)

    def test_readme_external_school_minimal_example_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            rules_path = tmpdir_path / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {
    "school_name": "某大学",
    "extends": "none"
  },
  "checks": {
    "enabled": ["page", "keywords"]
  },
  "page": {
    "margin_top_cm": 2.5,
    "margin_bottom_cm": 2.0,
    "margin_left_cm": 2.5,
    "margin_right_cm": 2.0
  },
  "keywords": {
    "en_label": "Key Words",
    "label_delimiter": "：",
    "separator": "；"
  }
}
```
""",
                encoding="utf-8",
            )
            docx_path = build_minimal_docx(tmpdir_path / "thesis.docx", body_text="Key Words：AI；RAG；商城")
            output_path = tmpdir_path / "reports" / "report.md"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main([str(rules_path), str(docx_path), "--output", str(output_path), "--json-summary"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertTrue(output_path.exists())
            summary = json.loads(stdout.getvalue())
            self.assertGreater(summary["checked_items"], 0)

    def test_main_reports_invalid_rules_config_without_unexpected_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            rules_path = tmpdir_path / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["NOT_A_CHECK"]}
}
```
""",
                encoding="utf-8",
            )
            docx_path = build_minimal_docx(tmpdir_path / "thesis.docx")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main([str(rules_path), str(docx_path)])

            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("error: invalid rules config:", stderr.getvalue())
            self.assertIn("NOT_A_CHECK", stderr.getvalue())
            self.assertNotIn("unexpected failure", stderr.getvalue())

    def test_main_returns_error_for_missing_docx(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            rules_path = tmpdir_path / "rules.md"
            rules_path.write_text("# Requirements\n", encoding="utf-8")
            missing_docx = tmpdir_path / "missing.docx"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main([str(rules_path), str(missing_docx)])

            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("error:", stderr.getvalue())

    def test_main_warns_when_rendered_header_check_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            expected_header = "武汉理工大学本科毕业设计（论文）"
            rules_path = tmpdir_path / "rules.md"
            rules_path.write_text(
                f"# Requirements\n\n- 正文页眉内容：`{expected_header}`。\n",
                encoding="utf-8",
            )
            docx_path = build_minimal_docx(
                tmpdir_path / "thesis.docx",
                header_text=expected_header,
            )
            output_path = tmpdir_path / "reports" / "report.md"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = main([str(rules_path), str(docx_path), "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")

            report = output_path.read_text(encoding="utf-8")
            self.assertNotIn("`HEADER_TEXT`", report)
            self.assertIn("`RENDERED_HEADER_CHECK_SKIPPED`", report)
            self.assertIn("requires --rendered-pdf", report)
