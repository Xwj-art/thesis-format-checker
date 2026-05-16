from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_minimal_docx(
    path: str | Path,
    *,
    body_text: str = "Thesis body paragraph.",
    header_text: str = "Thesis header",
    footer_text: str = "Thesis footer",
    paragraph_properties_xml: str = "",
    table_properties_xml: str = "",
    first_row_cell_properties_xml: str = "",
    table_extra_rows_xml: str = "",
    table_cell_paragraph_properties_xml: str = "",
    styles_xml: str | None = None,
) -> Path:
    """Create a small but structurally valid DOCX package for tests."""
    docx_path = Path(path)
    docx_path.parent.mkdir(parents=True, exist_ok=True)

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      {paragraph_properties_xml}
      <w:r>
        <w:rPr>
          <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>
          <w:sz w:val="24"/>
          <w:b/>
        </w:rPr>
        <w:t>{_xml_escape(body_text)}</w:t>
      </w:r>
    </w:p>
    <w:tbl>
      {table_properties_xml}
      <w:tr>
        <w:tc>
          {first_row_cell_properties_xml}
          <w:p>
            {table_cell_paragraph_properties_xml}
            <w:r>
              <w:t>Table cell</w:t>
            </w:r>
          </w:p>
        </w:tc>
      </w:tr>
      {table_extra_rows_xml}
    </w:tbl>
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
      <w:headerReference w:type="default" r:id="rHeader1"/>
      <w:footerReference w:type="default" r:id="rFooter1"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

    header_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p>
    <w:r>
      <w:t>{_xml_escape(header_text)}</w:t>
    </w:r>
  </w:p>
</w:hdr>
"""

    footer_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:p>
    <w:r>
      <w:t>{_xml_escape(footer_text)}</w:t>
    </w:r>
  </w:p>
</w:ftr>
"""

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
  {'<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' if styles_xml else ''}
</Types>
"""

    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rDoc1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

    document_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rHeader1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
  <Relationship Id="rFooter1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
</Relationships>
"""

    with ZipFile(docx_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels_xml)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", document_rels_xml)
        archive.writestr("word/header1.xml", header_xml)
        archive.writestr("word/footer1.xml", footer_xml)
        if styles_xml:
            archive.writestr("word/styles.xml", styles_xml)

    return docx_path
