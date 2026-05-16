from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .model import DocumentInfo, ParagraphInfo, RunInfo, SectionInfo, TableInfo


class DocxReadError(RuntimeError):
    """Raised when a DOCX file cannot be parsed."""


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def read_docx(path: str | Path) -> DocumentInfo:
    """Read a DOCX file into a lightweight static model."""
    docx_path = Path(path)
    if not docx_path.exists():
        raise DocxReadError(f"DOCX file does not exist: {docx_path}")
    if docx_path.suffix.lower() != ".docx":
        raise DocxReadError(f"Expected a .docx file: {docx_path}")

    try:
        with zipfile.ZipFile(docx_path) as archive:
            try:
                document_xml = _read_xml(archive, "word/document.xml")
            except DocxReadError as exc:
                raise DocxReadError(f"{docx_path}: {exc}") from exc
            styles = _parse_styles(archive)
            relationships = _parse_document_relationships(archive)
            part_cache: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], tuple[int, ...], tuple[int, ...]]] = {}

            paragraphs: list[ParagraphInfo] = []
            sections: list[SectionInfo] = []
            tables: list[TableInfo] = []

            body = document_xml.find("w:body", NS)
            if body is None:
                raise DocxReadError(f"{docx_path}: word/document.xml is missing w:body")

            for block_index, child in enumerate(list(body)):
                if child.tag == _qn("w:p"):
                    paragraph = _parse_paragraph(child, len(paragraphs), block_index, styles)
                    paragraphs.append(paragraph)
                    sect_pr = child.find("w:pPr/w:sectPr", NS)
                    if sect_pr is not None:
                        sections.append(
                            _parse_section(sect_pr, len(sections), archive, relationships, part_cache, styles)
                        )
                elif child.tag == _qn("w:tbl"):
                    tables.append(_parse_table(child, len(tables), block_index, styles))
                elif child.tag == _qn("w:sectPr"):
                    sections.append(_parse_section(child, len(sections), archive, relationships, part_cache, styles))

            headers = _parse_package_parts(archive, "word/header")
            footers = _parse_package_parts(archive, "word/footer")

            if not sections:
                body_sect_pr = body.find("w:sectPr", NS)
                if body_sect_pr is not None:
                    sections.append(_parse_section(body_sect_pr, 0, archive, relationships, part_cache, styles))

            return DocumentInfo(
                path=docx_path,
                paragraphs=tuple(paragraphs),
                sections=tuple(sections),
                tables=tuple(tables),
                headers=tuple(headers),
                footers=tuple(footers),
            )
    except zipfile.BadZipFile as exc:
        raise DocxReadError(f"{docx_path}: not a valid DOCX zip archive") from exc
    except ET.ParseError as exc:
        raise DocxReadError(f"{docx_path}: malformed XML ({exc})") from exc


def _qn(tag: str) -> str:
    prefix, local = tag.split(":", 1)
    return f"{{{NS[prefix]}}}{local}"


def _read_xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    try:
        raw = archive.read(member)
    except KeyError as exc:
        raise DocxReadError(f"missing required DOCX part: {member}") from exc
    return ET.fromstring(raw)


def _parse_package_parts(archive: zipfile.ZipFile, prefix: str) -> tuple[str, ...]:
    members = sorted(
        name
        for name in archive.namelist()
        if name.startswith(prefix) and name.lower().endswith(".xml")
    )
    texts: list[str] = []
    for member in members:
        try:
            root = ET.fromstring(archive.read(member))
        except KeyError as exc:
            raise DocxReadError(f"missing DOCX part: {member}") from exc
        except ET.ParseError as exc:
            raise DocxReadError(f"malformed XML in {member}: {exc}") from exc
        text = _collect_text(root)
        if text or member:
            texts.append(text)
    return tuple(texts)


def _parse_document_relationships(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        root = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
    except KeyError:
        return {}
    rel_ns = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
    result: dict[str, str] = {}
    for rel in root.findall("rel:Relationship", rel_ns):
        rel_id = rel.get("Id")
        target = rel.get("Target")
        if not rel_id or not target:
            continue
        if target.startswith("/"):
            result[rel_id] = target.lstrip("/")
        elif target.startswith("word/"):
            result[rel_id] = target
        else:
            result[rel_id] = f"word/{target}"
    return result


def _read_part_text_and_fields(
    archive: zipfile.ZipFile,
    member: str,
    cache: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], tuple[int, ...], tuple[int, ...]]],
    style_data: dict[str, Any],
) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[int, ...], tuple[int, ...]]:
    if member in cache:
        return cache[member]
    try:
        root = ET.fromstring(archive.read(member))
    except KeyError:
        result = ("", (), (), (), ())
    else:
        positions, sizes, spaces = _paragraph_border_metadata(root, style_data)
        result = (_collect_text(root), _field_instructions(root), positions, sizes, spaces)
    cache[member] = result
    return result


def _parse_styles(archive: zipfile.ZipFile) -> dict[str, Any]:
    try:
        root = ET.fromstring(archive.read("word/styles.xml"))
    except KeyError:
        return {"styles": {}, "defaults": {}}

    styles: dict[str, dict[str, Any]] = {}
    defaults: dict[str, Any] = {}

    p_default = root.find("w:docDefaults/w:pPrDefault/w:pPr", NS)
    r_default = root.find("w:docDefaults/w:rPrDefault/w:rPr", NS)
    defaults.update(_paragraph_props(p_default))
    defaults.update(_run_props(r_default))

    for style in root.findall("w:style", NS):
        style_id = _attr_val(style, "styleId")
        if not style_id:
            continue
        style_name = _attr_val(style.find("w:name", NS), "val")
        props: dict[str, Any] = {}
        if style_name:
            props["style_name"] = style_name
        based_on = _attr_val(style.find("w:basedOn", NS), "val")
        if based_on:
            props["based_on"] = based_on
        props.update(_paragraph_props(style.find("w:pPr", NS)))
        props.update(_run_props(style.find("w:rPr", NS)))
        styles[style_id] = props
    return {"styles": styles, "defaults": defaults}


def _resolve_style_props(style_id: str | None, style_data: dict[str, Any]) -> dict[str, Any]:
    defaults = dict(style_data.get("defaults", {}))
    styles: dict[str, dict[str, Any]] = style_data.get("styles", {})
    if not style_id:
        return defaults

    resolved: dict[str, Any] = {}
    seen: set[str] = set()

    def visit(current: str) -> None:
        if current in seen:
            return
        seen.add(current)
        props = styles.get(current)
        if not props:
            return
        based_on = props.get("based_on")
        if isinstance(based_on, str):
            visit(based_on)
        for key, value in props.items():
            if key != "based_on" and value is not None:
                resolved[key] = value

    visit(style_id)
    resolved.pop("style_name", None)
    defaults.update(resolved)
    return defaults


def _paragraph_props(p_pr: ET.Element | None) -> dict[str, Any]:
    props: dict[str, Any] = {}
    if p_pr is None:
        return props
    props["alignment"] = _attr_val(p_pr.find("w:jc", NS), "val")
    spacing = p_pr.find("w:spacing", NS)
    if spacing is not None:
        line = _attr_int(spacing, "line")
        line_rule = _attr_val(spacing, "lineRule")
        if line is not None and line_rule in {"exact", "fixed"}:
            props["line_spacing_pt"] = _twips_to_pt(line)
            props["line_spacing_rule"] = line_rule
        elif line is not None and line_rule in {None, "auto"}:
            props["line_spacing_multiple"] = line / 240.0
            props["line_spacing_rule"] = "auto"
        elif line is not None:
            props["line_spacing_pt"] = _twips_to_pt(line)
            props["line_spacing_rule"] = line_rule
        before = _attr_int(spacing, "before")
        after = _attr_int(spacing, "after")
        if before is not None:
            props["space_before_pt"] = _twips_to_pt(before)
        if after is not None:
            props["space_after_pt"] = _twips_to_pt(after)
    ind = p_pr.find("w:ind", NS)
    if ind is not None:
        props["first_line_indent_chars"] = _first_line_indent_chars(ind, None)
    bottom_border = p_pr.find("w:pBdr/w:bottom", NS)
    if _is_visible_border(bottom_border):
        props["bottom_border_size"] = _attr_int(bottom_border, "sz")
        props["bottom_border_space"] = _attr_int(bottom_border, "space")
    return props


def _run_props(r_pr: ET.Element | None) -> dict[str, Any]:
    if r_pr is None:
        return {}
    return {
        "font_ascii": _font_name(r_pr, "ascii"),
        "font_east_asia": _font_name(r_pr, "eastAsia"),
        "size_pt": _font_size_pt(r_pr),
        "bold": _bool_prop(r_pr.find("w:b", NS)),
    }


def _paragraph_border_metadata(
    root: ET.Element,
    style_data: dict[str, Any],
) -> tuple[tuple[str, ...], tuple[int, ...], tuple[int, ...]]:
    positions: list[str] = []
    bottom_sizes: list[int] = []
    bottom_spaces: list[int] = []
    for paragraph in root.findall(".//w:p", NS):
        p_pr = paragraph.find("w:pPr", NS)
        style = _attr_val(p_pr.find("w:pStyle", NS), "val") if p_pr is not None else None
        style_props = _resolve_style_props(style, style_data)
        p_bdr = p_pr.find("w:pBdr", NS) if p_pr is not None else None
        paragraph_positions: set[str] = set()
        for position in ("top", "bottom"):
            border = p_bdr.find(f"w:{position}", NS) if p_bdr is not None else None
            if _is_visible_border(border):
                positions.append(position)
                paragraph_positions.add(position)
                if position == "bottom":
                    size = _attr_int(border, "sz")
                    space = _attr_int(border, "space")
                    if size is not None:
                        bottom_sizes.append(size)
                    if space is not None:
                        bottom_spaces.append(space)
        if "bottom" not in paragraph_positions and style_props.get("bottom_border_size") is not None:
            positions.append("bottom")
            bottom_sizes.append(style_props["bottom_border_size"])
            if style_props.get("bottom_border_space") is not None:
                bottom_spaces.append(style_props["bottom_border_space"])
    return tuple(positions), tuple(bottom_sizes), tuple(bottom_spaces)


def _parse_paragraph(
    element: ET.Element,
    index: int,
    block_index: int,
    style_data: dict[str, Any],
) -> ParagraphInfo:
    p_pr = element.find("w:pPr", NS)
    style = _attr_val(p_pr.find("w:pStyle", NS), "val") if p_pr is not None else None
    style_props = _resolve_style_props(style, style_data)
    style_name = None
    if style:
        style_name = style_data.get("styles", {}).get(style, {}).get("style_name")
    direct_p_props = _paragraph_props(p_pr)
    alignment = direct_p_props.get("alignment") or style_props.get("alignment")

    direct_has_line_spacing = "line_spacing_rule" in direct_p_props
    if direct_has_line_spacing:
        line_spacing_pt = direct_p_props.get("line_spacing_pt")
        line_spacing_multiple = direct_p_props.get("line_spacing_multiple")
        line_spacing_rule = direct_p_props.get("line_spacing_rule")
    else:
        line_spacing_pt = style_props.get("line_spacing_pt")
        line_spacing_multiple = style_props.get("line_spacing_multiple")
        line_spacing_rule = style_props.get("line_spacing_rule")
    first_line_indent_chars = direct_p_props.get("first_line_indent_chars")
    if first_line_indent_chars is None:
        first_line_indent_chars = style_props.get("first_line_indent_chars")
    space_before_pt = direct_p_props.get("space_before_pt")
    if space_before_pt is None:
        space_before_pt = style_props.get("space_before_pt")
    space_after_pt = direct_p_props.get("space_after_pt")
    if space_after_pt is None:
        space_after_pt = style_props.get("space_after_pt")
    has_page_break_before = False
    has_page_break = False

    if p_pr is not None:
        ind = p_pr.find("w:ind", NS)
        indent = _first_line_indent_chars(ind, _paragraph_font_size_pt(element))
        if indent is not None:
            first_line_indent_chars = indent

        page_break_before = p_pr.find("w:pageBreakBefore", NS)
        has_page_break_before = page_break_before is not None and _is_on(page_break_before)

    runs: list[RunInfo] = []
    for run in element.findall("w:r", NS):
        if run.find("w:br", NS) is not None:
            for br in run.findall("w:br", NS):
                if _attr_val(br, "type") == "page":
                    has_page_break = True
        text = _collect_text(run)
        if text == "":
            continue
        r_pr = run.find("w:rPr", NS)
        direct_r_props = _run_props(r_pr)
        runs.append(
            RunInfo(
                text=text,
                font_ascii=direct_r_props.get("font_ascii") or style_props.get("font_ascii"),
                font_east_asia=direct_r_props.get("font_east_asia") or style_props.get("font_east_asia"),
                size_pt=direct_r_props.get("size_pt") or style_props.get("size_pt"),
                bold=direct_r_props.get("bold") if direct_r_props.get("bold") is not None else style_props.get("bold"),
            )
        )

    text = _collect_text(element)
    return ParagraphInfo(
        index=index,
        text=text,
        block_index=block_index,
        style=style,
        style_name=style_name,
        alignment=alignment,
        line_spacing_pt=line_spacing_pt,
        line_spacing_multiple=line_spacing_multiple,
        line_spacing_rule=line_spacing_rule,
        first_line_indent_chars=first_line_indent_chars,
        space_before_pt=space_before_pt,
        space_after_pt=space_after_pt,
        has_page_break_before=has_page_break_before,
        has_page_break=has_page_break,
        has_drawing=element.find(".//w:drawing", NS) is not None or element.find(".//w:pict", NS) is not None,
        field_instructions=_field_instructions(element),
        runs=tuple(runs),
    )


def _parse_section(
    element: ET.Element,
    index: int,
    archive: zipfile.ZipFile,
    relationships: dict[str, str],
    part_cache: dict[str, tuple[str, tuple[str, ...], tuple[str, ...], tuple[int, ...], tuple[int, ...]]],
    style_data: dict[str, Any],
) -> SectionInfo:
    pg_sz = element.find("w:pgSz", NS)
    pg_mar = element.find("w:pgMar", NS)
    pg_num_type = element.find("w:pgNumType", NS)
    header_texts: list[str] = []
    header_border_positions: list[str] = []
    header_bottom_border_sizes: list[int] = []
    header_bottom_border_spaces: list[int] = []
    footer_texts: list[str] = []
    footer_fields: list[str] = []
    for header_ref in element.findall("w:headerReference", NS):
        rel_id = header_ref.get(f"{{{NS['r']}}}id")
        member = relationships.get(rel_id or "")
        if member:
            text, _fields, positions, bottom_sizes, bottom_spaces = _read_part_text_and_fields(
                archive, member, part_cache, style_data
            )
            header_texts.append(text)
            header_border_positions.extend(positions)
            header_bottom_border_sizes.extend(bottom_sizes)
            header_bottom_border_spaces.extend(bottom_spaces)
    for footer_ref in element.findall("w:footerReference", NS):
        rel_id = footer_ref.get(f"{{{NS['r']}}}id")
        member = relationships.get(rel_id or "")
        if member:
            text, fields, _positions, _bottom_sizes, _bottom_spaces = _read_part_text_and_fields(
                archive, member, part_cache, style_data
            )
            footer_texts.append(text)
            footer_fields.extend(fields)
    return SectionInfo(
        index=index,
        page_width_cm=_twips_to_cm(_attr_int(pg_sz, "w")) if pg_sz is not None else None,
        page_height_cm=_twips_to_cm(_attr_int(pg_sz, "h")) if pg_sz is not None else None,
        margin_top_cm=_twips_to_cm(_attr_int(pg_mar, "top")) if pg_mar is not None else None,
        margin_bottom_cm=_twips_to_cm(_attr_int(pg_mar, "bottom")) if pg_mar is not None else None,
        margin_left_cm=_twips_to_cm(_attr_int(pg_mar, "left")) if pg_mar is not None else None,
        margin_right_cm=_twips_to_cm(_attr_int(pg_mar, "right")) if pg_mar is not None else None,
        header_distance_cm=_twips_to_cm(_attr_int(pg_mar, "header")) if pg_mar is not None else None,
        footer_distance_cm=_twips_to_cm(_attr_int(pg_mar, "footer")) if pg_mar is not None else None,
        page_number_start=_attr_int(pg_num_type, "start") if pg_num_type is not None else None,
        page_number_format=_attr_val(pg_num_type, "fmt") if pg_num_type is not None else None,
        header_texts=tuple(header_texts),
        header_border_positions=tuple(header_border_positions),
        header_bottom_border_sizes=tuple(header_bottom_border_sizes),
        header_bottom_border_spaces=tuple(header_bottom_border_spaces),
        footer_texts=tuple(footer_texts),
        footer_field_instructions=tuple(footer_fields),
    )


def _parse_table(element: ET.Element, index: int, block_index: int, style_data: dict[str, Any]) -> TableInfo:
    rows: list[tuple[str, ...]] = []
    paragraphs: list[ParagraphInfo] = []
    for row in element.findall("w:tr", NS):
        cells: list[str] = []
        for cell in row.findall("w:tc", NS):
            cells.append(_collect_cell_text(cell))
            for paragraph in cell.iter(_qn("w:p")):
                paragraphs.append(_parse_paragraph(paragraph, len(paragraphs), block_index, style_data))
        rows.append(tuple(cells))
    tbl_pr = element.find("w:tblPr", NS)
    tbl_w = tbl_pr.find("w:tblW", NS) if tbl_pr is not None else None
    tbl_jc = tbl_pr.find("w:jc", NS) if tbl_pr is not None else None
    borders = _table_border_values(element)
    vertical_names = {"left", "right", "start", "end", "insideV"}
    has_vertical = any(name in vertical_names and value not in {"nil", "none"} for name, value in borders)
    border_values = tuple(f"{name}={value}" for name, value in borders)
    table_border_sizes = _direct_table_border_sizes(element)
    horizontal_line_positions = _horizontal_line_positions(element)
    header_bottom_sizes = _header_bottom_border_sizes(element)
    return TableInfo(
        index=index,
        block_index=block_index,
        rows=tuple(rows),
        paragraphs=tuple(paragraphs),
        border_values=border_values,
        border_sizes=tuple(f"{name}={size}" for name, size in table_border_sizes),
        horizontal_line_count=len(horizontal_line_positions),
        horizontal_line_positions=tuple(horizontal_line_positions),
        header_bottom_border_sizes=tuple(header_bottom_sizes),
        has_vertical_borders=has_vertical if borders else None,
        alignment=_attr_val(tbl_jc, "val"),
        width_type=_attr_val(tbl_w, "type"),
        width_value=_attr_int(tbl_w, "w"),
    )


def _collect_cell_text(element: ET.Element) -> str:
    paragraphs = []
    for child in element.iter():
        if child.tag == _qn("w:p"):
            text = _collect_text(child)
            if text:
                paragraphs.append(text)
    return "\n".join(paragraphs)


def _collect_text(element: ET.Element) -> str:
    parts: list[str] = []
    for node in element.iter():
        if node.tag == _qn("w:t"):
            parts.append(node.text or "")
        elif node.tag == _qn("w:tab"):
            parts.append("\t")
        elif node.tag in {_qn("w:br"), _qn("w:cr")}:
            parts.append("\n")
    return "".join(parts)


def _field_instructions(element: ET.Element) -> tuple[str, ...]:
    instructions: list[str] = []
    for fld_simple in element.findall(".//w:fldSimple", NS):
        instruction = _attr_val(fld_simple, "instr")
        if instruction:
            instructions.append(" ".join(instruction.split()))
    for instr in element.findall(".//w:instrText", NS):
        if instr.text and instr.text.strip():
            instructions.append(" ".join(instr.text.split()))
    return tuple(instructions)


def _table_border_values(element: ET.Element) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for borders in element.findall(".//w:tblBorders", NS) + element.findall(".//w:tcBorders", NS):
        for border in list(borders):
            if not border.tag.startswith("{"):
                continue
            name = border.tag.rsplit("}", 1)[-1]
            value = _attr_val(border, "val")
            if value:
                values.append((name, value))
    return values


def _direct_table_border_sizes(element: ET.Element) -> list[tuple[str, int]]:
    values: list[tuple[str, int]] = []
    borders = element.find("w:tblPr/w:tblBorders", NS)
    if borders is None:
        return values
    for border in list(borders):
        if not border.tag.startswith("{"):
            continue
        name = border.tag.rsplit("}", 1)[-1]
        value = _attr_val(border, "val")
        size = _attr_int(border, "sz")
        if value in {"nil", "none"} or size is None:
            continue
        values.append((name, size))
    return values


def _horizontal_line_positions(element: ET.Element) -> list[str]:
    rows = element.findall("w:tr", NS)
    if not rows:
        return []
    positions: set[int] = set()
    borders = element.find("w:tblPr/w:tblBorders", NS)
    if _is_visible_border(borders.find("w:top", NS) if borders is not None else None):
        positions.add(0)
    if _is_visible_border(borders.find("w:bottom", NS) if borders is not None else None):
        positions.add(len(rows))
    if _is_visible_border(borders.find("w:insideH", NS) if borders is not None else None):
        positions.update(range(1, len(rows)))

    for row_index, row in enumerate(rows):
        for cell in row.findall("w:tc", NS):
            cell_borders = cell.find("w:tcPr/w:tcBorders", NS)
            if cell_borders is None:
                continue
            if _is_visible_border(cell_borders.find("w:top", NS)):
                positions.add(row_index)
            if _is_visible_border(cell_borders.find("w:bottom", NS)):
                positions.add(row_index + 1)
    return [_line_position_label(position, len(rows)) for position in sorted(positions)]


def _line_position_label(position: int, row_count: int) -> str:
    if position == 0:
        return "top"
    if position == row_count:
        return "bottom"
    return f"after row {position}"


def _is_visible_border(element: ET.Element | None) -> bool:
    if element is None:
        return False
    value = _attr_val(element, "val")
    return value not in {None, "nil", "none"}


def _header_bottom_border_sizes(element: ET.Element) -> list[int]:
    first_row = element.find("w:tr", NS)
    if first_row is None:
        return []
    values: list[int] = []
    for cell in first_row.findall("w:tc", NS):
        bottom = cell.find("w:tcPr/w:tcBorders/w:bottom", NS)
        value = _attr_val(bottom, "val")
        size = _attr_int(bottom, "sz")
        if value not in {"nil", "none"} and size is not None:
            values.append(size)
    return values


def _attr_val(element: ET.Element | None, name: str) -> str | None:
    if element is None:
        return None
    return element.get(_qn_attr(name))


def _attr_int(element: ET.Element | None, name: str) -> int | None:
    if element is None:
        return None
    value = element.get(_qn_attr(name))
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise DocxReadError(f"invalid integer attribute {name}={value!r} on <{element.tag}>") from exc


def _qn_attr(name: str) -> str:
    return f"{{{NS['w']}}}{name}"


def _bool_prop(element: ET.Element | None) -> bool | None:
    if element is None:
        return None
    value = element.get(_qn_attr("val"))
    if value is None:
        return True
    normalized = value.lower()
    if normalized in {"1", "true", "on", "yes"}:
        return True
    if normalized in {"0", "false", "off", "no"}:
        return False
    return True


def _is_on(element: ET.Element) -> bool:
    value = element.get(_qn_attr("val"))
    if value is None:
        return True
    return value.lower() not in {"0", "false", "off", "no"}


def _font_name(r_pr: ET.Element | None, which: str) -> str | None:
    if r_pr is None:
        return None
    r_fonts = r_pr.find("w:rFonts", NS)
    if r_fonts is None:
        return None
    return r_fonts.get(_qn_attr(which))


def _font_size_pt(r_pr: ET.Element | None) -> float | None:
    if r_pr is None:
        return None
    size = _attr_int(r_pr.find("w:sz", NS), "val")
    if size is None:
        size = _attr_int(r_pr.find("w:szCs", NS), "val")
    if size is None:
        return None
    return size / 2.0


def _paragraph_font_size_pt(paragraph: ET.Element) -> float | None:
    first_run = paragraph.find("w:r", NS)
    if first_run is None:
        return None
    return _font_size_pt(first_run.find("w:rPr", NS))


def _first_line_indent_chars(ind: ET.Element | None, font_size_pt: float | None) -> float | None:
    if ind is None:
        return None
    first_line_chars = _attr_int(ind, "firstLineChars")
    if first_line_chars is not None:
        return first_line_chars / 100.0
    first_line = _attr_int(ind, "firstLine")
    hanging = _attr_int(ind, "hanging")
    if first_line is not None:
        return _twips_to_chars(first_line, font_size_pt)
    if hanging is not None:
        return -_twips_to_chars(hanging, font_size_pt)
    return None


def _twips_to_cm(value: int | None) -> float | None:
    if value is None:
        return None
    return value * 2.54 / 1440.0


def _twips_to_pt(value: int) -> float:
    return value / 20.0


def _twips_to_chars(value: int, font_size_pt: float | None) -> float:
    if font_size_pt and font_size_pt > 0:
        return _twips_to_pt(value) / font_size_pt
    return _twips_to_pt(value) / 12.0
