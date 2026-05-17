from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path
import unittest

from .helpers import build_minimal_docx

from thesis_format_checker.cli import main


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

    def test_json_summary_omits_error_metric(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            rules_path = tmpdir_path / "rules.md"
            rules_path.write_text("# Requirements\n", encoding="utf-8")
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
            self.assertNotIn("error", summary)
            self.assertIn("warning", summary)
            self.assertIn("info", summary)

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
