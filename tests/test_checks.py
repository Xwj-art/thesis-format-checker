from __future__ import annotations

from pathlib import Path
import unittest

from thesis_format_checker.checks import (
    _check_body_typography,
    _check_captions,
    _check_caption_object_order,
    _check_continued_table_layout,
    _check_header_text,
    _check_heading_script_fonts,
    _check_mixed_language_spacing,
    _check_numbering,
    _check_table_borders,
    _check_table_cell_typography,
)
from thesis_format_checker.model import DocumentInfo, ParagraphInfo, RuleSet, RunInfo, TableInfo


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

    def test_mixed_language_spacing_helper_flags_adjacent_chinese_and_english(self) -> None:
        paragraph = ParagraphInfo(index=1, text="本文基于Spring AI实现智能客服。")
        document = DocumentInfo(path=Path("fixture.docx"), paragraphs=(paragraph,))

        issues = _check_mixed_language_spacing(document)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "MIXED_LANGUAGE_SPACING")

    def test_mixed_language_spacing_accepts_half_width_spaces(self) -> None:
        paragraph = ParagraphInfo(index=1, text="本文基于 Spring AI 实现智能客服。")
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

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "TABLE_CELL_FORMAT")

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
                    header_bottom_border_sizes=(6, 6),
                    has_vertical_borders=False,
                    alignment="center",
                    width_type="pct",
                    width_value=5000,
                ),
            ),
        )

        issues = _check_table_borders(document)

        self.assertEqual(issues, [])

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
                    has_vertical_borders=False,
                    alignment="left",
                    width_type="dxa",
                    width_value=8000,
                ),
            ),
        )

        issues = _check_table_borders(document)
        codes = {issue.code for issue in issues}

        self.assertIn("TABLE_WIDTH", codes)
        self.assertIn("TABLE_ALIGNMENT", codes)
        self.assertIn("TABLE_BORDER_WIDTH", codes)
        self.assertIn("TABLE_HEADER_BORDER", codes)

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
