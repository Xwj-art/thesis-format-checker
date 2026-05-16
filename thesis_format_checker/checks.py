from __future__ import annotations

import re

from .model import CheckResult, DocumentInfo, Issue, ParagraphInfo, RuleSet, Severity, TableInfo


_PAGE_TOLERANCE_CM = 0.1
_LINE_SPACING_TOLERANCE_PT = 0.5
_FONT_SIZE_TOLERANCE_PT = 0.25
_INDENT_TOLERANCE_CHARS = 0.25
_TEMPLATE_TABLE_WIDTH_TYPE = "pct"
_TEMPLATE_TABLE_WIDTH_VALUE = 5000
_TEMPLATE_TABLE_ALIGNMENT = "center"
_TEMPLATE_TABLE_OUTER_BORDER_SIZE = 18
_TEMPLATE_TABLE_HEADER_BOTTOM_BORDER_SIZE = 6
_PUNCTUATION_SUFFIX = "：:。.;；、,，!！?？"
_HEADING_CHAPTER_RE = re.compile(r"^第\s*\d+\s*章(?:\s+.+)?$")
_HEADING_LEVEL1_RE = re.compile(r"^\d+\.\d+(?:\s+.+)?$")
_HEADING_LEVEL2_RE = re.compile(r"^\d+\.\d+\.\d+(?:\s+.+)?$")
_FIGURE_DOT_RE = re.compile(r"图\s*\d+\.\d+")
_TABLE_DOT_RE = re.compile(r"表\s*\d+\.\d+")
_EQUATION_DOT_RE = re.compile(r"[（(]\s*[1-9]\d{0,1}\.\d{1,2}\s*[）)]")
_FIGURE_CAPTION_RE = re.compile(r"^图\s*\d+-\d+(?:\s+|$)")
_TABLE_CAPTION_RE = re.compile(r"^表\s*\d+-\d+(?:\s+|$)")
_CONTINUED_TABLE_CAPTION_RE = re.compile(r"^续表\s*\d+-\d+(?:\s+|$)")
_CAPTION_RE = re.compile(r"^(图|表|续表)\s*(\d+-\d+)(\s+)(.+)$")
_CAPTION_PREFIX_RE = re.compile(r"^(?:图|表|续表)\s*\d+-\d+(?:\s+|$)")
_REFERENCE_ENTRY_RE = re.compile(r"^\[(\d+)\]")
_REFERENCE_TYPE_RE = re.compile(r"\[(?:M|J|D|C|R|P|EB/OL|OL|N|S|Z)(?:/[A-Z]+)?\]")
_KEYWORD_LINE_RE = re.compile(r"^(关键词|Key Words)\s*[：:]\s*(.+)$", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_ASCII_WORD_RE = re.compile(r"[A-Za-z0-9]")
_CJK_ASCII_ADJACENT_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff][A-Za-z]|[A-Za-z][\u3400-\u4dbf\u4e00-\u9fff]"
)


def _issue(
    code: str,
    severity: Severity,
    message: str,
    *,
    location: str | None = None,
    expected: str | None = None,
    actual: str | None = None,
    evidence: str | None = None,
) -> Issue:
    return Issue(
        code=code,
        severity=severity,
        message=message,
        location=location,
        expected=expected,
        actual=actual,
        evidence=evidence,
    )


def _paragraph_location(paragraph: ParagraphInfo) -> str:
    return f"paragraph {paragraph.index}"


def _is_toc_paragraph(paragraph: ParagraphInfo) -> bool:
    style = paragraph.style or ""
    text = paragraph.text.strip()
    if style.upper().startswith("TOC"):
        return True
    return bool("\t" in paragraph.text and re.search(r"\d+\s*$", text))


def _is_reference_heading(text: str) -> bool:
    return text.replace(" ", "") == "参考文献"


def _is_thanks_heading(text: str) -> bool:
    return text.replace(" ", "") == "致谢"


def _first_body_paragraph_index(document: DocumentInfo) -> int:
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if re.match(r"^第\s*1\s*章\b", text):
            return paragraph.index
    return 0


def _reference_heading_index(document: DocumentInfo) -> int | None:
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if _is_toc_paragraph(paragraph):
            continue
        if _is_reference_heading(text):
            return paragraph.index
    return None


def _thanks_heading_index(document: DocumentInfo) -> int | None:
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if _is_toc_paragraph(paragraph):
            continue
        if _is_thanks_heading(text):
            return paragraph.index
    return None


def _in_body_range(paragraph: ParagraphInfo, document: DocumentInfo) -> bool:
    first_body = _first_body_paragraph_index(document)
    reference_start = _reference_heading_index(document)
    if paragraph.index < first_body:
        return False
    if reference_start is not None and paragraph.index >= reference_start:
        return False
    return True


def _next_nonempty_paragraph(document: DocumentInfo, index: int) -> ParagraphInfo | None:
    for paragraph in document.paragraphs:
        if paragraph.index <= index:
            continue
        if paragraph.text.strip() or paragraph.has_drawing:
            return paragraph
    return None


def _previous_content_paragraph(document: DocumentInfo, index: int) -> ParagraphInfo | None:
    previous = None
    for paragraph in document.paragraphs:
        if paragraph.index >= index:
            break
        if paragraph.text.strip() or paragraph.has_drawing:
            previous = paragraph
    return previous


def _is_heading_text(text: str) -> bool:
    stripped = text.strip()
    return bool(
        _HEADING_CHAPTER_RE.match(stripped)
        or _HEADING_LEVEL1_RE.match(stripped)
        or _HEADING_LEVEL2_RE.match(stripped)
    )


def _style_heading_level(paragraph: ParagraphInfo) -> int | None:
    style_name = (paragraph.style_name or "").lower().replace("_", " ")
    match = re.match(r"heading\s*([1-3])$", style_name)
    if match:
        return int(match.group(1))
    style_id = (paragraph.style or "").lower()
    if style_id in {"heading1", "heading 1", "1"}:
        return 1
    if style_id in {"heading2", "heading 2", "2"}:
        return 2
    if style_id in {"heading3", "heading 3", "3"}:
        return 3
    return None


def _heading_level(paragraph: ParagraphInfo) -> int | None:
    text = paragraph.text.strip()
    if _HEADING_CHAPTER_RE.match(text):
        return 1
    if _HEADING_LEVEL2_RE.match(text):
        return 3
    if _HEADING_LEVEL1_RE.match(text):
        return 2
    return _style_heading_level(paragraph)


def _is_heading_paragraph(paragraph: ParagraphInfo) -> bool:
    return _heading_level(paragraph) is not None


def _is_caption_text(text: str) -> bool:
    return bool(_CAPTION_PREFIX_RE.match(text.strip()))


def _has_trailing_punctuation(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped) and stripped[-1] in _PUNCTUATION_SUFFIX


def _looks_like_body_paragraph(paragraph: ParagraphInfo) -> bool:
    text = paragraph.text.strip()
    if not text:
        return False
    if _is_toc_paragraph(paragraph):
        return False
    if _is_heading_paragraph(paragraph):
        return False
    if text == "参考文献" or text.startswith("参考文献"):
        return False
    if _KEYWORD_LINE_RE.match(text):
        return False
    if _REFERENCE_ENTRY_RE.match(text):
        return False
    if _is_caption_text(text):
        return False
    return True


def _line_spacing_check_start_index(document: DocumentInfo) -> int:
    for paragraph in document.paragraphs:
        if paragraph.text.strip().replace(" ", "") == "学位论文原创性声明":
            return paragraph.index
    for paragraph in document.paragraphs:
        if paragraph.text.strip().replace(" ", "") == "摘要":
            return paragraph.index
    return _first_body_paragraph_index(document)


def _looks_like_line_spacing_target(paragraph: ParagraphInfo, document: DocumentInfo) -> bool:
    text = paragraph.text.strip()
    if not text:
        return False
    if paragraph.index < _line_spacing_check_start_index(document):
        return False
    if _is_toc_paragraph(paragraph):
        return False
    normalized = text.replace(" ", "")
    if normalized in {
        "学位论文原创性声明",
        "学位论文版权使用授权书",
        "摘要",
        "目录",
        "参考文献",
        "致谢",
    }:
        return False
    if text == "Abstract":
        return False
    if _is_heading_paragraph(paragraph):
        return False
    if _is_caption_text(text):
        return False
    return True


def _looks_like_table_line_spacing_target(paragraph: ParagraphInfo) -> bool:
    text = paragraph.text.strip()
    if not text:
        return False
    if _is_heading_paragraph(paragraph):
        return False
    if _is_caption_text(text):
        return False
    return True


def _visible_runs(paragraph: ParagraphInfo):
    for run in paragraph.runs:
        if run.text.strip():
            yield run


def _font_matches(font: str | None, expected: str) -> bool:
    if font is None:
        return True
    normalized = font.lower().replace(" ", "")
    expected_normalized = expected.lower().replace(" ", "")
    if expected == "宋体":
        return "宋体" in font
    if expected == "黑体":
        return "黑体" in font
    if expected == "Times New Roman":
        return normalized in {"timesnewroman", "timenewroman"}
    return normalized == expected_normalized


def _run_font_actual(run) -> str:
    fonts = [font for font in (run.font_east_asia, run.font_ascii) if font]
    return "/".join(fonts) if fonts else "not explicit"


def _has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text))


def _has_ascii_word(text: str) -> bool:
    return bool(_ASCII_WORD_RE.search(text))


def _check_explicit_run_format(
    paragraph: ParagraphInfo,
    *,
    code: str,
    expected_size_pt: float | None = None,
    expected_east_asia: str | None = None,
    expected_ascii: str | None = None,
    require_bold: bool | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    for run in _visible_runs(paragraph):
        if expected_size_pt is not None and run.size_pt is not None:
            if abs(run.size_pt - expected_size_pt) > _FONT_SIZE_TOLERANCE_PT:
                issues.append(
                    _issue(
                        code,
                        Severity.WARNING,
                        "Explicit run font size does not match the expected format.",
                        location=_paragraph_location(paragraph),
                        expected=f"{expected_size_pt:g} pt",
                        actual=f"{run.size_pt:g} pt",
                        evidence=paragraph.text.strip(),
                    )
                )
                break
        if expected_east_asia is not None and run.font_east_asia is not None:
            if not _font_matches(run.font_east_asia, expected_east_asia):
                issues.append(
                    _issue(
                        code,
                        Severity.WARNING,
                        "Explicit East Asian font does not match the expected format.",
                        location=_paragraph_location(paragraph),
                        expected=expected_east_asia,
                        actual=_run_font_actual(run),
                        evidence=paragraph.text.strip(),
                    )
                )
                break
        if expected_ascii is not None and run.font_ascii is not None:
            if not _font_matches(run.font_ascii, expected_ascii):
                issues.append(
                    _issue(
                        code,
                        Severity.WARNING,
                        "Explicit ASCII font does not match the expected format.",
                        location=_paragraph_location(paragraph),
                        expected=expected_ascii,
                        actual=_run_font_actual(run),
                        evidence=paragraph.text.strip(),
                    )
                )
                break
        if require_bold is True and run.bold is False:
            issues.append(
                _issue(
                    code,
                    Severity.WARNING,
                    "Explicit run bold setting does not match the expected format.",
                    location=_paragraph_location(paragraph),
                    expected="bold",
                    actual="not bold",
                    evidence=paragraph.text.strip(),
                )
            )
            break
    return issues


def _check_heading_script_fonts(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        if not text or not _is_heading_paragraph(paragraph):
            continue
        for run in _visible_runs(paragraph):
            if _has_cjk(run.text) and run.font_east_asia is not None:
                if not _font_matches(run.font_east_asia, "黑体"):
                    issues.append(
                        _issue(
                            "HEADING_SCRIPT_FONT",
                            Severity.WARNING,
                            "Heading Chinese text should use Heiti.",
                            location=_paragraph_location(paragraph),
                            expected="中文=黑体",
                            actual=_run_font_actual(run),
                            evidence=text,
                        )
                    )
                    break
            if _has_ascii_word(run.text) and run.font_ascii is not None:
                if not (_font_matches(run.font_ascii, "Times New Roman") or _font_matches(run.font_ascii, "黑体")):
                    issues.append(
                        _issue(
                            "HEADING_SCRIPT_FONT",
                            Severity.WARNING,
                            "Heading numbers and English text should not use body ASCII fonts.",
                            location=_paragraph_location(paragraph),
                            expected="数字/英文=Times New Roman or heading Heiti style",
                            actual=_run_font_actual(run),
                            evidence=text,
                        )
                    )
                    break
    return issues


def _split_keywords(keyword_text: str) -> tuple[list[str], bool, bool]:
    has_ascii_separator = ";" in keyword_text
    items = [part.strip() for part in re.split(r"[；;]", keyword_text) if part.strip()]
    trailing_separator = keyword_text.rstrip().endswith(("；", ";"))
    return items, has_ascii_separator, trailing_separator


def _check_page_settings(document: DocumentInfo, rules: RuleSet) -> list[Issue]:
    issues: list[Issue] = []
    if not rules.expected_page:
        return issues
    if not document.sections:
        issues.append(
            _issue(
                "PAGE_SETUP_UNAVAILABLE",
                Severity.INFO,
                "No section metadata was available for page setup checks.",
            )
        )
        return issues

    for section in document.sections:
        actual = {
            "page_width_cm": section.page_width_cm,
            "page_height_cm": section.page_height_cm,
            "margin_top_cm": section.margin_top_cm,
            "margin_bottom_cm": section.margin_bottom_cm,
            "margin_left_cm": section.margin_left_cm,
            "margin_right_cm": section.margin_right_cm,
            "header_distance_cm": section.header_distance_cm,
            "footer_distance_cm": section.footer_distance_cm,
        }
        for key, expected_value in rules.expected_page.items():
            actual_value = actual.get(key)
            if actual_value is None:
                continue
            if abs(actual_value - expected_value) <= _PAGE_TOLERANCE_CM:
                continue
            issues.append(
                _issue(
                    "PAGE_SETUP",
                    Severity.WARNING,
                    f"Section {section.index} {key} does not match the expected page setting.",
                    location=f"section {section.index}",
                    expected=f"{expected_value:.1f} cm",
                    actual=f"{actual_value:.1f} cm",
                )
            )
    return issues


def _check_header_text(document: DocumentInfo, rules: RuleSet) -> list[Issue]:
    if not rules.expected_header_text:
        return []

    candidates = [header.strip() for header in document.headers if header.strip()]
    if not candidates:
        candidates = [line.strip() for line in document.full_text.splitlines() if line.strip()]

    if any(rules.expected_header_text in candidate for candidate in candidates):
        return []

    return [
        _issue(
            "HEADER_TEXT",
            Severity.WARNING,
            "Expected header text was not detected.",
            expected=rules.expected_header_text,
            actual="; ".join(candidates[:3]) if candidates else "not available",
        )
    ]


def _check_static_headers_and_page_numbers(document: DocumentInfo, rules: RuleSet) -> list[Issue]:
    issues: list[Issue] = []
    first_body = _first_body_paragraph_index(document)
    body_section = None
    if rules.expected_header_text:
        for section in document.sections:
            if any(rules.expected_header_text in text for text in section.header_texts):
                body_section = section
                break
    if body_section is None:
        for section in document.sections:
            body_section = section
            if section.page_number_start == 1 and section.footer_field_instructions:
                break
    if body_section is None and document.sections:
        body_section = document.sections[-1]
    if body_section is None:
        return issues

    if body_section.page_number_start is not None and body_section.page_number_start != 1:
        issues.append(
            _issue(
                "STATIC_PAGE_NUMBERING",
                Severity.WARNING,
                "Parsed body-like section page numbering does not restart at 1.",
                location=f"section {body_section.index}",
                expected="start=1",
                actual=f"start={body_section.page_number_start}",
            )
        )
    elif body_section.page_number_start is None:
        issues.append(
            _issue(
                "STATIC_PAGE_NUMBERING",
                Severity.INFO,
                "No explicit body-like section page-number restart was detected; verify page numbering in Word/PDF.",
                location=f"paragraph {first_body}",
                expected="正文第1章从阿拉伯数字 1 开始",
                actual="not explicit in section metadata",
            )
        )

    if rules.expected_header_text:
        header_candidates = [text.strip() for text in body_section.header_texts if text.strip()]
        if header_candidates and not any(rules.expected_header_text in text for text in header_candidates):
            issues.append(
                _issue(
                    "STATIC_BODY_HEADER",
                    Severity.WARNING,
                    "The parsed body-like section header does not contain the expected text.",
                    location=f"section {body_section.index}",
                    expected=rules.expected_header_text,
                    actual="; ".join(header_candidates[:3]),
                )
            )
        elif not header_candidates:
            issues.append(
                _issue(
                    "STATIC_BODY_HEADER",
                    Severity.INFO,
                    "No explicit body-like section header reference was detected; verify header display in Word/PDF.",
                    location=f"paragraph {first_body}",
                    expected=rules.expected_header_text,
                    actual="not explicit in section metadata",
                )
            )

    footer_fields = " ".join(body_section.footer_field_instructions).upper()
    if footer_fields and "PAGE" not in footer_fields:
        issues.append(
            _issue(
                "STATIC_PAGE_FIELD",
                Severity.WARNING,
                "Body-like section footer does not appear to contain a PAGE field.",
                location=f"section {body_section.index}",
                expected="PAGE field in footer",
                actual=footer_fields,
            )
        )
    elif not footer_fields:
        footer_text = " ".join(text.strip() for text in body_section.footer_texts if text.strip())
        if not footer_text:
            issues.append(
                _issue(
                    "STATIC_PAGE_FIELD",
                    Severity.INFO,
                    "No explicit footer page-number field was detected; verify page numbers in Word/PDF.",
                    location=f"section {body_section.index}",
                    expected="PAGE field in footer",
                    actual="not explicit in section metadata",
                )
            )
    return issues

def _check_headings(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        level = _heading_level(paragraph)
        if not text or level is None:
            continue
        if _has_trailing_punctuation(text):
            issues.append(
                _issue(
                    "HEADING_PUNCTUATION",
                    Severity.WARNING,
                    "Heading text should not end with punctuation.",
                    location=_paragraph_location(paragraph),
                    evidence=text,
                )
            )
        if level == 1:
            if paragraph.alignment is not None and paragraph.alignment != "center":
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "Chapter heading should be centered.",
                        location=_paragraph_location(paragraph),
                        expected="center",
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="HEADING_FORMAT",
                    expected_size_pt=18.0,
                    expected_east_asia="黑体",
                )
            )
        elif level == 3:
            if paragraph.alignment is not None and paragraph.alignment not in {"left", "both"}:
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "Second-level heading should be left aligned.",
                        location=_paragraph_location(paragraph),
                        expected="left",
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="HEADING_FORMAT",
                    expected_size_pt=14.0,
                    expected_east_asia="黑体",
                )
            )
        elif level == 2:
            if paragraph.alignment is not None and paragraph.alignment not in {"left", "both"}:
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "First-level heading should be left aligned.",
                        location=_paragraph_location(paragraph),
                        expected="left",
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="HEADING_FORMAT",
                    expected_size_pt=16.0,
                    expected_east_asia="黑体",
                )
            )
    return issues


def _check_numbering(paragraph: ParagraphInfo) -> list[Issue]:
    if _is_toc_paragraph(paragraph):
        return []
    text = paragraph.text.strip()
    if not text:
        return []

    issues: list[Issue] = []
    if _FIGURE_DOT_RE.search(text):
        issues.append(
            _issue(
                "FIGURE_NUMBERING",
                Severity.WARNING,
                "Figure numbering should use a hyphen rather than a dot.",
                location=_paragraph_location(paragraph),
                evidence=text,
            )
        )
    if _TABLE_DOT_RE.search(text):
        issues.append(
            _issue(
                "TABLE_NUMBERING",
                Severity.WARNING,
                "Table numbering should use a hyphen rather than a dot.",
                location=_paragraph_location(paragraph),
                evidence=text,
            )
        )
    if _EQUATION_DOT_RE.search(text):
        issues.append(
            _issue(
                "EQUATION_NUMBERING",
                Severity.WARNING,
                "Equation numbering should use a hyphen rather than a dot.",
                location=_paragraph_location(paragraph),
                evidence=text,
            )
        )
    return issues


def _check_keywords(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        match = _KEYWORD_LINE_RE.match(text)
        if not match:
            continue

        label = match.group(1)
        keyword_text = match.group(2).strip()
        items, has_ascii_separator, has_trailing_separator = _split_keywords(keyword_text)

        if has_ascii_separator:
            issues.append(
                _issue(
                    "KEYWORD_SEPARATOR",
                    Severity.WARNING,
                    f"{label} line should use Chinese semicolons as separators.",
                    location=_paragraph_location(paragraph),
                    evidence=text,
                )
            )
        if has_trailing_separator:
            issues.append(
                _issue(
                    "KEYWORD_TERMINATOR",
                    Severity.WARNING,
                    f"{label} line should not end with a semicolon.",
                    location=_paragraph_location(paragraph),
                    evidence=text,
                )
            )
        if not 3 <= len(items) <= 5:
            issues.append(
                _issue(
                    "KEYWORD_COUNT",
                    Severity.WARNING,
                    f"{label} line should contain 3 to 5 keywords.",
                    location=_paragraph_location(paragraph),
                    expected="3-5 keywords",
                    actual=f"{len(items)} keywords",
                    evidence=text,
                )
            )
    return issues


def _check_structure_presence(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    texts = [paragraph.text.strip() for paragraph in document.paragraphs if not _is_toc_paragraph(paragraph)]
    normalized = [text.replace(" ", "") for text in texts]
    required = {
        "STRUCTURE_ABSTRACT_CN": ("摘  要", "Chinese abstract heading was not detected."),
        "STRUCTURE_ABSTRACT_EN": ("Abstract", "English abstract heading was not detected."),
        "STRUCTURE_TOC": ("目录", "Table of contents heading was not detected."),
        "STRUCTURE_BODY_START": ("第1章", "Chapter 1 heading was not detected."),
        "STRUCTURE_REFERENCES": ("参考文献", "References heading was not detected."),
        "STRUCTURE_THANKS": ("致谢", "Acknowledgements heading was not detected."),
    }
    for code, (needle, message) in required.items():
        if code == "STRUCTURE_TOC":
            found = any("目录" in text.replace(" ", "") for text in texts)
        elif code == "STRUCTURE_ABSTRACT_EN":
            found = any(text == "Abstract" for text in texts)
        elif code == "STRUCTURE_BODY_START":
            found = any(text.startswith("第1章") for text in texts)
        else:
            found = needle.replace(" ", "") in normalized
        if not found:
            issues.append(_issue(code, Severity.WARNING, message, expected=needle))
    return issues


def _check_abstract_format(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        normalized = text.replace(" ", "")
        if normalized == "摘要":
            if paragraph.alignment is not None and paragraph.alignment != "center":
                issues.append(
                    _issue(
                        "ABSTRACT_FORMAT",
                        Severity.WARNING,
                        "Chinese abstract heading should be centered.",
                        location=_paragraph_location(paragraph),
                        expected="center",
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="ABSTRACT_FORMAT",
                    expected_size_pt=18.0,
                    expected_east_asia="黑体",
                )
            )
        elif text == "Abstract":
            if paragraph.alignment is not None and paragraph.alignment != "center":
                issues.append(
                    _issue(
                        "ABSTRACT_FORMAT",
                        Severity.WARNING,
                        "English abstract heading should be centered.",
                        location=_paragraph_location(paragraph),
                        expected="center",
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="ABSTRACT_FORMAT",
                    expected_size_pt=18.0,
                    expected_ascii="Times New Roman",
                    require_bold=True,
                )
            )
    return issues


def _check_references(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    reference_started = False

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if _is_toc_paragraph(paragraph):
            continue

        if not reference_started:
            if _is_reference_heading(text):
                reference_started = True
            continue

        normalized = text.replace(" ", "")
        if _is_heading_text(text) or normalized in {"致谢", "附录", "附录A", "附录B"}:
            break

        if not (_REFERENCE_ENTRY_RE.match(text) or _REFERENCE_TYPE_RE.search(text)):
            issues.append(
                _issue(
                    "REFERENCE_FORMAT",
                    Severity.WARNING,
                    "Reference entry does not contain a recognizable literature type marker.",
                    location=_paragraph_location(paragraph),
                    evidence=text,
                )
            )
    return issues


def _check_toc_fields(document: DocumentInfo) -> list[Issue]:
    has_toc_heading = any("目录" in paragraph.text.replace(" ", "") for paragraph in document.paragraphs)
    if not has_toc_heading:
        return []
    has_toc_field = any(
        instruction.strip().upper().startswith("TOC")
        for paragraph in document.paragraphs
        for instruction in paragraph.field_instructions
    )
    if has_toc_field:
        return []
    return [
        _issue(
            "TOC_FIELD",
            Severity.WARNING,
            "Table of contents field code was not detected; page numbers may be manually typed or stale.",
            expected="Word TOC field",
            actual="not detected",
        )
    ]


def _check_table_borders(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    first_body = _first_body_paragraph_index(document)
    reference_start = _reference_heading_index(document)
    for table in document.tables:
        if not _looks_like_data_table(table):
            continue
        if table.block_index is None:
            continue
        if table.block_index < first_body:
            continue
        if reference_start is not None:
            ref_block = document.paragraphs[reference_start].block_index
            if ref_block is not None and table.block_index >= ref_block:
                continue

        visible_borders = _visible_table_border_names(table)
        vertical_borders = sorted(visible_borders & {"left", "right", "start", "end", "insideV"})
        if vertical_borders:
            issues.append(
                _issue(
                    "TABLE_BORDER",
                    Severity.WARNING,
                    "Table has explicit vertical borders; template expects three-line-table style.",
                    location=f"table {table.index}",
                    expected="no visible vertical borders",
                    actual=", ".join(vertical_borders),
                )
            )
            continue

        missing_three_line_borders = sorted({"top", "bottom"} - visible_borders)
        if visible_borders and missing_three_line_borders:
            issues.append(
                _issue(
                    "TABLE_THREE_LINE",
                    Severity.WARNING,
                    "Table border metadata does not look like a complete three-line table.",
                    location=f"table {table.index}",
                    expected="visible top and bottom borders; no vertical borders",
                    actual=f"missing {', '.join(missing_three_line_borders)}",
                    evidence=", ".join(table.border_values[:12]),
                )
            )
        issues.extend(_check_table_template_layout(table))
    return issues


def _check_table_template_layout(table: TableInfo) -> list[Issue]:
    issues: list[Issue] = []
    if table.width_type != _TEMPLATE_TABLE_WIDTH_TYPE or table.width_value != _TEMPLATE_TABLE_WIDTH_VALUE:
        issues.append(
            _issue(
                "TABLE_WIDTH",
                Severity.WARNING,
                "Table width does not match the empty template.",
                location=f"table {table.index}",
                expected="100% page text width (w:tblW type=pct w=5000)",
                actual=f"type={table.width_type or 'not explicit'} w={table.width_value or 'not explicit'}",
            )
        )
    if table.alignment != _TEMPLATE_TABLE_ALIGNMENT:
        issues.append(
            _issue(
                "TABLE_ALIGNMENT",
                Severity.WARNING,
                "Table alignment does not match the empty template.",
                location=f"table {table.index}",
                expected="center",
                actual=table.alignment or "not explicit",
            )
        )

    border_sizes = _table_border_size_map(table)
    for border_name in ("top", "bottom"):
        actual_size = border_sizes.get(border_name)
        if actual_size != _TEMPLATE_TABLE_OUTER_BORDER_SIZE:
            issues.append(
                _issue(
                    "TABLE_BORDER_WIDTH",
                    Severity.WARNING,
                    "Table outer border width does not match the empty template.",
                    location=f"table {table.index}",
                    expected=f"{_TEMPLATE_TABLE_OUTER_BORDER_SIZE} eighths of a point (2.25 pt)",
                    actual=(
                        _format_border_size(actual_size)
                        if actual_size is not None
                        else f"{border_name} border size not explicit"
                    ),
                    evidence=", ".join(table.border_sizes[:8]),
                )
            )

    expected_header_cells = max((len(row) for row in table.rows[:1]), default=0)
    header_sizes = table.header_bottom_border_sizes
    if (
        not header_sizes
        or len(header_sizes) < expected_header_cells
        or any(size != _TEMPLATE_TABLE_HEADER_BOTTOM_BORDER_SIZE for size in header_sizes)
    ):
        issues.append(
            _issue(
                "TABLE_HEADER_BORDER",
                Severity.WARNING,
                "Table header bottom border width does not match the empty template.",
                location=f"table {table.index}",
                expected=f"{_TEMPLATE_TABLE_HEADER_BOTTOM_BORDER_SIZE} eighths of a point (0.75 pt) on each header cell",
                actual=", ".join(_format_border_size(size) for size in header_sizes) if header_sizes else "not explicit",
            )
        )
    return issues


def _looks_like_data_table(table: TableInfo) -> bool:
    if len(table.rows) < 2:
        return False
    max_columns = max((len(row) for row in table.rows), default=0)
    if max_columns < 2:
        return False
    return any(any(cell.strip() for cell in row) for row in table.rows)


def _visible_table_border_names(table: TableInfo) -> set[str]:
    visible: set[str] = set()
    for item in table.border_values:
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        if value not in {"nil", "none"}:
            visible.add(name)
    return visible


def _table_border_size_map(table: TableInfo) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in table.border_sizes:
        if "=" not in item:
            continue
        name, value = item.split("=", 1)
        try:
            result[name] = int(value)
        except ValueError:
            continue
    return result


def _format_border_size(size: int) -> str:
    return f"{size} eighths of a point ({size / 8:g} pt)"


def _caption_paragraphs(document: DocumentInfo) -> list[tuple[ParagraphInfo, str]]:
    result: list[tuple[ParagraphInfo, str]] = []
    for paragraph in document.paragraphs:
        if _is_caption_text(paragraph.text):
            result.append((paragraph, _paragraph_location(paragraph)))
    for table in document.tables:
        for paragraph in table.paragraphs:
            if _is_caption_text(paragraph.text):
                result.append((paragraph, f"table {table.index} paragraph {paragraph.index}"))
    return result


def _check_captions(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph, location in _caption_paragraphs(document):
        text = paragraph.text.strip()
        match = _CAPTION_RE.match(text)
        if not match:
            issues.append(
                _issue(
                    "CAPTION_SEPARATOR",
                    Severity.WARNING,
                    "Caption should contain exactly one half-width space between the number and title.",
                    location=location,
                    expected="图3-1 Caption / 表3-1 Caption / 续表3-1 Caption",
                    actual=text,
                    evidence=text,
                )
            )
        elif match.group(3) != " ":
            issues.append(
                _issue(
                    "CAPTION_SEPARATOR",
                    Severity.WARNING,
                    "Caption should use exactly one half-width space between the number and title.",
                    location=location,
                    expected="one half-width space",
                    actual=f"{len(match.group(3))} space characters",
                    evidence=text,
                )
            )

        if paragraph.alignment is not None and paragraph.alignment != "center":
            issues.append(
                _issue(
                    "CAPTION_FORMAT",
                    Severity.WARNING,
                    "Caption should be centered.",
                    location=location,
                    expected="center",
                    actual=paragraph.alignment,
                    evidence=text,
                )
            )

        for run in _visible_runs(paragraph):
            if run.size_pt is not None and abs(run.size_pt - 12.0) > _FONT_SIZE_TOLERANCE_PT:
                issues.append(
                    _issue(
                        "CAPTION_FORMAT",
                        Severity.WARNING,
                        "Caption font size should be xiaosi / 12 pt.",
                        location=location,
                        expected="12 pt",
                        actual=f"{run.size_pt:g} pt",
                        evidence=text,
                    )
                )
                break
            if run.font_east_asia is not None and not _font_matches(run.font_east_asia, "宋体"):
                issues.append(
                    _issue(
                        "CAPTION_FORMAT",
                        Severity.WARNING,
                        "Caption East Asian font should be Songti.",
                        location=location,
                        expected="宋体",
                        actual=_run_font_actual(run),
                        evidence=text,
                    )
                )
                break
            if _has_ascii_word(run.text) and run.font_ascii is not None:
                if not _font_matches(run.font_ascii, "宋体"):
                    issues.append(
                        _issue(
                            "CAPTION_FORMAT",
                            Severity.WARNING,
                            "Caption ASCII text and numbers should follow the caption Songti style.",
                            location=location,
                            expected="宋体",
                            actual=_run_font_actual(run),
                            evidence=text,
                        )
                    )
                    break

        if paragraph.line_spacing_multiple is not None:
            issues.append(
                _issue(
                    "CAPTION_LINE_SPACING",
                    Severity.WARNING,
                    "Caption line spacing should be fixed at 20 pt, not multiple/auto line spacing.",
                    location=location,
                    expected="fixed 20 pt",
                    actual=f"{paragraph.line_spacing_multiple:g}x ({paragraph.line_spacing_rule or 'auto'})",
                    evidence=text,
                )
            )
        elif paragraph.line_spacing_pt is not None:
            if paragraph.line_spacing_rule not in {None, "exact", "fixed"}:
                issues.append(
                    _issue(
                        "CAPTION_LINE_SPACING",
                        Severity.WARNING,
                        "Caption line spacing should be fixed at 20 pt.",
                        location=location,
                        expected="fixed 20 pt",
                        actual=f"{paragraph.line_spacing_pt:.1f} pt ({paragraph.line_spacing_rule})",
                        evidence=text,
                    )
                )
            elif abs(paragraph.line_spacing_pt - 20.0) > _LINE_SPACING_TOLERANCE_PT:
                issues.append(
                    _issue(
                        "CAPTION_LINE_SPACING",
                        Severity.WARNING,
                        "Caption line spacing should be fixed at 20 pt.",
                        location=location,
                        expected="20 pt",
                        actual=f"{paragraph.line_spacing_pt:.1f} pt",
                        evidence=text,
                    )
                )
    return issues


def _check_caption_object_order(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    tables_by_block = [table for table in document.tables if table.block_index is not None]
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not _in_body_range(paragraph, document):
            continue
        if _FIGURE_CAPTION_RE.match(text):
            previous = _previous_content_paragraph(document, paragraph.index)
            if previous is not None and not previous.has_drawing:
                next_paragraph = _next_nonempty_paragraph(document, paragraph.index)
                if next_paragraph is not None and next_paragraph.has_drawing:
                    issues.append(
                        _issue(
                            "FIGURE_CAPTION_POSITION",
                            Severity.WARNING,
                            "Figure caption appears before the image; template expects figure captions below figures.",
                            location=_paragraph_location(paragraph),
                            expected="image before caption",
                            actual="image after caption",
                            evidence=text,
                        )
                    )
        if _TABLE_CAPTION_RE.match(text) and paragraph.block_index is not None:
            previous_table = next(
                (table for table in reversed(tables_by_block) if table.block_index is not None and table.block_index < paragraph.block_index),
                None,
            )
            next_table = next(
                (table for table in tables_by_block if table.block_index is not None and table.block_index > paragraph.block_index),
                None,
            )
            if previous_table is not None and next_table is None:
                issues.append(
                    _issue(
                        "TABLE_CAPTION_POSITION",
                        Severity.WARNING,
                        "Table caption appears after a table; template expects table captions above tables.",
                        location=_paragraph_location(paragraph),
                        expected="caption before table",
                        actual=f"caption after table {previous_table.index}",
                        evidence=text,
                    )
                )
            elif previous_table is not None and next_table is not None:
                prev_distance = paragraph.block_index - (previous_table.block_index or paragraph.block_index)
                next_distance = (next_table.block_index or paragraph.block_index) - paragraph.block_index
                if prev_distance <= 2 and next_distance > 2:
                    issues.append(
                        _issue(
                            "TABLE_CAPTION_POSITION",
                            Severity.WARNING,
                            "Table caption is closer to the preceding table than to a following table.",
                            location=_paragraph_location(paragraph),
                            expected="caption before table",
                            actual=f"near table {previous_table.index}",
                            evidence=text,
                        )
                    )
    return issues


def _check_continued_table_layout(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    tables_by_block = [table for table in document.tables if table.block_index is not None]
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not _CONTINUED_TABLE_CAPTION_RE.match(text):
            continue
        if paragraph.block_index is None:
            issues.append(
                _issue(
                    "CONTINUED_TABLE_LAYOUT",
                    Severity.INFO,
                    "Continued-table caption block position was unavailable; verify it in Word/PDF.",
                    location=_paragraph_location(paragraph),
                    evidence=text,
                )
            )
            continue

        previous_table = next(
            (
                table
                for table in reversed(tables_by_block)
                if table.block_index is not None and table.block_index < paragraph.block_index
            ),
            None,
        )
        next_table = next(
            (
                table
                for table in tables_by_block
                if table.block_index is not None and table.block_index > paragraph.block_index
            ),
            None,
        )
        if previous_table is None:
            issues.append(
                _issue(
                    "CONTINUED_TABLE_LAYOUT",
                    Severity.WARNING,
                    "Continued-table caption should follow the first table fragment.",
                    location=_paragraph_location(paragraph),
                    expected="table fragment before continued caption",
                    actual="no previous table fragment detected",
                    evidence=text,
                )
            )
        if next_table is None:
            issues.append(
                _issue(
                    "CONTINUED_TABLE_LAYOUT",
                    Severity.WARNING,
                    "Continued-table caption should be directly above a continued table fragment.",
                    location=_paragraph_location(paragraph),
                    expected="continued table fragment after caption",
                    actual="no following table fragment detected",
                    evidence=text,
                )
            )
            continue
        if (next_table.block_index or paragraph.block_index) - paragraph.block_index > 2:
            issues.append(
                _issue(
                    "CONTINUED_TABLE_LAYOUT",
                    Severity.WARNING,
                    "Continued-table caption is not close to the following table fragment.",
                    location=_paragraph_location(paragraph),
                    expected="caption immediately above continued table fragment",
                    actual=f"next table block {next_table.block_index}",
                    evidence=text,
                )
            )
        if previous_table is not None and previous_table.rows and next_table.rows:
            previous_header = previous_table.rows[0]
            next_header = next_table.rows[0]
            if previous_header != next_header:
                issues.append(
                    _issue(
                        "CONTINUED_TABLE_LAYOUT",
                        Severity.WARNING,
                        "Continued table should repeat the same header row as the first table fragment.",
                        location=_paragraph_location(paragraph),
                        expected=" | ".join(previous_header),
                        actual=" | ".join(next_header),
                        evidence=text,
                    )
                )
    return issues


def _check_table_cell_typography(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    first_body = _first_body_paragraph_index(document)
    reference_start = _reference_heading_index(document)
    reference_block = document.paragraphs[reference_start].block_index if reference_start is not None else None
    for table in document.tables:
        if table.block_index is None:
            continue
        if table.block_index < first_body:
            continue
        if reference_block is not None and table.block_index >= reference_block:
            continue
        for paragraph in table.paragraphs:
            text = paragraph.text.strip()
            if not text or _is_caption_text(text):
                continue
            location = f"table {table.index} paragraph {paragraph.index}"
            for run in _visible_runs(paragraph):
                if run.size_pt is not None and abs(run.size_pt - 12.0) > _FONT_SIZE_TOLERANCE_PT:
                    issues.append(
                        _issue(
                            "TABLE_CELL_FORMAT",
                            Severity.WARNING,
                            "Table cell text should be xiaosi / 12 pt.",
                            location=location,
                            expected="12 pt",
                            actual=f"{run.size_pt:g} pt",
                            evidence=text,
                        )
                    )
                    break
                if _has_ascii_word(run.text) and run.font_ascii is not None:
                    if not _font_matches(run.font_ascii, "Times New Roman"):
                        issues.append(
                            _issue(
                                "TABLE_CELL_FONT",
                                Severity.WARNING,
                                "Table cell English and numbers should use Times New Roman.",
                                location=location,
                                expected="Times New Roman",
                                actual=_run_font_actual(run),
                                evidence=text,
                            )
                        )
                        break
                if _has_cjk(run.text) and run.font_east_asia is not None:
                    if not _font_matches(run.font_east_asia, "宋体"):
                        issues.append(
                            _issue(
                                "TABLE_CELL_FONT",
                                Severity.WARNING,
                                "Table cell Chinese text should use Songti.",
                                location=location,
                                expected="宋体",
                                actual=_run_font_actual(run),
                                evidence=text,
                            )
                        )
                        break
    return issues


def _check_page_numbering_static(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    if not document.sections:
        return issues
    first_body = _first_body_paragraph_index(document)
    body_section = None
    for section in document.sections:
        if section.page_number_start is not None:
            body_section = section
            break
    if body_section is None:
        issues.append(
            _issue(
                "PAGE_NUMBERING_STATIC",
                Severity.INFO,
                "No explicit page-number restart metadata was detected; verify page numbering in Word.",
                location=f"paragraph {first_body}",
                expected="正文第1章从阿拉伯数字 1 开始",
                actual="not explicit in parsed section metadata",
            )
        )
    elif body_section.page_number_start != 1:
        issues.append(
            _issue(
                "PAGE_NUMBERING_STATIC",
                Severity.WARNING,
                "Detected page-number restart does not start at 1.",
                location=f"section {body_section.index}",
                expected="start=1",
                actual=f"start={body_section.page_number_start}",
            )
        )
    return issues


def _check_reference_typography(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    reference_started = False
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text or _is_toc_paragraph(paragraph):
            continue
        normalized = text.replace(" ", "")
        if not reference_started:
            if _is_reference_heading(text):
                reference_started = True
                if paragraph.alignment is not None and paragraph.alignment != "center":
                    issues.append(
                        _issue(
                            "REFERENCE_HEADING_FORMAT",
                            Severity.WARNING,
                            "References heading should be centered.",
                            location=_paragraph_location(paragraph),
                            expected="center",
                            actual=paragraph.alignment,
                            evidence=text,
                        )
                    )
                issues.extend(
                    _check_explicit_run_format(
                        paragraph,
                        code="REFERENCE_HEADING_FORMAT",
                        expected_size_pt=18.0,
                        expected_east_asia="黑体",
                    )
                )
            continue

        if _is_heading_text(text) or normalized in {"致谢", "附录", "附录A", "附录B"}:
            break
        issues.extend(
            _check_explicit_run_format(
                paragraph,
                code="REFERENCE_LIST_FORMAT",
                expected_size_pt=10.5,
                expected_east_asia="宋体",
            )
        )
    return issues


def _check_empty_paragraphs(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    run_start: ParagraphInfo | None = None
    run_length = 0
    first_body_index = _first_body_paragraph_index(document)

    for paragraph in document.paragraphs:
        if paragraph.index < first_body_index:
            continue
        if paragraph.text.strip():
            if run_length >= 2 and run_start is not None:
                issues.append(
                    _issue(
                        "EMPTY_PARAGRAPHS",
                        Severity.WARNING,
                        "Consecutive empty paragraphs were detected.",
                        location=_paragraph_location(run_start),
                        actual=f"{run_length} consecutive empty paragraphs",
                    )
                )
            run_start = None
            run_length = 0
            continue

        if run_start is None:
            run_start = paragraph
        run_length += 1

    if run_length >= 2 and run_start is not None:
        issues.append(
            _issue(
                "EMPTY_PARAGRAPHS",
                Severity.WARNING,
                "Consecutive empty paragraphs were detected.",
                location=_paragraph_location(run_start),
                actual=f"{run_length} consecutive empty paragraphs",
            )
        )

    return issues


def _check_body_typography(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        if not _in_body_range(paragraph, document):
            continue
        if not _looks_like_body_paragraph(paragraph):
            continue
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        if paragraph.first_line_indent_chars is not None:
            if abs(paragraph.first_line_indent_chars - 2.0) > _INDENT_TOLERANCE_CHARS:
                issues.append(
                    _issue(
                        "BODY_INDENT",
                        Severity.WARNING,
                        "Body paragraph first-line indent should be 2 characters.",
                        location=_paragraph_location(paragraph),
                        expected="2 characters",
                        actual=f"{paragraph.first_line_indent_chars:g} characters",
                        evidence=text,
                    )
                )
        issues.extend(
            _check_explicit_run_format(
                paragraph,
                code="BODY_FONT",
                expected_size_pt=12.0,
                expected_east_asia="宋体",
                expected_ascii="Times New Roman",
            )
        )
    return issues


def _mixed_language_spacing_evidence(text: str) -> str:
    match = _CJK_ASCII_ADJACENT_RE.search(text)
    if not match:
        return text
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 20)
    return text[start:end]


def _mixed_language_check_start_index(document: DocumentInfo) -> int:
    for paragraph in document.paragraphs:
        if paragraph.text.strip().replace(" ", "") == "摘要":
            return paragraph.index
    return _first_body_paragraph_index(document)


def _check_mixed_language_spacing(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    reference_start = _reference_heading_index(document)
    thanks_start = _thanks_heading_index(document)
    stop_index = reference_start if reference_start is not None else thanks_start
    seen: set[int] = set()
    for paragraph in document.paragraphs:
        if paragraph.index in seen:
            continue
        seen.add(paragraph.index)
        if paragraph.index < _mixed_language_check_start_index(document):
            continue
        if stop_index is not None and paragraph.index >= stop_index:
            continue
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        if not text or text == "Abstract":
            continue
        if _is_heading_paragraph(paragraph) or _is_caption_text(text):
            continue
        if re.search(r"https?://|www\.|[A-Za-z]:[/\\]", text):
            continue
        if _CJK_ASCII_ADJACENT_RE.search(text):
            issues.append(
                _issue(
                    "MIXED_LANGUAGE_SPACING",
                    Severity.INFO,
                    "Chinese text and adjacent English words/numbers should usually be separated by one half-width space.",
                    location=_paragraph_location(paragraph),
                    expected="中文 English 中文",
                    actual="Chinese/English adjacent without a space",
                    evidence=_mixed_language_spacing_evidence(text),
                )
            )
    return issues


def _check_thanks_format(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    thanks_index = _thanks_heading_index(document)
    if thanks_index is None:
        return issues
    for paragraph in document.paragraphs:
        if paragraph.index < thanks_index:
            continue
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.index == thanks_index:
            if paragraph.alignment is not None and paragraph.alignment != "center":
                issues.append(
                    _issue(
                        "THANKS_HEADING_FORMAT",
                        Severity.WARNING,
                        "Acknowledgements heading should be centered.",
                        location=_paragraph_location(paragraph),
                        expected="center",
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="THANKS_HEADING_FORMAT",
                    expected_size_pt=18.0,
                    expected_east_asia="黑体",
                )
            )
            continue
        if _is_heading_text(text):
            break
        if paragraph.first_line_indent_chars is not None:
            if abs(paragraph.first_line_indent_chars - 2.0) > _INDENT_TOLERANCE_CHARS:
                issues.append(
                    _issue(
                        "THANKS_BODY_FORMAT",
                        Severity.WARNING,
                        "Acknowledgements body should use 2-character first-line indent.",
                        location=_paragraph_location(paragraph),
                        expected="2 characters",
                        actual=f"{paragraph.first_line_indent_chars:g} characters",
                        evidence=text,
                    )
                )
        issues.extend(
            _check_explicit_run_format(
                paragraph,
                code="THANKS_BODY_FORMAT",
                expected_size_pt=12.0,
                expected_east_asia="宋体",
            )
        )
    return issues


def _check_line_spacing(document: DocumentInfo) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        if not _looks_like_line_spacing_target(paragraph, document):
            continue
        issues.extend(_line_spacing_issues_for_paragraph(paragraph, _paragraph_location(paragraph)))

    first_body = _first_body_paragraph_index(document)
    reference_start = _reference_heading_index(document)
    reference_block = document.paragraphs[reference_start].block_index if reference_start is not None else None
    for table in document.tables:
        if table.block_index is None:
            continue
        if table.block_index < first_body:
            continue
        if reference_block is not None and table.block_index >= reference_block:
            continue
        for paragraph in table.paragraphs:
            if not _looks_like_table_line_spacing_target(paragraph):
                continue
            issues.extend(
                _line_spacing_issues_for_paragraph(
                    paragraph,
                    f"table {table.index} paragraph {paragraph.index}",
                )
            )
    return issues


def _line_spacing_issues_for_paragraph(paragraph: ParagraphInfo, location: str) -> list[Issue]:
    issues: list[Issue] = []
    if paragraph.line_spacing_multiple is not None:
        issues.append(
            _issue(
                "LINE_SPACING",
                Severity.WARNING,
                "Text paragraph line spacing should be fixed at 20 pt, not multiple/auto line spacing.",
                location=location,
                expected="fixed 20 pt",
                actual=f"{paragraph.line_spacing_multiple:g}x ({paragraph.line_spacing_rule or 'auto'})",
                evidence=paragraph.text.strip(),
            )
        )
        return issues
    if paragraph.line_spacing_pt is None:
        return issues
    if paragraph.line_spacing_rule not in {None, "exact", "fixed"}:
        issues.append(
            _issue(
                "LINE_SPACING",
                Severity.WARNING,
                "Text paragraph line spacing should be fixed at 20 pt.",
                location=location,
                expected="fixed 20 pt",
                actual=f"{paragraph.line_spacing_pt:.1f} pt ({paragraph.line_spacing_rule})",
                evidence=paragraph.text.strip(),
            )
        )
        return issues
    if abs(paragraph.line_spacing_pt - 20.0) <= _LINE_SPACING_TOLERANCE_PT:
        return issues
    issues.append(
        _issue(
            "LINE_SPACING",
            Severity.WARNING,
            "Text paragraph line spacing should be fixed at 20 pt.",
            location=location,
            expected="20 pt",
            actual=f"{paragraph.line_spacing_pt:.1f} pt",
        )
    )
    return issues


def run_checks(document: DocumentInfo, rules: RuleSet) -> CheckResult:
    """Run all supported checks."""
    issues: list[Issue] = []
    issues.extend(_check_structure_presence(document))
    issues.extend(_check_page_settings(document, rules))
    issues.extend(_check_header_text(document, rules))
    issues.extend(_check_static_headers_and_page_numbers(document, rules))
    issues.extend(_check_abstract_format(document))
    issues.extend(_check_headings(document))
    issues.extend(_check_heading_script_fonts(document))
    for paragraph in document.paragraphs:
        issues.extend(_check_numbering(paragraph))
    issues.extend(_check_keywords(document))
    issues.extend(_check_references(document))
    issues.extend(_check_toc_fields(document))
    issues.extend(_check_table_borders(document))
    issues.extend(_check_captions(document))
    issues.extend(_check_caption_object_order(document))
    issues.extend(_check_continued_table_layout(document))
    issues.extend(_check_page_numbering_static(document))
    issues.extend(_check_reference_typography(document))
    issues.extend(_check_empty_paragraphs(document))
    issues.extend(_check_body_typography(document))
    issues.extend(_check_table_cell_typography(document))
    issues.extend(_check_thanks_format(document))
    issues.extend(_check_line_spacing(document))
    return CheckResult(
        issues=tuple(issues),
        checked_items=(
            "STRUCTURE_ABSTRACT_CN",
            "STRUCTURE_ABSTRACT_EN",
            "STRUCTURE_TOC",
            "STRUCTURE_BODY_START",
            "STRUCTURE_REFERENCES",
            "STRUCTURE_THANKS",
            "PAGE_SETUP",
            "HEADER_TEXT",
            "STATIC_BODY_HEADER",
            "STATIC_PAGE_FIELD",
            "ABSTRACT_FORMAT",
            "HEADING_PUNCTUATION",
            "HEADING_FORMAT",
            "HEADING_SCRIPT_FONT",
            "FIGURE_NUMBERING",
            "TABLE_NUMBERING",
            "EQUATION_NUMBERING",
            "KEYWORD_SEPARATOR",
            "KEYWORD_TERMINATOR",
            "KEYWORD_COUNT",
            "REFERENCE_FORMAT",
            "TOC_FIELD",
            "TABLE_BORDER",
            "TABLE_THREE_LINE",
            "TABLE_BORDER_WIDTH",
            "TABLE_HEADER_BORDER",
            "TABLE_WIDTH",
            "TABLE_ALIGNMENT",
            "CAPTION_SEPARATOR",
            "CAPTION_FORMAT",
            "CAPTION_LINE_SPACING",
            "FIGURE_CAPTION_POSITION",
            "TABLE_CAPTION_POSITION",
            "CONTINUED_TABLE_LAYOUT",
            "PAGE_NUMBERING_STATIC",
            "REFERENCE_HEADING_FORMAT",
            "REFERENCE_LIST_FORMAT",
            "EMPTY_PARAGRAPHS",
            "BODY_INDENT",
            "BODY_FONT",
            "TABLE_CELL_FORMAT",
            "TABLE_CELL_FONT",
            "THANKS_HEADING_FORMAT",
            "THANKS_BODY_FORMAT",
            "LINE_SPACING",
        ),
        unsupported_items=rules.manual_review_items,
    )
