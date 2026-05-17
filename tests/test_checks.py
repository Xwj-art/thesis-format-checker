from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from thesis_format_checker.checks import (
    _check_body_typography,
    _check_captions,
    _check_caption_object_order,
    _check_continued_table_layout,
    _check_registry,
    _check_header_text,
    _check_headings,
    _check_heading_script_fonts,
    _check_keywords,
    _check_major_heading_spacing,
    _check_mixed_language_spacing,
    _check_numbering,
    _check_reference_citations,
    _check_reference_typography,
    _check_structure_presence,
    _check_static_headers_and_page_numbers,
    _check_table_borders,
    _check_table_cell_typography,
    run_checks,
)
from thesis_format_checker.model import DocumentInfo, ParagraphInfo, RuleSet, RunInfo, SectionInfo, Severity, TableInfo
from thesis_format_checker.rules import load_rules


class ChecksTests(unittest.TestCase):
    def _load_rules_from_json(self, json_body: str) -> RuleSet:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                f"""# Requirements

```json thesis-format-rules
{json_body}
```
""",
                encoding="utf-8",
            )
            return load_rules(rules_path)

    def test_header_text_requires_undergraduate_wording(self) -> None:
        rules = RuleSet(
            source_path=Path("rules.md"),
            raw_markdown="",
            expected_header_text="武汉理工大学本科毕业设计（论文）",
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            headers=("武汉理工大学毕业设计（论文）",),
        )

        issues = _check_header_text(document, rules)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "HEADER_TEXT")

    def test_header_text_accepts_expected_undergraduate_wording(self) -> None:
        rules = RuleSet(
            source_path=Path("rules.md"),
            raw_markdown="",
            expected_header_text="武汉理工大学本科毕业设计（论文）",
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            headers=("武汉理工大学本科毕业设计（论文）",),
        )

        issues = _check_header_text(document, rules)

        self.assertEqual(issues, [])

    def test_static_header_line_accepts_template_bottom_border(self) -> None:
        rules = RuleSet(
            source_path=Path("rules.md"),
            raw_markdown="",
            expected_header_text="武汉理工大学本科毕业设计（论文）",
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            sections=(
                SectionInfo(
                    index=0,
                    header_texts=("武汉理工大学本科毕业设计（论文）",),
                    header_border_positions=("bottom",),
                    header_bottom_border_sizes=(6,),
                    header_bottom_border_spaces=(1,),
                ),
            ),
        )

        issues = _check_static_headers_and_page_numbers(document, rules)

        codes = {issue.code for issue in issues}
        self.assertNotIn("HEADER_LINE_POSITION", codes)
        self.assertNotIn("HEADER_LINE_WIDTH", codes)

    def test_static_header_line_flags_wrong_position_and_width(self) -> None:
        rules = RuleSet(
            source_path=Path("rules.md"),
            raw_markdown="",
            expected_header_text="武汉理工大学本科毕业设计（论文）",
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            sections=(
                SectionInfo(
                    index=0,
                    header_texts=("武汉理工大学本科毕业设计（论文）",),
                    header_border_positions=("top",),
                    header_bottom_border_sizes=(4,),
                    header_bottom_border_spaces=(2,),
                ),
            ),
        )

        issues = _check_static_headers_and_page_numbers(document, rules)
        codes = {issue.code for issue in issues}

        self.assertIn("HEADER_LINE_POSITION", codes)
        self.assertIn("HEADER_LINE_WIDTH", codes)

    def test_major_heading_spacing_accepts_template_text(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=1, text="摘  要"),
                ParagraphInfo(index=2, text="目　　录"),
                ParagraphInfo(index=3, text="参考文献"),
                ParagraphInfo(index=4, text="致  谢"),
            ),
        )

        issues = _check_major_heading_spacing(document)

        self.assertEqual(issues, [])

    def test_major_heading_spacing_flags_half_width_toc_spaces(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=1, text="目  录"),),
        )

        issues = _check_major_heading_spacing(document)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "MAJOR_HEADING_SPACING")
        self.assertEqual(issues[0].expected, "目　　录")

    def test_caption_separator_and_line_spacing_are_checked(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="图3-1  系统架构图",
            alignment="center",
            line_spacing_multiple=1.5,
            line_spacing_rule="auto",
            runs=(
                RunInfo(text="图3-1  系统架构图", font_east_asia="宋体", font_ascii="宋体", size_pt=12.0),
            ),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_captions(document)
        codes = {issue.code for issue in issues}

        self.assertIn("CAPTION_SEPARATOR", codes)
        self.assertIn("CAPTION_LINE_SPACING", codes)

    def test_continued_table_caption_uses_same_separator_rule(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="续表5-1  环境测试配置表",
            alignment="center",
            line_spacing_pt=20.0,
            line_spacing_rule="exact",
            runs=(RunInfo(text="续表5-1  环境测试配置表", font_east_asia="宋体", size_pt=12.0),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_captions(document)

        self.assertTrue(any(issue.code == "CAPTION_SEPARATOR" for issue in issues))

    def test_caption_format_checks_ascii_font_as_songti(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="图3-1 E-R图",
            alignment="center",
            line_spacing_pt=20.0,
            line_spacing_rule="exact",
            runs=(RunInfo(text="图3-1 E-R图", font_east_asia="宋体", font_ascii="Times New Roman", size_pt=12.0),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_captions(document)

        self.assertTrue(any(issue.code == "CAPTION_FORMAT" for issue in issues))

    def test_caption_format_checks_number_part_as_songti(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="图2-1 系统架构图",
            alignment="center",
            line_spacing_pt=20.0,
            line_spacing_rule="exact",
            runs=(
                RunInfo(text="图", font_east_asia="宋体", font_ascii="宋体", size_pt=12.0),
                RunInfo(text="2-1", font_ascii="Times New Roman", font_east_asia="宋体", size_pt=12.0),
                RunInfo(text=" 系统架构图", font_east_asia="宋体", font_ascii="宋体", size_pt=12.0),
            ),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_captions(document)

        self.assertTrue(any(issue.code == "CAPTION_FORMAT" for issue in issues))

    def test_caption_format_rejects_first_line_indent(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="表2-1 实验结果",
            alignment="center",
            first_line_indent_chars=2.0,
            line_spacing_pt=20.0,
            line_spacing_rule="exact",
            runs=(RunInfo(text="表2-1 实验结果", font_east_asia="宋体", font_ascii="宋体", size_pt=12.0),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_captions(document)

        self.assertTrue(any(issue.code == "CAPTION_FORMAT" and "indent" in issue.message for issue in issues))

    def test_mixed_language_spacing_flags_spaces_in_body_text(self) -> None:
        paragraph = ParagraphInfo(index=1, text="本文基于 Spring AI 实现智能客服。")
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_mixed_language_spacing(document)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "MIXED_LANGUAGE_SPACING")

    def test_mixed_language_spacing_accepts_natural_adjacent_text(self) -> None:
        paragraph = ParagraphInfo(index=1, text="本文基于Spring AI实现智能客服。")
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_mixed_language_spacing(document)

        self.assertEqual(issues, [])

    def test_mixed_language_spacing_ignores_headings(self) -> None:
        paragraph = ParagraphInfo(index=1, text="1.1 Spring AI研究背景")
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_mixed_language_spacing(document)

        self.assertEqual(issues, [])

    def test_mixed_language_spacing_ignores_dates_and_chapter_numbers(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=1, text="作者签名：张三    2026年5月11日"),
                ParagraphInfo(index=2, text="第1章绪论部分介绍研究背景。"),
            ),
        )

        issues = _check_mixed_language_spacing(document)

        self.assertEqual(issues, [])

    def test_mixed_language_spacing_ignores_caption_text(self) -> None:
        paragraph = ParagraphInfo(index=1, text="图5-9 AI短问题或模糊问题边界测试图")
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_mixed_language_spacing(document)

        self.assertEqual(issues, [])

    def test_numbering_ignores_metric_decimals_in_parentheses(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="Sparse-only取得最高检索指标（Hit@5=0.8597），Hybrid次之（0.8489）。",
        )

        issues = _check_numbering(paragraph)

        self.assertFalse(any(issue.code == "EQUATION_NUMBERING" for issue in issues))

    def test_numbering_flags_dot_style_equation_numbers(self) -> None:
        paragraph = ParagraphInfo(index=1, text="E = mc^2 （6.1）")

        issues = _check_numbering(paragraph)

        self.assertTrue(any(issue.code == "EQUATION_NUMBERING" for issue in issues))

    def test_keywords_flag_english_label_colon_and_space_format(self) -> None:
        paragraph = ParagraphInfo(index=1, text="Key Words : Spring AI；RAG；商城")
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_keywords(document)

        self.assertTrue(any(issue.code == "KEYWORD_LABEL_FORMAT" for issue in issues))

    def test_keywords_accept_configured_english_label_with_chinese_colon(self) -> None:
        paragraph = ParagraphInfo(index=1, text="Key Words：Spring AI；RAG；商城")
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_keywords(document)

        self.assertFalse(any(issue.code == "KEYWORD_LABEL_FORMAT" for issue in issues))

    def test_reference_citations_accept_superscript_cross_reference(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="相关研究见[1]。",
            field_instructions=("REF _Ref123456 \\r \\h",),
            runs=(
                RunInfo(text="相关研究见"),
                RunInfo(text="[1]", vertical_align="superscript"),
                RunInfo(text="。"),
            ),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="第1章 绪论"),
                paragraph,
                ParagraphInfo(index=2, text="参考文献"),
                ParagraphInfo(index=3, text="[1] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
            ),
        )

        issues = _check_reference_citations(document)

        self.assertEqual(issues, [])

    def test_reference_citations_flag_plain_text_not_superscript_or_field(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="相关研究见[1]。",
            runs=(RunInfo(text="相关研究见[1]。"),),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="第1章 绪论"),
                paragraph,
                ParagraphInfo(index=2, text="参考文献"),
                ParagraphInfo(index=3, text="[1] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
            ),
        )

        issues = _check_reference_citations(document)
        codes = {issue.code for issue in issues}

        self.assertIn("REFERENCE_CITATION_FORMAT", codes)
        self.assertIn("REFERENCE_CITATION_FIELD", codes)

    def test_reference_citations_flag_ascii_comma_inside_superscript(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="相关研究见[1,2]。",
            field_instructions=("REF _Ref123456 \\r \\h",),
            runs=(
                RunInfo(text="相关研究见"),
                RunInfo(text="[1,2]", vertical_align="superscript"),
                RunInfo(text="。"),
            ),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="第1章 绪论"),
                paragraph,
                ParagraphInfo(index=2, text="参考文献"),
                ParagraphInfo(index=3, text="[1] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
                ParagraphInfo(index=4, text="[2] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
            ),
        )

        issues = _check_reference_citations(document)

        self.assertTrue(any(issue.code == "REFERENCE_CITATION_SEPARATOR" for issue in issues))

    def test_reference_citations_accept_chinese_comma_inside_superscript(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="相关研究见[1，2]。",
            field_instructions=("REF _Ref123456 \\r \\h",),
            runs=(
                RunInfo(text="相关研究见"),
                RunInfo(text="[1，2]", vertical_align="superscript"),
                RunInfo(text="。"),
            ),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="第1章 绪论"),
                paragraph,
                ParagraphInfo(index=2, text="参考文献"),
                ParagraphInfo(index=3, text="[1] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
                ParagraphInfo(index=4, text="[2] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
            ),
        )

        issues = _check_reference_citations(document)

        self.assertFalse(any(issue.code == "REFERENCE_CITATION_SEPARATOR" for issue in issues))

    def test_reference_citations_flag_uncited_reference_entry(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="第1章 绪论"),
                ParagraphInfo(index=1, text="正文没有引用。"),
                ParagraphInfo(index=2, text="参考文献"),
                ParagraphInfo(index=3, text="[1] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
            ),
        )

        issues = _check_reference_citations(document)

        self.assertTrue(
            any(issue.code == "REFERENCE_CITATION_TARGET" and issue.severity is Severity.INFO for issue in issues)
        )

    def test_custom_markdown_structure_controls_reference_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                r"""# Requirements

```json thesis-format-rules
{
  "structure": {
    "headings": {
      "abstract_cn": ["中文概要"],
      "abstract_en": ["Summary"],
      "toc": ["Contents"],
      "reference": ["Works Cited"],
      "thanks": ["Acknowledgments"],
      "terminal": ["Acknowledgments", "Appendix"]
    },
    "patterns": {
      "body_start": "^Chapter\\s+1\\b",
      "heading_level_1": "^Chapter\\s+\\d+(?:\\s+.+)?$"
    },
    "required": {
      "STRUCTURE_ABSTRACT_CN": ["中文概要", "Chinese abstract heading was not detected."],
      "STRUCTURE_ABSTRACT_EN": ["Summary", "English abstract heading was not detected."],
      "STRUCTURE_TOC": ["Contents", "Table of contents heading was not detected."],
      "STRUCTURE_BODY_START": ["Chapter 1", "Chapter 1 heading was not detected."],
      "STRUCTURE_REFERENCES": ["Works Cited", "References heading was not detected."],
      "STRUCTURE_THANKS": ["Acknowledgments", "Acknowledgements heading was not detected."]
    }
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            paragraph = ParagraphInfo(
                index=5,
                text="Prior work is discussed in [1].",
                field_instructions=("REF _Ref123456 \\r \\h",),
                runs=(
                    RunInfo(text="Prior work is discussed in "),
                    RunInfo(text="[1]", vertical_align="superscript"),
                    RunInfo(text="."),
                ),
            )
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="中文概要"),
                    ParagraphInfo(index=1, text="Summary"),
                    ParagraphInfo(index=2, text="Contents"),
                    ParagraphInfo(index=3, text="Chapter 1 Introduction"),
                    paragraph,
                    ParagraphInfo(index=6, text="Works Cited"),
                    ParagraphInfo(index=7, text="[1] Author. Title[J]. Journal, 2024."),
                    ParagraphInfo(index=8, text="Acknowledgments"),
                ),
            )

            structure_issues = _check_structure_presence(document, rules)
            citation_issues = _check_reference_citations(document, rules)

            self.assertEqual(structure_issues, [])
            self.assertFalse(any(issue.code == "REFERENCE_CITATION_TARGET" for issue in citation_issues))

    def test_extends_none_page_setup_only_skips_unrelated_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["PAGE_SETUP"]},
  "tolerances": {"page_cm": 0.1},
  "page": {"margin_top_cm": 2.5}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                sections=(SectionInfo(index=0, margin_top_cm=3.0),),
                paragraphs=(
                    ParagraphInfo(index=0, text="Title page"),
                    ParagraphInfo(index=1, text="Body paragraph without school-specific structure."),
                ),
            )

            result = run_checks(document, rules)
            codes = {issue.code for issue in result.issues}

            self.assertEqual(codes, {"PAGE_SETUP"})
            self.assertIn("PAGE_SETUP", result.checked_items)
            self.assertNotIn("STRUCTURE_ABSTRACT_EN", result.checked_items)
            self.assertTrue(any("STRUCTURE_ABSTRACT_EN" in item for item in result.skipped_items))
            self.assertTrue(any("KEYWORD_LABEL_FORMAT" in item for item in result.skipped_items))

    def test_disabled_check_suppresses_whut_inherited_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "builtin-whut-v1"},
  "checks": {"disabled": ["STRUCTURE_THANKS"]}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="摘  要"),
                    ParagraphInfo(index=1, text="Abstract"),
                    ParagraphInfo(index=2, text="目录"),
                    ParagraphInfo(index=3, text="第1章 绪论"),
                    ParagraphInfo(index=4, text="参考文献"),
                ),
            )

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code == "STRUCTURE_THANKS" for issue in result.issues))
            self.assertTrue(any("STRUCTURE_THANKS" in item for item in result.skipped_items))

    def test_keywords_enabled_group_runs_only_keyword_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["keywords"]},
  "keywords": {
    "min_count": 3,
    "max_count": 5,
    "cn_label": "关键词",
    "en_label": "Key Words",
    "label_delimiter": "：",
    "allow_space_before_delimiter": false,
    "allow_space_after_delimiter": false,
    "separator": "；",
    "forbid_trailing_separator": true
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                sections=(SectionInfo(index=0, margin_top_cm=3.0),),
                paragraphs=(ParagraphInfo(index=0, text="Key Words: alpha; beta"),),
            )

            result = run_checks(document, rules)
            codes = {issue.code for issue in result.issues}

            self.assertTrue(codes)
            self.assertTrue(all(code.startswith("KEYWORD_") for code in codes))
            self.assertIn("KEYWORD_LABEL_FORMAT", codes)
            self.assertNotIn("PAGE_SETUP", codes)
            self.assertFalse(any(code.startswith("STRUCTURE_") for code in codes))

    def test_custom_english_structure_body_range_used_by_body_typography(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                r"""# Requirements

```json thesis-format-rules
{
  "structure": {
    "headings": {
      "reference": ["References"]
    },
    "patterns": {
      "body_start": "^Chapter\\s+1\\b",
      "heading_level_1": "^Chapter\\s+\\d+(?:\\s+.+)?$"
    }
  },
  "body": {
    "first_line_indent_chars": 2.0,
    "space_before_pt": 0.0,
    "space_after_pt": 0.0,
    "size_pt": 12.0,
    "east_asia": "宋体",
    "ascii": "Times New Roman"
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            cover = ParagraphInfo(
                index=0,
                text="Cover page text",
                first_line_indent_chars=0.0,
                runs=(RunInfo(text="Cover page text", font_ascii="Times New Roman", size_pt=12.0),),
            )
            body = ParagraphInfo(
                index=2,
                text="This body paragraph should be checked.",
                first_line_indent_chars=0.0,
                space_before_pt=0.0,
                space_after_pt=0.0,
                runs=(
                    RunInfo(
                        text="This body paragraph should be checked.",
                        font_ascii="Times New Roman",
                        size_pt=12.0,
                    ),
                ),
            )
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    cover,
                    ParagraphInfo(index=1, text="Chapter 1 Introduction"),
                    body,
                    ParagraphInfo(index=3, text="References"),
                ),
            )

            issues = _check_body_typography(document, rules)

            self.assertTrue(any(issue.code == "BODY_INDENT" and issue.evidence == body.text for issue in issues))
            self.assertFalse(any(issue.evidence == cover.text for issue in issues))

    def test_no_english_abstract_when_not_required_does_not_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                r"""# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["structure"]},
  "structure": {
    "headings": {
      "abstract_cn": ["摘要"]
    },
    "patterns": {
      "body_start": "^第\\s*1\\s*章\\b"
    },
    "required": {
      "STRUCTURE_ABSTRACT_CN": ["摘要", "Chinese abstract heading was not detected."],
      "STRUCTURE_BODY_START": ["第1章", "Chapter 1 heading was not detected."]
    }
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="摘要"),
                    ParagraphInfo(index=1, text="第1章 绪论"),
                ),
            )

            issues = _check_structure_presence(document, rules)

            self.assertFalse(any(issue.code == "STRUCTURE_ABSTRACT_EN" for issue in issues))
            self.assertEqual(issues, [])

    def test_toc_heading_with_toc_style_is_still_detected_as_structure_heading(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="摘  要"),
                ParagraphInfo(index=1, text="Abstract"),
                ParagraphInfo(index=2, text="目　　录", style="TOC10", style_name="TOC 标题1"),
                ParagraphInfo(index=3, text="第1章 绪论"),
                ParagraphInfo(index=4, text="参考文献"),
                ParagraphInfo(index=5, text="致  谢"),
            ),
        )

        issues = _check_structure_presence(document)

        self.assertFalse(any(issue.code == "STRUCTURE_TOC" for issue in issues))

    def test_extends_none_enabled_body_without_body_config_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["body"]}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(ParagraphInfo(index=0, text="A body paragraph."),),
            )

            result = run_checks(document, rules)

            self.assertEqual(result.issues, ())
            self.assertNotIn("BODY_INDENT", result.checked_items)
            self.assertTrue(any("BODY_INDENT" in item and "missing config" in item for item in result.skipped_items))

    def test_checks_enabled_unknown_item_reports_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
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
            rules = load_rules(rules_path)

            with self.assertRaisesRegex(ValueError, "NOT_A_CHECK"):
                run_checks(DocumentInfo(path=Path("fixture.docx")), rules)

    def test_checks_config_wrong_type_reports_config_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": "page"}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)

            with self.assertRaisesRegex(ValueError, "checks\\.enabled"):
                run_checks(DocumentInfo(path=Path("fixture.docx")), rules)

    def test_table_checks_can_be_disabled_for_grid_table_school(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "checks": {"disabled": ["tables"]}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
                tables=(
                    TableInfo(
                        index=1,
                        block_index=1,
                        rows=(("字段", "说明"), ("name", "商品名称")),
                        border_values=("top=single", "bottom=single", "insideH=single", "insideV=single"),
                        has_vertical_borders=True,
                    ),
                ),
            )

            result = run_checks(document, rules)
            codes = {issue.code for issue in result.issues}

            self.assertNotIn("TABLE_BORDER", codes)
            self.assertNotIn("TABLE_THREE_LINE", codes)
            self.assertTrue(any("TABLE_BORDER" in item and "disabled" in item for item in result.skipped_items))

    def test_mixed_language_spacing_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "checks": {"disabled": ["mixed_language"]}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="第1章 绪论"),
                    ParagraphInfo(index=1, text="本文基于 Spring AI 实现智能客服。"),
                ),
            )

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code == "MIXED_LANGUAGE_SPACING" for issue in result.issues))
            self.assertTrue(any("MIXED_LANGUAGE_SPACING" in item and "disabled" in item for item in result.skipped_items))

    def test_toc_field_check_can_be_disabled_for_manual_toc_school(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "checks": {"disabled": ["toc"]}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="目录"),
                    ParagraphInfo(index=1, text="第1章 绪论"),
                ),
            )

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code == "TOC_FIELD" for issue in result.issues))
            self.assertTrue(any("TOC_FIELD" in item and "disabled" in item for item in result.skipped_items))

    def test_reference_field_check_can_be_disabled_for_manual_citation_school(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "checks": {"disabled": ["REFERENCE_CITATION_FIELD"]}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            paragraph = ParagraphInfo(
                index=1,
                text="相关研究见[1]。",
                runs=(
                    RunInfo(text="相关研究见"),
                    RunInfo(text="[1]", vertical_align="superscript"),
                    RunInfo(text="。"),
                ),
            )
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="第1章 绪论"),
                    paragraph,
                    ParagraphInfo(index=2, text="参考文献"),
                    ParagraphInfo(index=3, text="[1] 作者. 题名[J]. 期刊,2024,1(1):1-2."),
                ),
            )

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code == "REFERENCE_CITATION_FIELD" for issue in result.issues))
            self.assertTrue(
                any("REFERENCE_CITATION_FIELD" in item and "disabled" in item for item in result.skipped_items)
            )

    def test_figure_dot_numbering_allowed_when_numbering_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "checks": {"disabled": ["numbering"]}
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="第1章 绪论"),
                    ParagraphInfo(index=1, text="图 1.1 系统结构"),
                ),
            )

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code == "FIGURE_NUMBERING" for issue in result.issues))
            self.assertTrue(any("FIGURE_NUMBERING" in item and "disabled" in item for item in result.skipped_items))

    def test_keywords_custom_count_and_separator(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["keywords"]},
  "keywords": {
    "min_count": 2,
    "max_count": 2,
    "cn_label": "关键词",
    "en_label": "Keywords",
    "label_delimiter": ":",
    "allow_space_before_delimiter": false,
    "allow_space_after_delimiter": true,
    "separator": ";",
    "forbid_trailing_separator": false
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(ParagraphInfo(index=0, text="Keywords: AI; RAG"),))

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code.startswith("KEYWORD_") for issue in result.issues))
            self.assertIn("KEYWORD_COUNT", result.checked_items)

    def test_keywords_allow_trailing_separator_when_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["keywords"]},
  "keywords": {
    "min_count": 2,
    "max_count": 3,
    "cn_label": "关键词",
    "en_label": "Keywords",
    "label_delimiter": ":",
    "allow_space_before_delimiter": false,
    "allow_space_after_delimiter": true,
    "separator": ";",
    "forbid_trailing_separator": false
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(ParagraphInfo(index=0, text="Keywords: AI; RAG;"),))

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code == "KEYWORD_TERMINATOR" for issue in result.issues))

    def test_body_partial_config_skips_missing_subfield_checks_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["body"]},
  "body": {
    "size_pt": 12.0,
    "east_asia": "宋体",
    "ascii": "Times New Roman"
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(ParagraphInfo(index=0, text="正文内容", runs=(RunInfo(text="正文内容", size_pt=12.0),)),),
            )

            result = run_checks(document, rules)

            self.assertFalse(any(issue.code in {"BODY_INDENT", "BODY_SPACING"} for issue in result.issues))
            self.assertIn("BODY_FONT", result.checked_items)
            self.assertTrue(any("BODY_INDENT" in item and "missing config" in item for item in result.skipped_items))

    def test_header_text_only_config_skips_header_line_checks_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["header"]},
  "header": {
    "body_text": "某大学本科毕业论文"
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(path=Path("fixture.docx"), headers=("其他页眉",))

            result = run_checks(document, rules)

            self.assertTrue(any(issue.code == "HEADER_TEXT" for issue in result.issues))
            self.assertNotIn("HEADER_LINE_WIDTH", result.checked_items)
            self.assertTrue(any("HEADER_LINE_WIDTH" in item and "missing config" in item for item in result.skipped_items))

    def test_reference_separator_only_config_skips_unconfigured_reference_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["REFERENCE_CITATION_SEPARATOR"]},
  "structure": {
    "patterns": {
      "body_start": "^第\\\\s*1\\\\s*章\\\\b"
    },
    "headings": {
      "reference": ["参考文献"]
    }
  },
  "reference": {
    "citation_separator": "，"
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            paragraph = ParagraphInfo(
                index=1,
                text="相关研究见[1,2]。",
                field_instructions=("REF _Ref123456 \\r \\h",),
                runs=(
                    RunInfo(text="相关研究见"),
                    RunInfo(text="[1,2]", vertical_align="superscript"),
                    RunInfo(text="。"),
                ),
            )
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="第1章 绪论"),
                    paragraph,
                    ParagraphInfo(index=2, text="参考文献"),
                    ParagraphInfo(index=3, text="[1] 作者. 题名[J]. 期刊,2024."),
                    ParagraphInfo(index=4, text="[2] 作者. 题名[J]. 期刊,2024."),
                ),
            )

            result = run_checks(document, rules)

            self.assertTrue(any(issue.code == "REFERENCE_CITATION_SEPARATOR" for issue in result.issues))
            self.assertEqual(result.checked_items, ("REFERENCE_CITATION_SEPARATOR",))

    def test_body_font_selector_runs_without_body_indent_or_spacing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["BODY_FONT"]},
  "body": {
    "size_pt": 12.0,
    "east_asia": "宋体",
    "ascii": "Times New Roman"
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(
                        index=0,
                        text="正文内容",
                        runs=(RunInfo(text="正文内容", font_east_asia="黑体", size_pt=12.0),),
                    ),
                ),
            )

            result = run_checks(document, rules)

            self.assertEqual(result.checked_items, ("BODY_FONT",))
            self.assertTrue(any(issue.code == "BODY_FONT" for issue in result.issues))
            self.assertFalse(any(item.startswith("BODY_FONT: missing config") for item in result.skipped_items))

    def test_table_cell_font_selector_runs_without_three_line_table_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["TABLE_CELL_FONT"]},
  "structure": {
    "patterns": {
      "body_start": "^第\\\\s*1\\\\s*章\\\\b"
    },
    "headings": {
      "reference": ["参考文献"]
    }
  },
  "table": {
    "cell_size_pt": 12.0,
    "cell_east_asia": "宋体",
    "cell_ascii": "Times New Roman"
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            table_paragraph = ParagraphInfo(
                index=1,
                text="单元格",
                runs=(RunInfo(text="单元格", font_east_asia="黑体", size_pt=12.0),),
            )
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
                tables=(
                    TableInfo(
                        index=1,
                        block_index=1,
                        rows=(("字段", "说明"), ("name", "商品名称")),
                        paragraphs=(table_paragraph,),
                    ),
                ),
            )

            result = run_checks(document, rules)

            self.assertEqual(result.checked_items, ("TABLE_CELL_FONT",))
            self.assertTrue(any(issue.code == "TABLE_CELL_FONT" for issue in result.issues))
            self.assertFalse(any(issue.code in {"TABLE_BORDER", "TABLE_THREE_LINE"} for issue in result.issues))

    @unittest.expectedFailure
    def test_each_single_check_selector_with_empty_school_config_skips_instead_of_crashing(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, block_index=0, text="正文段落"),
                ParagraphInfo(index=1, block_index=1, text=""),
                ParagraphInfo(index=2, block_index=2, text=""),
            ),
            tables=(
                TableInfo(
                    index=1,
                    block_index=3,
                    rows=(("字段", "说明"), ("name", "商品名称")),
                ),
            ),
        )
        item_codes = [item for _group, items, _runner in _check_registry() for item in items]

        for item_code in item_codes:
            with self.subTest(item_code=item_code):
                rules = self._load_rules_from_json(
                    f"""{{
  "profile": {{"extends": "none"}},
  "checks": {{"enabled": ["{item_code}"]}}
}}"""
                )

                result = run_checks(document, rules)

                self.assertTrue(
                    item_code in result.checked_items
                    or any(item.startswith(f"{item_code}:") for item in result.skipped_items)
                )

    @unittest.expectedFailure
    def test_heading_punctuation_selector_runs_with_minimal_punctuation_config(self) -> None:
        rules = self._load_rules_from_json(
            """{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["HEADING_PUNCTUATION"]},
  "structure": {
    "patterns": {
      "heading_level_1": "^第\\\\s*\\\\d+\\\\s*章(?:\\\\s+.+)?$",
      "heading_level_2": "^\\\\d+\\\\.\\\\d+(?:\\\\s+.+)?$",
      "heading_level_3": "^\\\\d+\\\\.\\\\d+\\\\.\\\\d+(?:\\\\s+.+)?$"
    }
  },
  "heading": {
    "punctuation_suffix": "：:"
  }
}"""
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, text="第1章 绪论："),),
        )

        result = run_checks(document, rules)

        self.assertEqual(result.checked_items, ("HEADING_PUNCTUATION",))
        self.assertTrue(any(issue.code == "HEADING_PUNCTUATION" for issue in result.issues))

    @unittest.expectedFailure
    def test_caption_separator_selector_runs_with_minimal_separator_config(self) -> None:
        rules = self._load_rules_from_json(
            """{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["CAPTION_SEPARATOR"]},
  "caption": {
    "separator": " "
  },
  "numbering": {
    "caption_prefix_pattern": "^(?:图|表|续表)\\\\s*\\\\d+-\\\\d+(?:\\\\s+|$)",
    "caption_pattern": "^(图|表|续表)\\\\s*(\\\\d+-\\\\d+)(\\\\s+)(.+)$"
  }
}"""
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, text="图3-1  系统架构图"),),
        )

        result = run_checks(document, rules)

        self.assertEqual(result.checked_items, ("CAPTION_SEPARATOR",))
        self.assertTrue(any(issue.code == "CAPTION_SEPARATOR" for issue in result.issues))

    @unittest.expectedFailure
    def test_figure_caption_position_selector_runs_without_caption_typography_config(self) -> None:
        rules = self._load_rules_from_json(
            """{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["FIGURE_CAPTION_POSITION"]},
  "structure": {
    "patterns": {
      "body_start": "^第\\\\s*1\\\\s*章\\\\b"
    },
    "headings": {
      "reference": ["参考文献"],
      "terminal": []
    }
  },
  "numbering": {
    "figure_caption_pattern": "^图\\\\s*\\\\d+-\\\\d+(?:\\\\s+|$)"
  }
}"""
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),
                ParagraphInfo(index=1, block_index=1, text="图3-1 系统架构图"),
                ParagraphInfo(index=2, block_index=2, text="", has_drawing=True),
            ),
        )

        result = run_checks(document, rules)

        self.assertEqual(result.checked_items, ("FIGURE_CAPTION_POSITION",))
        self.assertTrue(any(issue.code == "FIGURE_CAPTION_POSITION" for issue in result.issues))

    @unittest.expectedFailure
    def test_reference_format_selector_runs_without_citation_or_typography_config(self) -> None:
        rules = self._load_rules_from_json(
            """{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["REFERENCE_FORMAT"]},
  "structure": {
    "patterns": {
      "heading_level_1": "^第\\\\s*\\\\d+\\\\s*章(?:\\\\s+.+)?$",
      "heading_level_2": "^\\\\d+\\\\.\\\\d+(?:\\\\s+.+)?$",
      "heading_level_3": "^\\\\d+\\\\.\\\\d+\\\\.\\\\d+(?:\\\\s+.+)?$"
    },
    "headings": {
      "reference": ["参考文献"],
      "terminal": []
    }
  },
  "reference": {}
}"""
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="参考文献"),
                ParagraphInfo(index=1, text="作者. 缺少类型标识的题名. 2024."),
            ),
        )

        result = run_checks(document, rules)

        self.assertEqual(result.checked_items, ("REFERENCE_FORMAT",))
        self.assertTrue(any(issue.code == "REFERENCE_FORMAT" for issue in result.issues))

    @unittest.expectedFailure
    def test_table_line_count_selector_runs_with_minimal_line_count_config(self) -> None:
        rules = self._load_rules_from_json(
            """{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["TABLE_LINE_COUNT"]},
  "structure": {
    "patterns": {
      "body_start": "^第\\\\s*1\\\\s*章\\\\b"
    },
    "headings": {
      "reference": ["参考文献"]
    }
  },
  "table": {
    "horizontal_line_count": 3
  }
}"""
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("字段", "说明"), ("name", "商品名称")),
                    horizontal_line_count=4,
                    horizontal_line_positions=("top", "insideH", "insideH", "bottom"),
                ),
            ),
        )

        result = run_checks(document, rules)

        self.assertEqual(result.checked_items, ("TABLE_LINE_COUNT",))
        self.assertTrue(any(issue.code == "TABLE_LINE_COUNT" for issue in result.issues))

    def test_line_spacing_selector_runs_with_only_body_line_spacing_config(self) -> None:
        rules = self._load_rules_from_json(
            """{
  "profile": {"extends": "none"},
  "checks": {"enabled": ["LINE_SPACING"]},
  "structure": {
    "patterns": {
      "body_start": "^第\\\\s*1\\\\s*章\\\\b",
      "heading_level_1": "^第\\\\s*\\\\d+\\\\s*章(?:\\\\s+.+)?$",
      "heading_level_2": "^\\\\d+\\\\.\\\\d+(?:\\\\s+.+)?$",
      "heading_level_3": "^\\\\d+\\\\.\\\\d+\\\\.\\\\d+(?:\\\\s+.+)?$"
    },
    "headings": {
      "line_spacing_start": [],
      "line_spacing_excluded": []
    }
  },
  "numbering": {
    "caption_prefix_pattern": "^(?:图|表|续表)\\\\s*\\\\d+-\\\\d+(?:\\\\s+|$)"
  },
  "body": {
    "line_spacing_pt": 20.0
  }
}"""
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(
                ParagraphInfo(index=0, text="第1章 绪论"),
                ParagraphInfo(index=1, text="正文段落", line_spacing_pt=24.0, line_spacing_rule="exact"),
            ),
        )

        result = run_checks(document, rules)

        self.assertEqual(result.checked_items, ("LINE_SPACING",))
        self.assertTrue(any(issue.code == "LINE_SPACING" for issue in result.issues))

    def test_appendix_stops_body_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "structure": {
    "headings": {
      "terminal": ["Appendix"]
    }
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            appendix_paragraph = ParagraphInfo(
                index=2,
                text="Appendix content should not be checked as body text.",
                first_line_indent_chars=0.0,
                runs=(RunInfo(text="Appendix content should not be checked as body text.", size_pt=12.0),),
            )
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    ParagraphInfo(index=0, text="第1章 绪论"),
                    ParagraphInfo(index=1, text="Appendix"),
                    appendix_paragraph,
                ),
            )

            issues = _check_body_typography(document, rules)

            self.assertFalse(any(issue.evidence == appendix_paragraph.text for issue in issues))

    def test_chinese_number_heading_patterns_are_not_checked_as_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                r"""# Requirements

```json thesis-format-rules
{
  "structure": {
    "patterns": {
      "heading_level_1": "^[一二三四五六七八九十]+、.+$",
      "heading_level_2": "^（[一二三四五六七八九十]+）.+$"
    }
  }
}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            heading_1 = ParagraphInfo(index=0, text="一、绪论", first_line_indent_chars=0.0)
            heading_2 = ParagraphInfo(index=1, text="（一）研究背景", first_line_indent_chars=0.0)
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(
                    heading_1,
                    heading_2,
                    ParagraphInfo(index=2, text="本文介绍研究背景。", first_line_indent_chars=2.0),
                ),
            )

            issues = _check_body_typography(document, rules)

            self.assertFalse(any(issue.evidence == heading_1.text for issue in issues))
            self.assertFalse(any(issue.evidence == heading_2.text for issue in issues))

    def test_reference_typography_checks_list_spacing_and_font(self) -> None:
        entry = ParagraphInfo(
            index=2,
            text="ALANAZI S S. Question answering systems[J]. Journal, 2021, 12(3): 495-502.",
            alignment="center",
            first_line_indent_chars=2.0,
            space_before_pt=3.0,
            space_after_pt=6.0,
            line_spacing_multiple=1.5,
            line_spacing_rule="auto",
            runs=(
                RunInfo(
                    text="ALANAZI S S. Question answering systems[J]. Journal, 2021, 12(3): 495-502.",
                    font_ascii="Times New Roman",
                    font_east_asia="宋体",
                    size_pt=12.0,
                    bold=True,
                ),
            ),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=1, text="参考文献", alignment="center"), entry),
        )

        issues = _check_reference_typography(document)
        codes = [issue.code for issue in issues]

        self.assertIn("REFERENCE_LIST_FORMAT", codes)
        self.assertIn("REFERENCE_LIST_SPACING", codes)

    def test_table_caption_position_ignores_body_references(self) -> None:
        paragraph = ParagraphInfo(index=2, block_index=2, text="表6-4进一步说明，不同检索方案的差异并不只来自总体指标。")
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"), paragraph),
            tables=(
                TableInfo(index=1, block_index=1, rows=(("字段", "说明"),)),
                TableInfo(index=2, block_index=10, rows=(("字段", "说明"),)),
            ),
        )

        issues = _check_caption_object_order(document)

        self.assertEqual(issues, [])

    def test_table_caption_position_still_checks_real_captions(self) -> None:
        paragraph = ParagraphInfo(index=2, block_index=2, text="表6-4 端到端回答小规模人工评测结果")
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"), paragraph),
            tables=(TableInfo(index=1, block_index=1, rows=(("字段", "说明"),)),),
        )

        issues = _check_caption_object_order(document)

        self.assertTrue(any(issue.code == "TABLE_CAPTION_POSITION" for issue in issues))

    def test_continued_table_layout_accepts_split_table_with_repeated_header(self) -> None:
        paragraph = ParagraphInfo(index=1, block_index=2, text="续表3-6  订单表结构设计")
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(paragraph,),
            tables=(
                TableInfo(index=1, block_index=1, rows=(("序号", "字段名"), ("1", "id"))),
                TableInfo(index=2, block_index=3, rows=(("序号", "字段名"), ("4", "address_id"))),
            ),
        )

        issues = _check_continued_table_layout(document)

        self.assertEqual(issues, [])

    def test_continued_table_layout_requires_repeated_header(self) -> None:
        paragraph = ParagraphInfo(index=1, block_index=2, text="续表3-6  订单表结构设计")
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(paragraph,),
            tables=(
                TableInfo(index=1, block_index=1, rows=(("序号", "字段名"), ("1", "id"))),
                TableInfo(index=2, block_index=3, rows=(("字段", "类型"), ("4", "BIGINT"))),
            ),
        )

        issues = _check_continued_table_layout(document)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "CONTINUED_TABLE_LAYOUT")

    def test_heading_script_font_rejects_body_ascii_font(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="4.9 RAG实现",
            runs=(
                RunInfo(text="4.9 RAG", font_ascii="Cambria", font_east_asia="黑体", size_pt=16.0),
                RunInfo(text="实现", font_ascii="Times New Roman", font_east_asia="黑体", size_pt=16.0),
            ),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_heading_script_fonts(document)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "HEADING_SCRIPT_FONT")

    def test_heading_script_font_accepts_word_font_aliases(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="4.9 RAG实现",
            runs=(
                RunInfo(text="4.9 RAG", font_ascii="SimHei", font_east_asia="SimHei", size_pt=16.0),
                RunInfo(text="实现", font_ascii="SimHei", font_east_asia="SimHei", size_pt=16.0),
            ),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_heading_script_fonts(document)

        self.assertEqual(issues, [])

    def test_heading_script_font_rejects_times_new_roman_numbers(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="3.1 数值模型",
            runs=(RunInfo(text="3.1 数值模型", font_ascii="Times New Roman", font_east_asia="黑体", size_pt=16.0),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_heading_script_fonts(document)

        self.assertTrue(any(issue.code == "HEADING_SCRIPT_FONT" for issue in issues))

    def test_section_heading_script_font_rejects_explicit_bold(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="3.1 数值模型",
            runs=(RunInfo(text="3.1 数值模型", font_ascii="黑体", font_east_asia="黑体", size_pt=16.0, bold=True),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_heading_script_fonts(document)

        self.assertTrue(any(issue.code == "HEADING_SCRIPT_FONT" and issue.actual == "bold" for issue in issues))

    def test_chapter_heading_script_font_requires_bold(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="第1章 绪论",
            runs=(RunInfo(text="第1章 绪论", font_ascii="黑体", font_east_asia="黑体", size_pt=18.0, bold=False),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_heading_script_fonts(document)

        self.assertTrue(any(issue.code == "HEADING_SCRIPT_FONT" and issue.expected == "bold" for issue in issues))

    def test_chapter_heading_script_font_accepts_template_bold(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="第1章 绪论",
            runs=(RunInfo(text="第1章 绪论", font_ascii="黑体", font_east_asia="黑体", size_pt=18.0, bold=True),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_heading_script_fonts(document)

        self.assertEqual(issues, [])

    def test_heading_spacing_checks_template_before_after_and_line_spacing(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="1.1 研究背景",
            alignment="left",
            space_before_lines=1.0,
            space_after_lines=0.0,
            line_spacing_multiple=1.0,
            line_spacing_rule="auto",
            runs=(RunInfo(text="1.1 研究背景", font_east_asia="黑体", size_pt=16.0),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_headings(document)

        codes = [issue.code for issue in issues]
        self.assertGreaterEqual(codes.count("HEADING_SPACING"), 3)

    def test_chapter_heading_line_spacing_uses_chapter_template_expectation(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="第1章 绪论",
            alignment="center",
            space_before_lines=0.5,
            space_after_lines=0.5,
            line_spacing_multiple=2.0,
            line_spacing_rule="auto",
            runs=(RunInfo(text="第1章 绪论", font_ascii="黑体", font_east_asia="黑体", size_pt=18.0, bold=True),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_headings(document)

        self.assertTrue(
            any(issue.code == "HEADING_SPACING" and "no explicit override" in (issue.expected or "") for issue in issues)
        )

    def test_section_heading_checks_missing_line_spacing_and_indent(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="3.1 数值模型",
            alignment="left",
            space_before_lines=0.5,
            space_after_lines=0.5,
            first_line_indent_chars=2.0,
            runs=(RunInfo(text="3.1 数值模型", font_ascii="黑体", font_east_asia="黑体", size_pt=16.0),),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_headings(document)
        codes = [issue.code for issue in issues]

        self.assertIn("HEADING_SPACING", codes)
        self.assertIn("HEADING_FORMAT", codes)

    def test_heading_script_font_uses_word_heading_style_name(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="AI客服模块实现",
            style_name="heading 2",
            runs=(
                RunInfo(text="AI", font_ascii="Cambria", font_east_asia="黑体", size_pt=16.0),
                RunInfo(text="客服模块实现", font_ascii="Times New Roman", font_east_asia="黑体", size_pt=16.0),
            ),
        )
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_heading_script_fonts(document)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "HEADING_SCRIPT_FONT")

    def test_body_typography_checks_indent_chinese_font_ascii_font_and_size(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="本文使用Spring AI实现客服系统。",
            first_line_indent_chars=0.0,
            runs=(
                RunInfo(text="本文使用", font_ascii="Times New Roman", font_east_asia="宋体", size_pt=12.0),
                RunInfo(text="Spring AI", font_ascii="Cambria", font_east_asia="宋体", size_pt=12.0),
            ),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, text="第1章 绪论"), paragraph),
        )

        issues = _check_body_typography(document)
        codes = [issue.code for issue in issues]

        self.assertIn("BODY_INDENT", codes)
        self.assertIn("BODY_FONT", codes)

    def test_body_typography_uses_indent_loaded_from_markdown_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{"body": {"first_line_indent_chars": 3.0}}
```
""",
                encoding="utf-8",
            )
            rules = load_rules(rules_path)
            paragraph = ParagraphInfo(
                index=1,
                text="本文使用Spring AI实现客服系统。",
                first_line_indent_chars=2.0,
                runs=(RunInfo(text="本文使用Spring AI实现客服系统。", font_east_asia="宋体", size_pt=12.0),),
            )
            document = DocumentInfo(
                path=Path("fixture.docx"),
                paragraphs=(ParagraphInfo(index=0, text="第1章 绪论"), paragraph),
            )

            issues = _check_body_typography(document, rules)

            self.assertTrue(any(issue.code == "BODY_INDENT" and issue.expected == "3 characters" for issue in issues))

    def test_body_typography_flags_missing_first_line_indent(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="从表6-3可以看出，事实类问题在日期和办事流程线索较强时表现更稳定。",
            first_line_indent_chars=None,
            runs=(RunInfo(text="从表6-3可以看出，事实类问题在日期和办事流程线索较强时表现更稳定。", size_pt=12.0),),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, text="第1章 绪论"), paragraph),
        )

        issues = _check_body_typography(document)

        self.assertTrue(any(issue.code == "BODY_INDENT" for issue in issues))

    def test_body_typography_checks_spacing_bold_and_italic(self) -> None:
        paragraph = ParagraphInfo(
            index=1,
            text="本文进一步说明模型训练过程。",
            first_line_indent_chars=2.0,
            space_before_pt=6.0,
            space_after_pt=0.0,
            runs=(
                RunInfo(
                    text="本文进一步说明模型训练过程。",
                    font_ascii="Times New Roman",
                    font_east_asia="宋体",
                    size_pt=12.0,
                    bold=True,
                    italic=True,
                ),
            ),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, text="第1章 绪论"), paragraph),
        )

        issues = _check_body_typography(document)
        codes = [issue.code for issue in issues]

        self.assertIn("BODY_SPACING", codes)
        self.assertIn("BODY_FONT", codes)

    def test_table_cell_typography_checks_font_size(self) -> None:
        table_paragraph = ParagraphInfo(
            index=1,
            text="商品名称",
            runs=(RunInfo(text="商品名称", font_ascii="Times New Roman", font_east_asia="宋体", size_pt=10.5),),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(TableInfo(index=1, block_index=1, rows=(("字段", "说明"), ("name", "商品名称")), paragraphs=(table_paragraph,)),),
        )

        issues = _check_table_cell_typography(document)

        self.assertTrue(any(issue.code == "TABLE_CELL_FORMAT" for issue in issues))

    def test_table_cell_typography_checks_paragraph_spacing_triplet(self) -> None:
        table_paragraph = ParagraphInfo(
            index=1,
            text="商品名称",
            space_before_pt=6.0,
            space_after_pt=3.0,
            line_spacing_multiple=1.5,
            line_spacing_rule="auto",
            runs=(RunInfo(text="商品名称", font_ascii="Times New Roman", font_east_asia="宋体", size_pt=12.0),),
        )
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("字段", "说明"), ("name", "商品名称")),
                    paragraphs=(table_paragraph,),
                ),
            ),
        )

        issues = _check_table_cell_typography(document)

        self.assertGreaterEqual([issue.code for issue in issues].count("TABLE_CELL_SPACING"), 3)

    def test_table_border_check_flags_visible_vertical_borders(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("字段", "说明"), ("name", "商品名称")),
                    border_values=("top=single", "bottom=single", "insideH=single", "insideV=single"),
                    has_vertical_borders=True,
                ),
            ),
        )

        issues = _check_table_borders(document)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "TABLE_BORDER")

    def test_table_border_check_flags_incomplete_three_line_metadata(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("字段", "说明"), ("name", "商品名称")),
                    border_values=("top=single", "insideH=single"),
                    has_vertical_borders=False,
                ),
            ),
        )

        issues = _check_table_borders(document)

        codes = {issue.code for issue in issues}
        self.assertIn("TABLE_THREE_LINE", codes)

    def test_table_border_check_accepts_empty_template_table_layout(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("字段", "说明"), ("name", "商品名称")),
                    border_values=("top=single", "bottom=single", "insideH=none", "insideV=none"),
                    border_sizes=("top=18", "bottom=18"),
                    horizontal_line_count=3,
                    horizontal_line_positions=("top", "after row 1", "bottom"),
                    header_bottom_border_sizes=(6, 6),
                    cell_width_types=(("pct", "pct"), ("pct", "pct")),
                    cell_width_values=((2500, 2500), (2500, 2500)),
                    cell_vertical_alignments=("center", "center", "center", "center"),
                    has_vertical_borders=False,
                    alignment="center",
                    width_type="pct",
                    width_value=5000,
                ),
            ),
        )

        issues = _check_table_borders(document)

        self.assertEqual(issues, [])

    def test_table_border_check_flags_extra_horizontal_lines(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("字段", "说明"), ("name", "商品名称"), ("price", "价格")),
                    border_values=("top=single", "bottom=single", "insideH=single", "insideV=none"),
                    border_sizes=("top=18", "bottom=18"),
                    horizontal_line_count=4,
                    horizontal_line_positions=("top", "after row 1", "after row 2", "bottom"),
                    header_bottom_border_sizes=(6, 6),
                    cell_width_types=(("pct", "pct"), ("pct", "pct"), ("pct", "pct")),
                    cell_width_values=((2500, 2500), (2500, 2500), (2500, 2500)),
                    cell_vertical_alignments=("center", "center", "center", "center", "center", "center"),
                    has_vertical_borders=False,
                    alignment="center",
                    width_type="pct",
                    width_value=5000,
                ),
            ),
        )

        issues = _check_table_borders(document)

        self.assertTrue(any(issue.code == "TABLE_LINE_COUNT" for issue in issues))

    def test_table_border_check_flags_template_layout_mismatches(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("字段", "说明"), ("name", "商品名称")),
                    border_values=("top=single", "bottom=single", "insideH=none", "insideV=none"),
                    border_sizes=("top=12", "bottom=18"),
                    header_bottom_border_sizes=(4, 6),
                    cell_width_types=(("dxa", "pct"), ("pct", "pct")),
                    cell_width_values=((2400, 2500), (3000, 1000)),
                    cell_vertical_alignments=("top", "center", None, "center"),
                    has_vertical_borders=False,
                    alignment="left",
                    width_type="dxa",
                    width_value=8000,
                ),
            ),
        )

        issues = _check_table_borders(document)
        codes = {issue.code for issue in issues}

        self.assertIn("TABLE_ALIGNMENT", codes)
        self.assertIn("TABLE_BORDER_WIDTH", codes)
        self.assertIn("TABLE_HEADER_BORDER", codes)
        self.assertIn("TABLE_WIDTH", codes)
        self.assertIn("TABLE_CELL_WIDTH", codes)
        self.assertIn("TABLE_CELL_ALIGNMENT", codes)

    def test_table_border_check_ignores_single_row_layout_tables(self) -> None:
        document = DocumentInfo(
            path=Path("fixture.docx"),
            paragraphs=(ParagraphInfo(index=0, block_index=0, text="第1章 绪论"),),
            tables=(
                TableInfo(
                    index=1,
                    block_index=1,
                    rows=(("图3-1 系统架构图",),),
                    border_values=("top=none", "bottom=none"),
                    has_vertical_borders=False,
                ),
            ),
        )

        issues = _check_table_borders(document)

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
