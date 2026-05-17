from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from thesis_format_checker.checks import (
    _check_body_typography,
    _check_captions,
    _check_caption_object_order,
    _check_continued_table_layout,
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
)
from thesis_format_checker.model import DocumentInfo, ParagraphInfo, RuleSet, RunInfo, SectionInfo, Severity, TableInfo
from thesis_format_checker.rules import load_rules


class ChecksTests(unittest.TestCase):
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
