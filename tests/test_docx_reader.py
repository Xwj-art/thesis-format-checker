from __future__ import annotations

import tempfile
from pathlib import Path
from zipfile import ZipFile
import unittest

from thesis_format_checker.docx_reader import DocxReadError, read_docx

from .helpers import build_minimal_docx


def _assert_docx_fields_if_present(testcase, document) -> None:
    if document.paragraphs:
        testcase.assertGreaterEqual(len(document.paragraphs), 1)
        testcase.assertEqual(document.paragraphs[0].text, "Thesis body paragraph.")

        first_paragraph = document.paragraphs[0]
        if first_paragraph.runs:
            testcase.assertEqual(first_paragraph.runs[0].text, "Thesis body paragraph.")
            testcase.assertEqual(first_paragraph.runs[0].font_ascii, "Times New Roman")
            testcase.assertEqual(first_paragraph.runs[0].font_east_asia, "宋体")
            testcase.assertEqual(first_paragraph.runs[0].size_pt, 12.0)
            testcase.assertTrue(first_paragraph.runs[0].bold)

    if document.tables:
        testcase.assertGreaterEqual(len(document.tables), 1)
        testcase.assertTrue(document.tables[0].rows)

    if document.sections:
        testcase.assertGreaterEqual(len(document.sections), 1)
        testcase.assertAlmostEqual(document.sections[0].page_width_cm or 0.0, 21.0, places=2)
        testcase.assertAlmostEqual(document.sections[0].page_height_cm or 0.0, 29.70, places=2)

    if document.headers:
        testcase.assertIn("Thesis header", document.headers)

    if document.footers:
        testcase.assertIn("Thesis footer", document.footers)


class DocxReaderTests(unittest.TestCase):
    def test_read_docx_accepts_minimal_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(Path(tmpdir) / "fixture.docx")

            with ZipFile(docx_path) as archive:
                self.assertIn("[Content_Types].xml", archive.namelist())
                self.assertIn("word/document.xml", archive.namelist())
                self.assertIn("word/header1.xml", archive.namelist())
                self.assertIn("word/footer1.xml", archive.namelist())

            document = read_docx(docx_path)

            self.assertEqual(document.path, docx_path)
            _assert_docx_fields_if_present(self, document)

    def test_read_docx_parses_auto_line_spacing_from_style(self) -> None:
        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:pPr>
      <w:spacing w:line="360" w:lineRule="auto"/>
    </w:pPr>
  </w:style>
</w:styles>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                paragraph_properties_xml='<w:pPr><w:pStyle w:val="Normal"/></w:pPr>',
                styles_xml=styles_xml,
            )

            paragraph = read_docx(docx_path).paragraphs[0]

            self.assertIsNone(paragraph.line_spacing_pt)
            self.assertEqual(paragraph.style_name, "Normal")
            self.assertEqual(paragraph.line_spacing_rule, "auto")
            self.assertAlmostEqual(paragraph.line_spacing_multiple or 0.0, 1.5)

    def test_direct_fixed_line_spacing_overrides_style_multiple_spacing(self) -> None:
        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:pPr>
      <w:spacing w:line="360" w:lineRule="auto"/>
    </w:pPr>
  </w:style>
</w:styles>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                paragraph_properties_xml=(
                    '<w:pPr><w:pStyle w:val="Normal"/>'
                    '<w:spacing w:line="400" w:lineRule="exact"/></w:pPr>'
                ),
                styles_xml=styles_xml,
            )

            paragraph = read_docx(docx_path).paragraphs[0]

            self.assertEqual(paragraph.line_spacing_rule, "exact")
            self.assertAlmostEqual(paragraph.line_spacing_pt or 0.0, 20.0)
            self.assertIsNone(paragraph.line_spacing_multiple)

    def test_read_docx_parses_italic_from_style(self) -> None:
        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:rPr>
      <w:i/>
    </w:rPr>
  </w:style>
</w:styles>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                paragraph_properties_xml='<w:pPr><w:pStyle w:val="Normal"/></w:pPr>',
                styles_xml=styles_xml,
            )

            paragraph = read_docx(docx_path).paragraphs[0]

            self.assertTrue(paragraph.runs[0].italic)

    def test_read_docx_parses_vertical_align_from_style(self) -> None:
        styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal">
    <w:rPr>
      <w:vertAlign w:val="superscript"/>
    </w:rPr>
  </w:style>
</w:styles>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                paragraph_properties_xml='<w:pPr><w:pStyle w:val="Normal"/></w:pPr>',
                styles_xml=styles_xml,
            )

            paragraph = read_docx(docx_path).paragraphs[0]

            self.assertEqual(paragraph.runs[0].vertical_align, "superscript")

    def test_read_docx_parses_runs_nested_in_hyperlinks(self) -> None:
        body_runs_xml = """
      <w:r><w:t>引用</w:t></w:r>
      <w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>[</w:t></w:r>
      <w:hyperlink w:anchor="_Ref1">
        <w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>1</w:t></w:r>
      </w:hyperlink>
      <w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>]</w:t></w:r>
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                body_runs_xml=body_runs_xml,
            )

            paragraph = read_docx(docx_path).paragraphs[0]

            self.assertEqual(paragraph.text, "引用[1]")
            self.assertEqual([run.text for run in paragraph.runs], ["引用", "[", "1", "]"])
            self.assertEqual([run.vertical_align for run in paragraph.runs[1:]], ["superscript", "superscript", "superscript"])

    def test_read_docx_parses_line_based_paragraph_spacing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                paragraph_properties_xml=(
                    '<w:pPr><w:spacing w:beforeLines="50" w:afterLines="50" '
                    'w:line="400" w:lineRule="exact"/></w:pPr>'
                ),
            )

            paragraph = read_docx(docx_path).paragraphs[0]

            self.assertAlmostEqual(paragraph.space_before_lines or 0.0, 0.5)
            self.assertAlmostEqual(paragraph.space_after_lines or 0.0, 0.5)
            self.assertEqual(paragraph.line_spacing_rule, "exact")
            self.assertAlmostEqual(paragraph.line_spacing_pt or 0.0, 20.0)

    def test_read_docx_parses_table_cell_paragraph_spacing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                table_cell_paragraph_properties_xml='<w:pPr><w:spacing w:line="300" w:lineRule="auto"/></w:pPr>',
            )

            table = read_docx(docx_path).tables[0]

            self.assertEqual(len(table.paragraphs), 1)
            self.assertEqual(table.paragraphs[0].line_spacing_rule, "auto")
            self.assertAlmostEqual(table.paragraphs[0].line_spacing_multiple or 0.0, 1.25)

    def test_read_docx_parses_table_layout_and_border_widths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            table_properties_xml = """
      <w:tblPr>
        <w:tblW w:w="5000" w:type="pct"/>
        <w:jc w:val="center"/>
        <w:tblBorders>
          <w:top w:val="single" w:sz="18" w:space="0" w:color="auto"/>
          <w:bottom w:val="single" w:sz="18" w:space="0" w:color="auto"/>
          <w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>
          <w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>
        </w:tblBorders>
      </w:tblPr>
"""
            first_row_cell_properties_xml = """
          <w:tcPr>
            <w:tcW w:w="5000" w:type="pct"/>
            <w:vAlign w:val="center"/>
            <w:tcBorders>
              <w:bottom w:val="single" w:sz="6" w:space="0" w:color="auto"/>
            </w:tcBorders>
          </w:tcPr>
"""
            table_extra_rows_xml = """
      <w:tr>
        <w:tc>
          <w:tcPr>
            <w:tcW w:w="5000" w:type="pct"/>
            <w:vAlign w:val="center"/>
          </w:tcPr>
          <w:p>
            <w:r>
              <w:t>Second row</w:t>
            </w:r>
          </w:p>
        </w:tc>
      </w:tr>
"""
            docx_path = build_minimal_docx(
                Path(tmpdir) / "fixture.docx",
                table_properties_xml=table_properties_xml,
                first_row_cell_properties_xml=first_row_cell_properties_xml,
                table_extra_rows_xml=table_extra_rows_xml,
            )

            table = read_docx(docx_path).tables[0]

            self.assertEqual(table.width_type, "pct")
            self.assertEqual(table.width_value, 5000)
            self.assertEqual(table.alignment, "center")
            self.assertIn("top=18", table.border_sizes)
            self.assertIn("bottom=18", table.border_sizes)
            self.assertEqual(table.horizontal_line_count, 3)
            self.assertEqual(table.horizontal_line_positions, ("top", "after row 1", "bottom"))
            self.assertEqual(table.header_bottom_border_sizes, (6,))
            self.assertEqual(table.cell_width_types, (("pct",), ("pct",)))
            self.assertEqual(table.cell_width_values, ((5000,), (5000,)))
            self.assertEqual(table.cell_vertical_alignments, ("center", "center"))

    def test_read_docx_rejects_missing_or_wrong_extension(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            with self.assertRaises(DocxReadError):
                read_docx(tmpdir_path / "missing.docx")

            bad_path = tmpdir_path / "not-a-docx.txt"
            bad_path.write_text("not a docx", encoding="utf-8")
            with self.assertRaises(DocxReadError):
                read_docx(bad_path)
