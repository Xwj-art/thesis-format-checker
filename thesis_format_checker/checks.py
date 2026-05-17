from __future__ import annotations

import re

from .model import CheckResult, DocumentInfo, Issue, ParagraphInfo, RuleSet, Severity, TableInfo
from .rules import default_rules


_HEADING_CHAPTER_RE = re.compile(r"^第\s*\d+\s*章(?:\s+.+)?$")
_HEADING_LEVEL1_RE = re.compile(r"^\d+\.\d+(?:\s+.+)?$")
_HEADING_LEVEL2_RE = re.compile(r"^\d+\.\d+\.\d+(?:\s+.+)?$")
_REFERENCE_ENTRY_RE = re.compile(r"^\[(\d+)\]")
_REFERENCE_TYPE_RE = re.compile(r"\[(?:M|J|D|C|R|P|EB/OL|OL|N|S|Z)(?:/[A-Z]+)?\]")
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_ASCII_WORD_RE = re.compile(r"[A-Za-z0-9]")
_CJK_ASCII_ADJACENT_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff][A-Za-z]|[A-Za-z][\u3400-\u4dbf\u4e00-\u9fff]"
)
_CJK_ASCII_SPACED_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff][ \t\u3000]+[A-Za-z0-9]|[A-Za-z0-9][ \t\u3000]+[\u3400-\u4dbf\u4e00-\u9fff]"
)
_REFERENCE_CITATION_RE = re.compile(r"\[(\d+(?:\s*[-,，]\s*\d+)*)\]")


def _active_rules(rules: RuleSet | None = None) -> RuleSet:
    if rules is not None and rules.config:
        return rules
    return default_rules()


def _cfg(rules: RuleSet | None, *path: str):
    current = _active_rules(rules).config
    for item in path:
        current = current[item]
    return current


def _float_cfg(rules: RuleSet | None, *path: str) -> float:
    return float(_cfg(rules, *path))


def _int_cfg(rules: RuleSet | None, *path: str) -> int:
    return int(_cfg(rules, *path))


def _alignment_allowed(expected) -> set[str]:
    if isinstance(expected, str):
        return {expected}
    return {str(item) for item in expected}


def _numbering_pattern(rules: RuleSet | None, key: str) -> re.Pattern[str]:
    return re.compile(str(_cfg(rules, "numbering", key)))


def _compact_text(text: str) -> str:
    return re.sub(r"[\s\u3000]+", "", text.strip())


def _structure_texts(rules: RuleSet | None, key: str) -> tuple[str, ...]:
    value = _cfg(rules, "structure", "headings", key)
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _structure_pattern(rules: RuleSet | None, key: str) -> re.Pattern[str]:
    return re.compile(str(_cfg(rules, "structure", "patterns", key)))


def _matches_configured_text(text: str, candidates: tuple[str, ...]) -> bool:
    stripped = text.strip()
    compact = _compact_text(stripped)
    return any(stripped == candidate or compact == _compact_text(candidate) for candidate in candidates)


def _is_configured_heading(text: str, rules: RuleSet | None, key: str) -> bool:
    return _matches_configured_text(text, _structure_texts(rules, key))


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
    if _compact_text(text) == "目录":
        return False
    if style.upper().startswith("TOC"):
        return True
    return bool("\t" in paragraph.text and re.search(r"\d+\s*$", text))


def _is_toc_heading(text: str, rules: RuleSet | None = None) -> bool:
    return _is_configured_heading(text, rules, "toc")


def _is_reference_heading(text: str, rules: RuleSet | None = None) -> bool:
    return _is_configured_heading(text, rules, "reference")


def _is_thanks_heading(text: str, rules: RuleSet | None = None) -> bool:
    return _is_configured_heading(text, rules, "thanks")


def _is_cn_abstract_heading(text: str, rules: RuleSet | None = None) -> bool:
    return _is_configured_heading(text, rules, "abstract_cn")


def _is_en_abstract_heading(text: str, rules: RuleSet | None = None) -> bool:
    return _is_configured_heading(text, rules, "abstract_en")


def _is_terminal_heading(text: str, rules: RuleSet | None = None) -> bool:
    return _matches_configured_text(text, _structure_texts(rules, "terminal"))


def _first_body_paragraph_index(document: DocumentInfo, rules: RuleSet | None = None) -> int:
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if _structure_pattern(rules, "body_start").match(text):
            return paragraph.index
    return 0


def _reference_heading_index(document: DocumentInfo, rules: RuleSet | None = None) -> int | None:
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if _is_toc_paragraph(paragraph):
            continue
        if _is_reference_heading(text, rules):
            return paragraph.index
    return None


def _thanks_heading_index(document: DocumentInfo, rules: RuleSet | None = None) -> int | None:
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if _is_toc_paragraph(paragraph):
            continue
        if _is_thanks_heading(text, rules):
            return paragraph.index
    return None


def _terminal_heading_index(document: DocumentInfo, rules: RuleSet | None = None, *, after_index: int = 0) -> int | None:
    for paragraph in document.paragraphs:
        if paragraph.index <= after_index:
            continue
        text = paragraph.text.strip()
        if _is_toc_paragraph(paragraph):
            continue
        if _is_terminal_heading(text, rules):
            return paragraph.index
    return None


def _in_body_range(paragraph: ParagraphInfo, document: DocumentInfo, rules: RuleSet | None = None) -> bool:
    first_body = _first_body_paragraph_index(document, rules)
    reference_start = _reference_heading_index(document, rules)
    terminal_start = _terminal_heading_index(document, rules, after_index=first_body)
    if paragraph.index < first_body:
        return False
    if reference_start is not None and paragraph.index >= reference_start:
        return False
    if terminal_start is not None and paragraph.index >= terminal_start:
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


def _is_heading_text(text: str, rules: RuleSet | None = None) -> bool:
    stripped = text.strip()
    return bool(
        _structure_pattern(rules, "heading_level_1").match(stripped)
        or _structure_pattern(rules, "heading_level_2").match(stripped)
        or _structure_pattern(rules, "heading_level_3").match(stripped)
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


def _heading_level(paragraph: ParagraphInfo, rules: RuleSet | None = None) -> int | None:
    text = paragraph.text.strip()
    if _structure_pattern(rules, "heading_level_1").match(text):
        return 1
    if _structure_pattern(rules, "heading_level_3").match(text):
        return 3
    if _structure_pattern(rules, "heading_level_2").match(text):
        return 2
    return _style_heading_level(paragraph)


def _is_heading_paragraph(paragraph: ParagraphInfo, rules: RuleSet | None = None) -> bool:
    return _heading_level(paragraph, rules) is not None


def _is_caption_text(text: str, rules: RuleSet | None = None) -> bool:
    return bool(_numbering_pattern(rules, "caption_prefix_pattern").match(text.strip()))


def _has_trailing_punctuation(text: str, rules: RuleSet | None = None) -> bool:
    stripped = text.strip()
    return bool(stripped) and stripped[-1] in str(_cfg(rules, "heading", "punctuation_suffix"))


def _looks_like_body_paragraph(paragraph: ParagraphInfo, rules: RuleSet | None = None) -> bool:
    text = paragraph.text.strip()
    if not text:
        return False
    if _is_toc_paragraph(paragraph):
        return False
    if _is_heading_paragraph(paragraph, rules):
        return False
    if _is_reference_heading(text, rules):
        return False
    if _keyword_line_parts(text, rules) is not None:
        return False
    if _REFERENCE_ENTRY_RE.match(text):
        return False
    if _is_caption_text(text, rules):
        return False
    return True


def _line_spacing_check_start_index(document: DocumentInfo, rules: RuleSet | None = None) -> int:
    for paragraph in document.paragraphs:
        if _matches_configured_text(paragraph.text, _structure_texts(rules, "line_spacing_start")):
            return paragraph.index
    return _first_body_paragraph_index(document, rules)


def _looks_like_line_spacing_target(
    paragraph: ParagraphInfo, document: DocumentInfo, rules: RuleSet | None = None
) -> bool:
    text = paragraph.text.strip()
    if not text:
        return False
    if paragraph.index < _line_spacing_check_start_index(document, rules):
        return False
    if _is_toc_paragraph(paragraph):
        return False
    if _matches_configured_text(text, _structure_texts(rules, "line_spacing_excluded")):
        return False
    if _is_heading_paragraph(paragraph, rules):
        return False
    if _is_caption_text(text, rules):
        return False
    return True


def _looks_like_table_line_spacing_target(paragraph: ParagraphInfo, rules: RuleSet | None = None) -> bool:
    text = paragraph.text.strip()
    if not text:
        return False
    if _is_heading_paragraph(paragraph, rules):
        return False
    if _is_caption_text(text, rules):
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
        return "宋体" in font or normalized in {"simsun", "simsun-extb", "nsimsun"}
    if expected == "黑体":
        return "黑体" in font or normalized in {"simhei"}
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
    rules: RuleSet | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    font_size_tolerance = _float_cfg(rules, "tolerances", "font_size_pt")
    for run in _visible_runs(paragraph):
        if expected_size_pt is not None and run.size_pt is not None:
            if abs(run.size_pt - expected_size_pt) > font_size_tolerance:
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


def _check_heading_script_fonts(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        level = _heading_level(paragraph, rules)
        if not text or level is None:
            continue
        level_config = _cfg(rules, "heading", "levels", str(level))
        expected_east_asia = str(level_config["east_asia"])
        expected_ascii = str(level_config["ascii"])
        expected_bold = level_config.get("bold")
        for run in _visible_runs(paragraph):
            if _has_cjk(run.text) and run.font_east_asia is not None:
                if not _font_matches(run.font_east_asia, expected_east_asia):
                    issues.append(
                        _issue(
                            "HEADING_SCRIPT_FONT",
                            Severity.WARNING,
                            "Heading Chinese text should match the configured font.",
                            location=_paragraph_location(paragraph),
                            expected=f"中文={expected_east_asia}",
                            actual=_run_font_actual(run),
                            evidence=text,
                        )
                    )
                    break
            if _has_ascii_word(run.text) and run.font_ascii is not None:
                if not _font_matches(run.font_ascii, expected_ascii):
                    issues.append(
                        _issue(
                            "HEADING_SCRIPT_FONT",
                            Severity.WARNING,
                            "Heading numbers and English text should match the configured font.",
                            location=_paragraph_location(paragraph),
                            expected=f"数字/英文={expected_ascii}",
                            actual=_run_font_actual(run),
                            evidence=text,
                        )
                    )
                    break
            if expected_bold is True and run.bold is not True:
                issues.append(
                    _issue(
                        "HEADING_SCRIPT_FONT",
                        Severity.WARNING,
                        "Chapter heading text should be bold like the empty template.",
                        location=_paragraph_location(paragraph),
                        expected="bold",
                        actual="not bold" if run.bold is False else "not explicit",
                        evidence=text,
                    )
                )
                break
            if expected_bold is False and run.bold is True:
                issues.append(
                    _issue(
                        "HEADING_SCRIPT_FONT",
                        Severity.WARNING,
                        "Section heading text should not be bold in the empty template.",
                        location=_paragraph_location(paragraph),
                        expected="not bold",
                        actual="bold",
                        evidence=text,
                    )
                )
                break
            if run.italic is True:
                issues.append(
                    _issue(
                        "HEADING_SCRIPT_FONT",
                        Severity.WARNING,
                        "Heading text should not be italic in the empty template.",
                        location=_paragraph_location(paragraph),
                        expected="not italic",
                        actual="italic",
                        evidence=text,
                    )
                )
                break
    return issues


def _loose_keyword_label_pattern(label: str) -> str:
    parts = re.split(r"([ \t\u3000]+)", label)
    return "".join(r"[ \t\u3000]+" if part.strip() == "" else re.escape(part) for part in parts)


def _keyword_line_parts(text: str, rules: RuleSet | None = None) -> dict[str, str] | None:
    labels = (
        str(_cfg(rules, "keywords", "cn_label")),
        str(_cfg(rules, "keywords", "en_label")),
    )
    for expected_label in labels:
        pattern = re.compile(
            rf"^(?P<label>{_loose_keyword_label_pattern(expected_label)})"
            r"(?P<space_before>[ \t\u3000]*)(?P<delimiter>[：:])"
            r"(?P<space_after>[ \t\u3000]*)(?P<body>.+)$",
            flags=re.IGNORECASE,
        )
        match = pattern.match(text)
        if match:
            return {
                "expected_label": expected_label,
                "label": match.group("label"),
                "space_before": match.group("space_before"),
                "delimiter": match.group("delimiter"),
                "space_after": match.group("space_after"),
                "body": match.group("body"),
            }
    return None


def _split_keywords(keyword_text: str, rules: RuleSet | None = None) -> tuple[list[str], bool, bool]:
    expected_separator = str(_cfg(rules, "keywords", "separator"))
    alternate_separators = {"；", ";"}
    has_ascii_separator = ";" in keyword_text and expected_separator != ";"
    split_pattern = re.escape(expected_separator)
    if expected_separator in alternate_separators:
        split_pattern = r"[；;]"
    items = [part.strip() for part in re.split(split_pattern, keyword_text) if part.strip()]
    trailing_separator = keyword_text.rstrip().endswith(expected_separator)
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
            if abs(actual_value - expected_value) <= _float_cfg(rules, "tolerances", "page_cm"):
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
    first_body = _first_body_paragraph_index(document, rules)
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
        header_positions = set(body_section.header_border_positions)
        if "bottom" not in header_positions:
            issues.append(
                _issue(
                    "HEADER_LINE_POSITION",
                    Severity.WARNING,
                    "Body page header should use a bottom paragraph border line.",
                    location=f"section {body_section.index}",
                    expected="bottom border in header paragraph",
                    actual=", ".join(body_section.header_border_positions) or "not detected",
                )
            )
        elif any(position != "bottom" for position in header_positions):
            issues.append(
                _issue(
                    "HEADER_LINE_POSITION",
                    Severity.WARNING,
                    "Body page header line position does not match the empty template.",
                    location=f"section {body_section.index}",
                    expected="bottom border only",
                    actual=", ".join(body_section.header_border_positions),
                )
            )
        expected_header_line_size = _int_cfg(rules, "header", "line_size_eighths")
        if body_section.header_bottom_border_sizes and any(
            size != expected_header_line_size for size in body_section.header_bottom_border_sizes
        ):
            issues.append(
                _issue(
                    "HEADER_LINE_WIDTH",
                    Severity.WARNING,
                    "Body page header line width does not match the empty template.",
                    location=f"section {body_section.index}",
                    expected=f"{expected_header_line_size} eighths of a point ({expected_header_line_size / 8:g} pt)",
                    actual=", ".join(_format_border_size(size) for size in body_section.header_bottom_border_sizes),
                )
            )
        expected_header_line_space = _int_cfg(rules, "header", "line_space")
        if body_section.header_bottom_border_spaces and any(
            space != expected_header_line_space for space in body_section.header_bottom_border_spaces
        ):
            issues.append(
                _issue(
                    "HEADER_LINE_POSITION",
                    Severity.WARNING,
                    "Body page header line spacing from text does not match the empty template.",
                    location=f"section {body_section.index}",
                    expected=f"space={expected_header_line_space}",
                    actual=", ".join(f"space={space}" for space in body_section.header_bottom_border_spaces),
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

def _check_headings(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        level = _heading_level(paragraph, rules)
        if not text or level is None:
            continue
        level_config = _cfg(rules, "heading", "levels", str(level))
        if _has_trailing_punctuation(text, rules):
            issues.append(
                _issue(
                    "HEADING_PUNCTUATION",
                    Severity.WARNING,
                    "Heading text should not end with punctuation.",
                    location=_paragraph_location(paragraph),
                    evidence=text,
                )
            )
        issues.extend(_check_heading_spacing(paragraph, level=level, rules=rules))
        if level == 1:
            expected_alignment = str(level_config["alignment"])
            if paragraph.alignment is not None and paragraph.alignment != expected_alignment:
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "Chapter heading alignment should match the configured format.",
                        location=_paragraph_location(paragraph),
                        expected=expected_alignment,
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="HEADING_FORMAT",
                    expected_size_pt=float(level_config["size_pt"]),
                    expected_east_asia=str(level_config["east_asia"]),
                    expected_ascii=str(level_config["ascii"]),
                    rules=rules,
                )
            )
        elif level == 3:
            expected_alignment = _alignment_allowed(level_config["alignment"])
            if paragraph.alignment is not None and paragraph.alignment not in expected_alignment:
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "Third-level heading alignment should match the configured format.",
                        location=_paragraph_location(paragraph),
                        expected="/".join(sorted(expected_alignment)),
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            if (
                paragraph.first_line_indent_chars is not None
                and abs(paragraph.first_line_indent_chars - float(level_config["first_line_indent_chars"]))
                > _float_cfg(rules, "tolerances", "indent_chars")
            ):
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "Third-level heading should not use first-line indent.",
                        location=_paragraph_location(paragraph),
                        expected="no first-line indent",
                        actual=f"{paragraph.first_line_indent_chars:g} characters",
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="HEADING_FORMAT",
                    expected_size_pt=float(level_config["size_pt"]),
                    expected_east_asia=str(level_config["east_asia"]),
                    expected_ascii=str(level_config["ascii"]),
                    rules=rules,
                )
            )
        elif level == 2:
            expected_alignment = _alignment_allowed(level_config["alignment"])
            if paragraph.alignment is not None and paragraph.alignment not in expected_alignment:
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "Second-level heading alignment should match the configured format.",
                        location=_paragraph_location(paragraph),
                        expected="/".join(sorted(expected_alignment)),
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            if (
                paragraph.first_line_indent_chars is not None
                and abs(paragraph.first_line_indent_chars - float(level_config["first_line_indent_chars"]))
                > _float_cfg(rules, "tolerances", "indent_chars")
            ):
                issues.append(
                    _issue(
                        "HEADING_FORMAT",
                        Severity.WARNING,
                        "Second-level heading should not use first-line indent.",
                        location=_paragraph_location(paragraph),
                        expected="no first-line indent",
                        actual=f"{paragraph.first_line_indent_chars:g} characters",
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="HEADING_FORMAT",
                    expected_size_pt=float(level_config["size_pt"]),
                    expected_east_asia=str(level_config["east_asia"]),
                    expected_ascii=str(level_config["ascii"]),
                    rules=rules,
                )
            )
    return issues


def _check_heading_spacing(
    paragraph: ParagraphInfo, *, level: int | None = None, rules: RuleSet | None = None
) -> list[Issue]:
    issues: list[Issue] = []
    text = paragraph.text.strip()
    expected_space_lines = _float_cfg(rules, "heading", "space_lines")
    expected_line_spacing_pt = _float_cfg(rules, "heading", "line_spacing_pt")
    if not _space_lines_match(paragraph.space_before_lines, expected_space_lines, rules):
        issues.append(
            _issue(
                "HEADING_SPACING",
                Severity.WARNING,
                "Heading paragraph space before should match the empty template.",
                location=_paragraph_location(paragraph),
                expected=f"{expected_space_lines:g} lines",
                actual=_format_space_lines(paragraph.space_before_lines, paragraph.space_before_pt),
                evidence=text,
            )
        )
    if not _space_lines_match(paragraph.space_after_lines, expected_space_lines, rules):
        issues.append(
            _issue(
                "HEADING_SPACING",
                Severity.WARNING,
                "Heading paragraph space after should match the empty template.",
                location=_paragraph_location(paragraph),
                expected=f"{expected_space_lines:g} lines",
                actual=_format_space_lines(paragraph.space_after_lines, paragraph.space_after_pt),
                evidence=text,
            )
        )
    requires_fixed_line_spacing = level in {2, 3}
    if level == 1 and (paragraph.line_spacing_pt is not None or paragraph.line_spacing_multiple is not None):
        if paragraph.line_spacing_multiple is not None:
            actual = f"{paragraph.line_spacing_multiple:g}x ({paragraph.line_spacing_rule or 'auto'})"
        else:
            actual = f"{paragraph.line_spacing_pt:.1f} pt ({paragraph.line_spacing_rule or 'not explicit'})"
        issues.append(
            _issue(
                "HEADING_SPACING",
                Severity.WARNING,
                "Chapter heading line spacing should match the empty template.",
                location=_paragraph_location(paragraph),
                expected="empty-template chapter line spacing with no explicit override",
                actual=actual,
                evidence=text,
            )
        )
    elif requires_fixed_line_spacing and paragraph.line_spacing_pt is None and paragraph.line_spacing_multiple is None:
        issues.append(
            _issue(
                "HEADING_SPACING",
                Severity.WARNING,
                "Section heading line spacing should match the empty template.",
                location=_paragraph_location(paragraph),
                expected=f"fixed {expected_line_spacing_pt:g} pt",
                actual="not explicit",
                evidence=text,
            )
        )
    elif paragraph.line_spacing_multiple is not None:
        issues.append(
            _issue(
                "HEADING_SPACING",
                Severity.WARNING,
                "Heading line spacing should match the empty template.",
                location=_paragraph_location(paragraph),
                expected=f"fixed {expected_line_spacing_pt:g} pt",
                actual=f"{paragraph.line_spacing_multiple:g}x ({paragraph.line_spacing_rule or 'auto'})",
                evidence=text,
            )
        )
    elif paragraph.line_spacing_pt is not None:
        if paragraph.line_spacing_rule not in {None, "exact", "fixed"}:
            issues.append(
                _issue(
                    "HEADING_SPACING",
                    Severity.WARNING,
                    "Heading line spacing should match the empty template.",
                    location=_paragraph_location(paragraph),
                    expected=f"fixed {expected_line_spacing_pt:g} pt",
                    actual=f"{paragraph.line_spacing_pt:.1f} pt ({paragraph.line_spacing_rule})",
                    evidence=text,
                )
            )
        elif abs(paragraph.line_spacing_pt - expected_line_spacing_pt) > _float_cfg(
            rules, "tolerances", "line_spacing_pt"
        ):
            issues.append(
                _issue(
                    "HEADING_SPACING",
                    Severity.WARNING,
                    "Heading line spacing should match the empty template.",
                    location=_paragraph_location(paragraph),
                    expected=f"{expected_line_spacing_pt:g} pt",
                    actual=f"{paragraph.line_spacing_pt:.1f} pt",
                    evidence=text,
                )
            )
    return issues


def _check_numbering(paragraph: ParagraphInfo, rules: RuleSet | None = None) -> list[Issue]:
    if _is_toc_paragraph(paragraph):
        return []
    text = paragraph.text.strip()
    if not text:
        return []

    issues: list[Issue] = []
    if _numbering_pattern(rules, "figure_dot_pattern").search(text):
        issues.append(
            _issue(
                "FIGURE_NUMBERING",
                Severity.WARNING,
                "Figure numbering should use a hyphen rather than a dot.",
                location=_paragraph_location(paragraph),
                evidence=text,
            )
        )
    if _numbering_pattern(rules, "table_dot_pattern").search(text):
        issues.append(
            _issue(
                "TABLE_NUMBERING",
                Severity.WARNING,
                "Table numbering should use a hyphen rather than a dot.",
                location=_paragraph_location(paragraph),
                evidence=text,
            )
        )
    if _numbering_pattern(rules, "equation_dot_pattern").search(text):
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


def _check_keywords(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    expected_delimiter = str(_cfg(rules, "keywords", "label_delimiter"))
    allow_space_before_delimiter = bool(_cfg(rules, "keywords", "allow_space_before_delimiter"))
    allow_space_after_delimiter = bool(_cfg(rules, "keywords", "allow_space_after_delimiter"))
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        match = _keyword_line_parts(text, rules)
        if match is None:
            continue

        label = match["label"]
        expected_label = match["expected_label"]
        keyword_text = match["body"].strip()
        items, has_ascii_separator, has_trailing_separator = _split_keywords(keyword_text, rules)

        if (
            label != expected_label
            or match["delimiter"] != expected_delimiter
            or (match["space_before"] and not allow_space_before_delimiter)
            or (match["space_after"] and not allow_space_after_delimiter)
        ):
            issues.append(
                _issue(
                    "KEYWORD_LABEL_FORMAT",
                    Severity.WARNING,
                    f"{expected_label} line label and delimiter should match the configured format.",
                    location=_paragraph_location(paragraph),
                    expected=f"{expected_label}{expected_delimiter}",
                    actual=text[: len(text) - len(match["body"])],
                    evidence=text,
                )
            )
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
        if has_trailing_separator and bool(_cfg(rules, "keywords", "forbid_trailing_separator")):
            issues.append(
                _issue(
                    "KEYWORD_TERMINATOR",
                    Severity.WARNING,
                    f"{label} line should not end with a semicolon.",
                    location=_paragraph_location(paragraph),
                    evidence=text,
                )
            )
        min_count = _int_cfg(rules, "keywords", "min_count")
        max_count = _int_cfg(rules, "keywords", "max_count")
        if not min_count <= len(items) <= max_count:
            issues.append(
                _issue(
                    "KEYWORD_COUNT",
                    Severity.WARNING,
                    f"{label} line should contain 3 to 5 keywords.",
                    location=_paragraph_location(paragraph),
                    expected=f"{min_count}-{max_count} keywords",
                    actual=f"{len(items)} keywords",
                    evidence=text,
                )
            )
    return issues


def _check_structure_presence(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    texts = [paragraph.text.strip() for paragraph in document.paragraphs if not _is_toc_paragraph(paragraph)]
    required = _cfg(rules, "structure", "required")
    for code, (needle, message) in required.items():
        if code == "STRUCTURE_TOC":
            found = any(_is_toc_heading(text, rules) for text in texts)
        elif code == "STRUCTURE_ABSTRACT_EN":
            found = any(_is_en_abstract_heading(text, rules) for text in texts)
        elif code == "STRUCTURE_ABSTRACT_CN":
            found = any(_is_cn_abstract_heading(text, rules) for text in texts)
        elif code == "STRUCTURE_BODY_START":
            found = any(_structure_pattern(rules, "body_start").match(text) for text in texts)
        elif code == "STRUCTURE_REFERENCES":
            found = any(_is_reference_heading(text, rules) for text in texts)
        elif code == "STRUCTURE_THANKS":
            found = any(_is_thanks_heading(text, rules) for text in texts)
        else:
            found = any(_matches_configured_text(text, (str(needle),)) for text in texts)
        if not found:
            issues.append(_issue(code, Severity.WARNING, message, expected=needle))
    return issues


def _major_heading_key(text: str, rules: RuleSet | None = None) -> str | None:
    compact = re.sub(r"[\s\u3000]+", "", text.strip())
    return compact if compact in _cfg(rules, "structure", "major_heading_expected") else None


def _check_major_heading_spacing(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[str] = set()
    for paragraph in document.paragraphs:
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        key = _major_heading_key(text, rules)
        if key is None or key in seen:
            continue
        seen.add(key)
        expected = _cfg(rules, "structure", "major_heading_expected")[key]
        if text != expected:
            issues.append(
                _issue(
                    "MAJOR_HEADING_SPACING",
                    Severity.WARNING,
                    "Major heading text spacing does not match the empty template.",
                    location=_paragraph_location(paragraph),
                    expected=expected,
                    actual=text,
                    evidence=text,
                )
            )
    return issues


def _check_abstract_format(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    expected_alignment = str(_cfg(rules, "abstract", "alignment"))
    expected_size_pt = _float_cfg(rules, "abstract", "heading_size_pt")
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        normalized = text.replace(" ", "")
        if _is_cn_abstract_heading(text, rules):
            if paragraph.alignment is not None and paragraph.alignment != expected_alignment:
                issues.append(
                    _issue(
                        "ABSTRACT_FORMAT",
                        Severity.WARNING,
                        "Chinese abstract heading alignment should match the configured format.",
                        location=_paragraph_location(paragraph),
                        expected=expected_alignment,
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="ABSTRACT_FORMAT",
                    expected_size_pt=expected_size_pt,
                    expected_east_asia=str(_cfg(rules, "abstract", "cn_font")),
                    rules=rules,
                )
            )
        elif _is_en_abstract_heading(text, rules):
            if paragraph.alignment is not None and paragraph.alignment != expected_alignment:
                issues.append(
                    _issue(
                        "ABSTRACT_FORMAT",
                        Severity.WARNING,
                        "English abstract heading alignment should match the configured format.",
                        location=_paragraph_location(paragraph),
                        expected=expected_alignment,
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="ABSTRACT_FORMAT",
                    expected_size_pt=expected_size_pt,
                    expected_ascii=str(_cfg(rules, "abstract", "en_font")),
                    require_bold=bool(_cfg(rules, "abstract", "en_bold")),
                    rules=rules,
                )
            )
    return issues


def _check_references(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    reference_started = False

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        if _is_toc_paragraph(paragraph):
            continue

        if not reference_started:
            if _is_reference_heading(text, rules):
                reference_started = True
            continue

        if _is_heading_text(text, rules) or _is_terminal_heading(text, rules):
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


def _check_toc_fields(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    has_toc_heading = any(_is_toc_heading(paragraph.text, rules) for paragraph in document.paragraphs)
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


def _reference_entry_numbers(document: DocumentInfo, rules: RuleSet | None = None) -> set[int]:
    numbers: set[int] = set()
    reference_started = False
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text or _is_toc_paragraph(paragraph):
            continue
        normalized = text.replace(" ", "")
        if not reference_started:
            if _is_reference_heading(text, rules):
                reference_started = True
            continue
        if _is_heading_text(text, rules) or _is_terminal_heading(text, rules):
            break
        match = _REFERENCE_ENTRY_RE.match(text)
        if match:
            numbers.add(int(match.group(1)))
    return numbers


def _citation_numbers(raw: str) -> set[int]:
    parts = re.split(r"[,，]", raw)
    numbers: set[int] = set()
    for part in parts:
        stripped = part.strip()
        if not stripped:
            continue
        if "-" in stripped:
            start_text, end_text = [item.strip() for item in stripped.split("-", 1)]
            if start_text.isdigit() and end_text.isdigit():
                start = int(start_text)
                end = int(end_text)
                if start <= end:
                    numbers.update(range(start, end + 1))
                else:
                    numbers.update({start, end})
            continue
        if stripped.isdigit():
            numbers.add(int(stripped))
    return numbers


def _run_spans(paragraph: ParagraphInfo) -> list[tuple[int, int, object]]:
    spans = []
    offset = 0
    for run in paragraph.runs:
        start = offset
        end = start + len(run.text)
        spans.append((start, end, run))
        offset = end
    return spans


def _runs_overlapping(paragraph: ParagraphInfo, start: int, end: int):
    for run_start, run_end, run in _run_spans(paragraph):
        if run_end <= start or run_start >= end:
            continue
        yield run


def _citation_is_superscript(paragraph: ParagraphInfo, start: int, end: int) -> bool:
    runs = list(_runs_overlapping(paragraph, start, end))
    return bool(runs) and all(run.vertical_align == "superscript" for run in runs)


def _has_reference_field(paragraph: ParagraphInfo) -> bool:
    return any(re.search(r"\b(?:REF|NOTEREF)\b", instruction.upper()) for instruction in paragraph.field_instructions)


def _check_reference_citations(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    reference_numbers = _reference_entry_numbers(document, rules)
    cited_numbers: set[int] = set()
    reference_start = _reference_heading_index(document, rules)
    expected_separator = str(_cfg(rules, "reference", "citation_separator"))
    for paragraph in document.paragraphs:
        if not _in_body_range(paragraph, document, rules):
            continue
        if reference_start is not None and paragraph.index >= reference_start:
            continue
        if _is_toc_paragraph(paragraph):
            continue
        raw_text = paragraph.text
        text = raw_text.strip()
        if not text or _is_heading_paragraph(paragraph, rules) or _is_caption_text(text, rules):
            continue
        for match in _REFERENCE_CITATION_RE.finditer(raw_text):
            citation_text = match.group(0)
            citation_inner = match.group(1)
            numbers = _citation_numbers(match.group(1))
            cited_numbers.update(numbers)
            if "," in citation_inner and expected_separator != ",":
                issues.append(
                    _issue(
                        "REFERENCE_CITATION_SEPARATOR",
                        Severity.WARNING,
                        "Multiple reference numbers in one superscript citation should use the configured separator.",
                        location=_paragraph_location(paragraph),
                        expected=f"Chinese comma separator, e.g. [1{expected_separator}2]",
                        actual=citation_text,
                        evidence=citation_text,
                    )
                )
            if not _citation_is_superscript(paragraph, match.start(), match.end()):
                issues.append(
                    _issue(
                        "REFERENCE_CITATION_FORMAT",
                        Severity.WARNING,
                        "In-text reference citation should be superscript.",
                        location=_paragraph_location(paragraph),
                        expected="superscript citation like [1]",
                        actual="not superscript or not explicit",
                        evidence=citation_text,
                    )
                )
            if not _has_reference_field(paragraph):
                issues.append(
                    _issue(
                        "REFERENCE_CITATION_FIELD",
                        Severity.WARNING,
                        "In-text reference citation does not appear to use a Word cross-reference field.",
                        location=_paragraph_location(paragraph),
                        expected="Word REF/NOTEREF field for the citation",
                        actual="field code not detected",
                        evidence=citation_text,
                    )
                )
            missing_targets = sorted(number for number in numbers if number not in reference_numbers)
            if missing_targets and reference_numbers:
                issues.append(
                    _issue(
                        "REFERENCE_CITATION_TARGET",
                        Severity.WARNING,
                        "In-text reference citation points to a number not found in the reference list.",
                        location=_paragraph_location(paragraph),
                        expected="citation number exists in references",
                        actual=", ".join(str(number) for number in missing_targets),
                        evidence=citation_text,
                    )
                )
    for number in sorted(reference_numbers - cited_numbers):
        issues.append(
            _issue(
                "REFERENCE_CITATION_TARGET",
                Severity.INFO,
                "Reference entry is not cited in the body text.",
                location="references",
                expected=f"[{number}] cited in body text",
                actual="not cited",
            )
        )
    return issues


def _check_table_borders(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    first_body = _first_body_paragraph_index(document, rules)
    reference_start = _reference_heading_index(document, rules)
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
        issues.extend(_check_table_template_layout(table, rules))
    return issues


def _check_table_template_layout(table: TableInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    expected_line_count = _int_cfg(rules, "table", "horizontal_line_count")
    expected_width_type = str(_cfg(rules, "table", "width_type"))
    expected_width_value = _int_cfg(rules, "table", "width_value")
    expected_alignment = str(_cfg(rules, "table", "alignment"))
    expected_cell_vertical_alignment = str(_cfg(rules, "table", "cell_vertical_alignment"))
    expected_outer_border_size = _int_cfg(rules, "table", "outer_border_size_eighths")
    expected_header_border_size = _int_cfg(rules, "table", "header_bottom_border_size_eighths")
    if table.horizontal_line_count is not None and table.horizontal_line_count != expected_line_count:
        issues.append(
            _issue(
                "TABLE_LINE_COUNT",
                Severity.WARNING,
                "Table should have exactly three visible horizontal lines.",
                location=f"table {table.index}",
                expected=f"{expected_line_count} horizontal lines",
                actual=f"{table.horizontal_line_count} horizontal lines",
                evidence=", ".join(table.horizontal_line_positions),
            )
        )
    if table.width_type != expected_width_type or table.width_value != expected_width_value:
        issues.append(
            _issue(
                "TABLE_WIDTH",
                Severity.WARNING,
                "Table width does not match the empty template.",
                location=f"table {table.index}",
                expected=f"100% page text width (w:tblW type={expected_width_type} w={expected_width_value})",
                actual=f"type={table.width_type or 'not explicit'} w={table.width_value or 'not explicit'}",
            )
        )
    for row_index, (width_types, width_values) in enumerate(zip(table.cell_width_types, table.cell_width_values), start=1):
        if any(width_type != expected_width_type for width_type in width_types):
            issues.append(
                _issue(
                    "TABLE_CELL_WIDTH",
                    Severity.WARNING,
                    "Table cell widths should use percentage widths like the empty template.",
                    location=f"table {table.index} row {row_index}",
                    expected=f"all cells type={expected_width_type}",
                    actual=", ".join(width_type or "not explicit" for width_type in width_types),
                )
            )
            continue
        explicit_widths = [value for value in width_values if value is not None]
        if len(explicit_widths) != len(width_values) or sum(explicit_widths) != expected_width_value:
            issues.append(
                _issue(
                    "TABLE_CELL_WIDTH",
                    Severity.WARNING,
                    "Table cell width sum should match the empty template table width.",
                    location=f"table {table.index} row {row_index}",
                    expected=f"cell widths sum={expected_width_value}",
                    actual=", ".join(str(value) if value is not None else "not explicit" for value in width_values),
                )
            )
    if table.alignment != expected_alignment:
        issues.append(
            _issue(
                "TABLE_ALIGNMENT",
                Severity.WARNING,
                "Table alignment does not match the empty template.",
                location=f"table {table.index}",
                expected=expected_alignment,
                actual=table.alignment or "not explicit",
            )
        )
    bad_vertical_alignments = [
        alignment or "not explicit"
        for alignment in table.cell_vertical_alignments
        if alignment != expected_cell_vertical_alignment
    ]
    if bad_vertical_alignments:
        issues.append(
            _issue(
                "TABLE_CELL_ALIGNMENT",
                Severity.WARNING,
                "Table cell vertical alignment should match the configured format.",
                location=f"table {table.index}",
                expected=f"vertical alignment={expected_cell_vertical_alignment}",
                actual=", ".join(bad_vertical_alignments[:8]),
            )
        )

    border_sizes = _table_border_size_map(table)
    for border_name in ("top", "bottom"):
        actual_size = border_sizes.get(border_name)
        if actual_size != expected_outer_border_size:
            issues.append(
                _issue(
                    "TABLE_BORDER_WIDTH",
                    Severity.WARNING,
                    "Table outer border width does not match the empty template.",
                    location=f"table {table.index}",
                    expected=f"{expected_outer_border_size} eighths of a point ({expected_outer_border_size / 8:g} pt)",
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
        or any(size != expected_header_border_size for size in header_sizes)
    ):
        issues.append(
            _issue(
                "TABLE_HEADER_BORDER",
                Severity.WARNING,
                "Table header bottom border width does not match the empty template.",
                location=f"table {table.index}",
                expected=f"{expected_header_border_size} eighths of a point ({expected_header_border_size / 8:g} pt) on each header cell",
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


def _space_lines_match(actual: float | None, expected: float, rules: RuleSet | None = None) -> bool:
    return actual is not None and abs(actual - expected) <= _float_cfg(rules, "tolerances", "line_space_lines")


def _space_pt_match(actual: float | None, expected: float, rules: RuleSet | None = None) -> bool:
    if actual is None:
        actual = 0.0
    return abs(actual - expected) <= _float_cfg(rules, "tolerances", "line_spacing_pt")


def _format_space_lines(space_lines: float | None, space_pt: float | None) -> str:
    if space_lines is not None:
        return f"{space_lines:g} lines"
    if space_pt is not None:
        return f"{space_pt:g} pt"
    return "not explicit"


def _format_space_pt(space_pt: float | None) -> str:
    if space_pt is None:
        return "not explicit (treated as 0 pt)"
    return f"{space_pt:g} pt"


def _format_border_size(size: int) -> str:
    return f"{size} eighths of a point ({size / 8:g} pt)"


def _caption_paragraphs(document: DocumentInfo, rules: RuleSet | None = None) -> list[tuple[ParagraphInfo, str]]:
    result: list[tuple[ParagraphInfo, str]] = []
    for paragraph in document.paragraphs:
        if _is_caption_text(paragraph.text, rules):
            result.append((paragraph, _paragraph_location(paragraph)))
    for table in document.tables:
        for paragraph in table.paragraphs:
            if _is_caption_text(paragraph.text, rules):
                result.append((paragraph, f"table {table.index} paragraph {paragraph.index}"))
    return result


def _check_captions(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    expected_alignment = str(_cfg(rules, "caption", "alignment"))
    expected_indent = _float_cfg(rules, "caption", "first_line_indent_chars")
    expected_size = _float_cfg(rules, "caption", "size_pt")
    expected_east_asia = str(_cfg(rules, "caption", "east_asia"))
    expected_ascii = str(_cfg(rules, "caption", "ascii"))
    expected_line_spacing = _float_cfg(rules, "caption", "line_spacing_pt")
    expected_separator = str(_cfg(rules, "caption", "separator"))
    for paragraph, location in _caption_paragraphs(document, rules):
        text = paragraph.text.strip()
        match = _numbering_pattern(rules, "caption_pattern").match(text)
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
        elif match.group(3) != expected_separator:
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

        if paragraph.alignment is not None and paragraph.alignment != expected_alignment:
            issues.append(
                _issue(
                    "CAPTION_FORMAT",
                    Severity.WARNING,
                    "Caption alignment should match the configured format.",
                    location=location,
                    expected=expected_alignment,
                    actual=paragraph.alignment,
                    evidence=text,
                )
            )
        if paragraph.first_line_indent_chars is not None and abs(
            paragraph.first_line_indent_chars - expected_indent
        ) > _float_cfg(rules, "tolerances", "indent_chars"):
            issues.append(
                _issue(
                    "CAPTION_FORMAT",
                    Severity.WARNING,
                    "Caption first-line indent should match the configured format.",
                    location=location,
                    expected="no first-line indent",
                    actual=f"{paragraph.first_line_indent_chars:g} characters",
                    evidence=text,
                )
            )

        for run in _visible_runs(paragraph):
            if run.size_pt is not None and abs(run.size_pt - expected_size) > _float_cfg(
                rules, "tolerances", "font_size_pt"
            ):
                issues.append(
                    _issue(
                        "CAPTION_FORMAT",
                        Severity.WARNING,
                        "Caption font size should match the configured format.",
                        location=location,
                        expected=f"{expected_size:g} pt",
                        actual=f"{run.size_pt:g} pt",
                        evidence=text,
                    )
                )
                break
            if run.font_east_asia is not None and not _font_matches(run.font_east_asia, expected_east_asia):
                issues.append(
                    _issue(
                        "CAPTION_FORMAT",
                        Severity.WARNING,
                        "Caption East Asian font should match the configured format.",
                        location=location,
                        expected=expected_east_asia,
                        actual=_run_font_actual(run),
                        evidence=text,
                    )
                )
                break
            if _has_ascii_word(run.text) and run.font_ascii is not None:
                if not _font_matches(run.font_ascii, expected_ascii):
                    issues.append(
                        _issue(
                            "CAPTION_FORMAT",
                            Severity.WARNING,
                            "Caption ASCII text and numbers should match the configured format.",
                            location=location,
                            expected=expected_ascii,
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
                    "Caption line spacing should match the configured fixed-line format, not multiple/auto line spacing.",
                    location=location,
                    expected=f"fixed {expected_line_spacing:g} pt",
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
                        "Caption line spacing should match the configured fixed-line format.",
                        location=location,
                        expected=f"fixed {expected_line_spacing:g} pt",
                        actual=f"{paragraph.line_spacing_pt:.1f} pt ({paragraph.line_spacing_rule})",
                        evidence=text,
                    )
                )
            elif abs(paragraph.line_spacing_pt - expected_line_spacing) > _float_cfg(
                rules, "tolerances", "line_spacing_pt"
            ):
                issues.append(
                    _issue(
                        "CAPTION_LINE_SPACING",
                        Severity.WARNING,
                        "Caption line spacing should match the configured fixed-line format.",
                        location=location,
                        expected=f"{expected_line_spacing:g} pt",
                        actual=f"{paragraph.line_spacing_pt:.1f} pt",
                        evidence=text,
                    )
                )
    return issues


def _check_caption_object_order(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    tables_by_block = [table for table in document.tables if table.block_index is not None]
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not _in_body_range(paragraph, document, rules):
            continue
        if _numbering_pattern(rules, "figure_caption_pattern").match(text):
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
        if _numbering_pattern(rules, "table_caption_pattern").match(text) and paragraph.block_index is not None:
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


def _check_continued_table_layout(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    tables_by_block = [table for table in document.tables if table.block_index is not None]
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not _numbering_pattern(rules, "continued_table_caption_pattern").match(text):
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


def _check_table_cell_typography(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    expected_cell_alignment = _optional_str_cfg(rules, "table", "cell_alignment")
    expected_cell_size = _optional_float_cfg(rules, "table", "cell_size_pt")
    expected_cell_ascii = _optional_str_cfg(rules, "table", "cell_ascii")
    expected_cell_east_asia = _optional_str_cfg(rules, "table", "cell_east_asia")
    try:
        first_body = _first_body_paragraph_index(document, rules)
    except KeyError:
        first_body = 0
    try:
        reference_start = _reference_heading_index(document, rules)
    except KeyError:
        reference_start = None
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
            try:
                is_caption = _is_caption_text(text, rules)
            except KeyError:
                is_caption = False
            if not text or is_caption:
                continue
            location = f"table {table.index} paragraph {paragraph.index}"
            if expected_cell_alignment is not None and paragraph.alignment != expected_cell_alignment:
                issues.append(
                    _issue(
                        "TABLE_CELL_ALIGNMENT",
                        Severity.WARNING,
                        "Table cell paragraph alignment should match the configured format.",
                        location=location,
                        expected=expected_cell_alignment,
                        actual=paragraph.alignment or "not explicit",
                        evidence=text,
                    )
                )
            issues.extend(_check_table_cell_spacing(paragraph, location, rules))
            for run in _visible_runs(paragraph):
                if expected_cell_size is not None and run.size_pt is not None and abs(run.size_pt - expected_cell_size) > _float_cfg(
                    rules, "tolerances", "font_size_pt"
                ):
                    issues.append(
                        _issue(
                            "TABLE_CELL_FORMAT",
                            Severity.WARNING,
                            "Table cell text size should match the configured format.",
                            location=location,
                            expected=f"{expected_cell_size:g} pt",
                            actual=f"{run.size_pt:g} pt",
                            evidence=text,
                        )
                    )
                    break
                if expected_cell_ascii is not None and _has_ascii_word(run.text) and run.font_ascii is not None:
                    if not _font_matches(run.font_ascii, expected_cell_ascii):
                        issues.append(
                            _issue(
                                "TABLE_CELL_FONT",
                                Severity.WARNING,
                                "Table cell English and numbers should match the configured font.",
                                location=location,
                                expected=expected_cell_ascii,
                                actual=_run_font_actual(run),
                                evidence=text,
                            )
                        )
                        break
                if expected_cell_east_asia is not None and _has_cjk(run.text) and run.font_east_asia is not None:
                    if not _font_matches(run.font_east_asia, expected_cell_east_asia):
                        issues.append(
                            _issue(
                                "TABLE_CELL_FONT",
                                Severity.WARNING,
                                "Table cell Chinese text should match the configured font.",
                                location=location,
                                expected=expected_cell_east_asia,
                                actual=_run_font_actual(run),
                                evidence=text,
                            )
                        )
                        break
    return issues


def _check_table_cell_spacing(
    paragraph: ParagraphInfo, location: str, rules: RuleSet | None = None
) -> list[Issue]:
    issues: list[Issue] = []
    text = paragraph.text.strip()
    expected_before = _optional_float_cfg(rules, "table", "cell_space_before_pt")
    expected_after = _optional_float_cfg(rules, "table", "cell_space_after_pt")
    expected_line_spacing = _optional_float_cfg(rules, "table", "cell_line_spacing_pt")
    if expected_before is not None and not _space_pt_match(paragraph.space_before_pt, expected_before, rules):
        issues.append(
            _issue(
                "TABLE_CELL_SPACING",
                Severity.WARNING,
                "Table cell paragraph space before should match the configured format.",
                location=location,
                expected=f"{expected_before:g} pt",
                actual=_format_space_pt(paragraph.space_before_pt),
                evidence=text,
            )
        )
    if expected_after is not None and not _space_pt_match(paragraph.space_after_pt, expected_after, rules):
        issues.append(
            _issue(
                "TABLE_CELL_SPACING",
                Severity.WARNING,
                "Table cell paragraph space after should match the configured format.",
                location=location,
                expected=f"{expected_after:g} pt",
                actual=_format_space_pt(paragraph.space_after_pt),
                evidence=text,
            )
        )
    if expected_line_spacing is not None:
        issues.extend(
            _line_spacing_issues_for_paragraph(
                paragraph,
                location,
                code="TABLE_CELL_SPACING",
                expected_line_spacing_pt=expected_line_spacing,
                rules=rules,
            )
        )
    return issues


def _check_page_numbering_static(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    if not document.sections:
        return issues
    first_body = _first_body_paragraph_index(document, rules)
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


def _check_reference_typography(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    reference_started = False
    heading_alignment = str(_cfg(rules, "reference", "heading_alignment"))
    list_alignment = _alignment_allowed(_cfg(rules, "reference", "list_alignment"))
    list_indent = _float_cfg(rules, "reference", "list_first_line_indent_chars")
    list_space_before = _float_cfg(rules, "reference", "list_space_before_pt")
    list_space_after = _float_cfg(rules, "reference", "list_space_after_pt")
    list_line_spacing = _float_cfg(rules, "reference", "list_line_spacing_pt")
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text or _is_toc_paragraph(paragraph):
            continue
        normalized = text.replace(" ", "")
        if not reference_started:
            if _is_reference_heading(text, rules):
                reference_started = True
                if paragraph.alignment is not None and paragraph.alignment != heading_alignment:
                    issues.append(
                        _issue(
                            "REFERENCE_HEADING_FORMAT",
                            Severity.WARNING,
                            "References heading alignment should match the configured format.",
                            location=_paragraph_location(paragraph),
                            expected=heading_alignment,
                            actual=paragraph.alignment,
                            evidence=text,
                        )
                    )
                issues.extend(
                    _check_explicit_run_format(
                        paragraph,
                        code="REFERENCE_HEADING_FORMAT",
                        expected_size_pt=_float_cfg(rules, "reference", "heading_size_pt"),
                        expected_east_asia=str(_cfg(rules, "reference", "heading_east_asia")),
                        rules=rules,
                    )
                )
            continue

        if _is_heading_text(text, rules) or _is_terminal_heading(text, rules):
            break
        if paragraph.alignment is not None and paragraph.alignment not in list_alignment:
            issues.append(
                _issue(
                    "REFERENCE_LIST_FORMAT",
                    Severity.WARNING,
                    "Reference list entry alignment should match the configured format.",
                    location=_paragraph_location(paragraph),
                    expected="/".join(sorted(list_alignment)),
                    actual=paragraph.alignment,
                    evidence=text,
                )
            )
        if paragraph.first_line_indent_chars is not None and abs(
            paragraph.first_line_indent_chars - list_indent
        ) > _float_cfg(rules, "tolerances", "indent_chars"):
            issues.append(
                _issue(
                    "REFERENCE_LIST_FORMAT",
                    Severity.WARNING,
                    "Reference list entry should not use first-line indent.",
                    location=_paragraph_location(paragraph),
                    expected="no first-line indent",
                    actual=f"{paragraph.first_line_indent_chars:g} characters",
                    evidence=text,
                )
            )
        if not _space_pt_match(paragraph.space_before_pt, list_space_before, rules):
            issues.append(
                _issue(
                    "REFERENCE_LIST_SPACING",
                    Severity.WARNING,
                    "Reference list paragraph space before should match the template.",
                    location=_paragraph_location(paragraph),
                    expected=f"{list_space_before:g} pt",
                    actual=_format_space_pt(paragraph.space_before_pt),
                    evidence=text,
                )
            )
        if not _space_pt_match(paragraph.space_after_pt, list_space_after, rules):
            issues.append(
                _issue(
                    "REFERENCE_LIST_SPACING",
                    Severity.WARNING,
                    "Reference list paragraph space after should match the template.",
                    location=_paragraph_location(paragraph),
                    expected=f"{list_space_after:g} pt",
                    actual=_format_space_pt(paragraph.space_after_pt),
                    evidence=text,
                )
            )
        if paragraph.line_spacing_multiple is not None or paragraph.line_spacing_pt is None:
            actual = (
                f"{paragraph.line_spacing_multiple:g}x ({paragraph.line_spacing_rule or 'auto'})"
                if paragraph.line_spacing_multiple is not None
                else "not explicit"
            )
            issues.append(
                _issue(
                    "REFERENCE_LIST_SPACING",
                    Severity.WARNING,
                    "Reference list line spacing should match the configured fixed-line format.",
                    location=_paragraph_location(paragraph),
                    expected=f"fixed {list_line_spacing:g} pt",
                    actual=actual,
                    evidence=text,
                )
            )
        else:
            issues.extend(
                _line_spacing_issues_for_paragraph(
                    paragraph,
                    _paragraph_location(paragraph),
                    code="REFERENCE_LIST_SPACING",
                    expected_line_spacing_pt=list_line_spacing,
                    rules=rules,
                )
            )
        issues.extend(
            _check_explicit_run_format(
                paragraph,
                code="REFERENCE_LIST_FORMAT",
                expected_size_pt=_float_cfg(rules, "reference", "list_size_pt"),
                expected_east_asia=str(_cfg(rules, "reference", "list_east_asia")),
                expected_ascii=str(_cfg(rules, "reference", "list_ascii")),
                rules=rules,
            )
        )
        for run in _visible_runs(paragraph):
            if run.bold is True:
                issues.append(
                    _issue(
                        "REFERENCE_LIST_FORMAT",
                        Severity.WARNING,
                        "Reference list text should not be bold.",
                        location=_paragraph_location(paragraph),
                        expected="not bold",
                        actual="bold",
                        evidence=text,
                    )
                )
                break
            if run.italic is True:
                issues.append(
                    _issue(
                        "REFERENCE_LIST_FORMAT",
                        Severity.WARNING,
                        "Reference list text should not be italic.",
                        location=_paragraph_location(paragraph),
                        expected="not italic",
                        actual="italic",
                        evidence=text,
                    )
                )
                break
    return issues


def _check_empty_paragraphs(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    run_start: ParagraphInfo | None = None
    run_length = 0
    first_body_index = _first_body_paragraph_index(document, rules)

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


def _config_path_exists(rules: RuleSet | None, *path: str) -> bool:
    current = _active_rules(rules).config
    for item in path:
        if not isinstance(current, dict) or item not in current:
            return False
        current = current[item]
    return True


def _optional_float_cfg(rules: RuleSet | None, *path: str) -> float | None:
    if not _config_path_exists(rules, *path):
        return None
    return _float_cfg(rules, *path)


def _optional_str_cfg(rules: RuleSet | None, *path: str) -> str | None:
    if not _config_path_exists(rules, *path):
        return None
    return str(_cfg(rules, *path))


def _safe_in_body_range(paragraph: ParagraphInfo, document: DocumentInfo, rules: RuleSet | None = None) -> bool:
    try:
        return _in_body_range(paragraph, document, rules)
    except KeyError:
        return True


def _safe_looks_like_body_paragraph(paragraph: ParagraphInfo, rules: RuleSet | None = None) -> bool:
    try:
        return _looks_like_body_paragraph(paragraph, rules)
    except KeyError:
        text = paragraph.text.strip()
        return bool(text) and not _is_toc_paragraph(paragraph) and not _REFERENCE_ENTRY_RE.match(text)


def _check_body_typography(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    expected_indent = _optional_float_cfg(rules, "body", "first_line_indent_chars")
    expected_space_before = _optional_float_cfg(rules, "body", "space_before_pt")
    expected_space_after = _optional_float_cfg(rules, "body", "space_after_pt")
    expected_size = _optional_float_cfg(rules, "body", "size_pt")
    expected_east_asia = _optional_str_cfg(rules, "body", "east_asia")
    expected_ascii = _optional_str_cfg(rules, "body", "ascii")
    for paragraph in document.paragraphs:
        if not _safe_in_body_range(paragraph, document, rules):
            continue
        if not _safe_looks_like_body_paragraph(paragraph, rules):
            continue
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        if expected_indent is not None and paragraph.first_line_indent_chars is None:
            issues.append(
                _issue(
                    "BODY_INDENT",
                    Severity.WARNING,
                    "Body paragraph first-line indent should match the configured format.",
                    location=_paragraph_location(paragraph),
                    expected=f"{expected_indent:g} characters",
                    actual="not explicit in paragraph/style metadata",
                    evidence=text,
                )
            )
        elif expected_indent is not None and abs(paragraph.first_line_indent_chars - expected_indent) > _float_cfg(rules, "tolerances", "indent_chars"):
            issues.append(
                _issue(
                    "BODY_INDENT",
                    Severity.WARNING,
                    "Body paragraph first-line indent should match the configured format.",
                    location=_paragraph_location(paragraph),
                    expected=f"{expected_indent:g} characters",
                    actual=f"{paragraph.first_line_indent_chars:g} characters",
                    evidence=text,
                )
            )
        if expected_space_before is not None and not _space_pt_match(paragraph.space_before_pt, expected_space_before, rules):
            issues.append(
                _issue(
                    "BODY_SPACING",
                    Severity.WARNING,
                    "Body paragraph space before should match the empty template.",
                    location=_paragraph_location(paragraph),
                    expected=f"{expected_space_before:g} pt",
                    actual=_format_space_pt(paragraph.space_before_pt),
                    evidence=text,
                )
            )
        if expected_space_after is not None and not _space_pt_match(paragraph.space_after_pt, expected_space_after, rules):
            issues.append(
                _issue(
                    "BODY_SPACING",
                    Severity.WARNING,
                    "Body paragraph space after should match the empty template.",
                    location=_paragraph_location(paragraph),
                    expected=f"{expected_space_after:g} pt",
                    actual=_format_space_pt(paragraph.space_after_pt),
                    evidence=text,
                )
            )
        if expected_size is not None or expected_east_asia is not None or expected_ascii is not None:
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="BODY_FONT",
                    expected_size_pt=expected_size,
                    expected_east_asia=expected_east_asia,
                    expected_ascii=expected_ascii,
                    rules=rules,
                )
            )
        for run in _visible_runs(paragraph):
            if run.bold is True:
                issues.append(
                    _issue(
                        "BODY_FONT",
                        Severity.WARNING,
                        "Body text should not be bold in the empty template.",
                        location=_paragraph_location(paragraph),
                        expected="not bold",
                        actual="bold",
                        evidence=text,
                    )
                )
                break
            if run.italic is True:
                issues.append(
                    _issue(
                        "BODY_FONT",
                        Severity.WARNING,
                        "Body text should not be italic in the empty template.",
                        location=_paragraph_location(paragraph),
                        expected="not italic",
                        actual="italic",
                        evidence=text,
                    )
                )
                break
    return issues


def _mixed_language_spacing_evidence(text: str) -> str:
    match = _CJK_ASCII_SPACED_RE.search(text)
    if not match:
        return text
    start = max(0, match.start() - 20)
    end = min(len(text), match.end() + 20)
    return text[start:end]


def _mixed_language_check_start_index(document: DocumentInfo, rules: RuleSet | None = None) -> int:
    for paragraph in document.paragraphs:
        if _is_cn_abstract_heading(paragraph.text, rules):
            return paragraph.index
    return _first_body_paragraph_index(document, rules)


def _check_mixed_language_spacing(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    reference_start = _reference_heading_index(document, rules)
    thanks_start = _thanks_heading_index(document, rules)
    stop_index = reference_start if reference_start is not None else thanks_start
    seen: set[int] = set()
    for paragraph in document.paragraphs:
        if paragraph.index in seen:
            continue
        seen.add(paragraph.index)
        if paragraph.index < _mixed_language_check_start_index(document, rules):
            continue
        if stop_index is not None and paragraph.index >= stop_index:
            continue
        if _is_toc_paragraph(paragraph):
            continue
        text = paragraph.text.strip()
        if not text or _is_en_abstract_heading(text, rules):
            continue
        if "签名" in text:
            continue
        if _keyword_line_parts(text, rules) is not None:
            continue
        if _is_heading_paragraph(paragraph, rules) or _is_caption_text(text, rules):
            continue
        if re.search(r"https?://|www\.|[A-Za-z]:[/\\]", text):
            continue
        if _CJK_ASCII_SPACED_RE.search(text):
            issues.append(
                _issue(
                    "MIXED_LANGUAGE_SPACING",
                    Severity.WARNING,
                    "Body text should not add spaces between Chinese text and adjacent English words or numbers.",
                    location=_paragraph_location(paragraph),
                    expected="中文English中文 / 中文123中文",
                    actual="space between Chinese and adjacent English/number text",
                    evidence=_mixed_language_spacing_evidence(text),
                )
            )
    return issues


def _check_thanks_format(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    thanks_index = _thanks_heading_index(document, rules)
    if thanks_index is None:
        return issues
    heading_alignment = str(_cfg(rules, "thanks", "heading_alignment"))
    body_indent = _float_cfg(rules, "thanks", "body_first_line_indent_chars")
    for paragraph in document.paragraphs:
        if paragraph.index < thanks_index:
            continue
        text = paragraph.text.strip()
        if not text:
            continue
        if paragraph.index == thanks_index:
            if paragraph.alignment is not None and paragraph.alignment != heading_alignment:
                issues.append(
                    _issue(
                        "THANKS_HEADING_FORMAT",
                        Severity.WARNING,
                        "Acknowledgements heading alignment should match the configured format.",
                        location=_paragraph_location(paragraph),
                        expected=heading_alignment,
                        actual=paragraph.alignment,
                        evidence=text,
                    )
                )
            issues.extend(
                _check_explicit_run_format(
                    paragraph,
                    code="THANKS_HEADING_FORMAT",
                    expected_size_pt=_float_cfg(rules, "thanks", "heading_size_pt"),
                    expected_east_asia=str(_cfg(rules, "thanks", "heading_east_asia")),
                    rules=rules,
                )
            )
            continue
        if _is_heading_text(text, rules):
            break
        if paragraph.first_line_indent_chars is not None:
            if abs(paragraph.first_line_indent_chars - body_indent) > _float_cfg(rules, "tolerances", "indent_chars"):
                issues.append(
                    _issue(
                        "THANKS_BODY_FORMAT",
                        Severity.WARNING,
                        "Acknowledgements body first-line indent should match the configured format.",
                        location=_paragraph_location(paragraph),
                        expected=f"{body_indent:g} characters",
                        actual=f"{paragraph.first_line_indent_chars:g} characters",
                        evidence=text,
                    )
                )
        issues.extend(
            _check_explicit_run_format(
                paragraph,
                code="THANKS_BODY_FORMAT",
                expected_size_pt=_float_cfg(rules, "thanks", "body_size_pt"),
                expected_east_asia=str(_cfg(rules, "thanks", "body_east_asia")),
                rules=rules,
            )
        )
    return issues


def _check_line_spacing(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        if not _looks_like_line_spacing_target(paragraph, document, rules):
            continue
        issues.extend(_line_spacing_issues_for_paragraph(paragraph, _paragraph_location(paragraph), rules=rules))
    return issues


def _line_spacing_issues_for_paragraph(
    paragraph: ParagraphInfo,
    location: str,
    *,
    code: str = "LINE_SPACING",
    expected_line_spacing_pt: float | None = None,
    rules: RuleSet | None = None,
) -> list[Issue]:
    issues: list[Issue] = []
    expected_line_spacing = (
        expected_line_spacing_pt
        if expected_line_spacing_pt is not None
        else _float_cfg(rules, "body", "line_spacing_pt")
    )
    if paragraph.line_spacing_multiple is not None:
        issues.append(
            _issue(
                code,
                Severity.WARNING,
                "Text paragraph line spacing should match the configured fixed-line format, not multiple/auto line spacing.",
                location=location,
                expected=f"fixed {expected_line_spacing:g} pt",
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
                code,
                Severity.WARNING,
                "Text paragraph line spacing should match the configured fixed-line format.",
                location=location,
                expected=f"fixed {expected_line_spacing:g} pt",
                actual=f"{paragraph.line_spacing_pt:.1f} pt ({paragraph.line_spacing_rule})",
                evidence=paragraph.text.strip(),
            )
        )
        return issues
    if abs(paragraph.line_spacing_pt - expected_line_spacing) <= _float_cfg(rules, "tolerances", "line_spacing_pt"):
        return issues
    issues.append(
        _issue(
            code,
            Severity.WARNING,
            "Text paragraph line spacing should match the configured fixed-line format.",
            location=location,
            expected=f"{expected_line_spacing:g} pt",
            actual=f"{paragraph.line_spacing_pt:.1f} pt",
        )
    )
    return issues


def _check_numbering_document(document: DocumentInfo, rules: RuleSet) -> list[Issue]:
    issues: list[Issue] = []
    for paragraph in document.paragraphs:
        issues.extend(_check_numbering(paragraph, rules))
    return issues


def _check_header_line_format(document: DocumentInfo, rules: RuleSet) -> list[Issue]:
    return [issue for issue in _check_static_headers_and_page_numbers(document, rules) if issue.code == "HEADER_LINE_WIDTH"]


def _check_reference_citation_separator(document: DocumentInfo, rules: RuleSet | None = None) -> list[Issue]:
    issues: list[Issue] = []
    expected_separator = str(_cfg(rules, "reference", "citation_separator"))
    first_body = _first_body_paragraph_index(document, rules)
    reference_start = _reference_heading_index(document, rules)
    for paragraph in document.paragraphs:
        if paragraph.index < first_body:
            continue
        if reference_start is not None and paragraph.index >= reference_start:
            continue
        raw_text = paragraph.text
        for match in _REFERENCE_CITATION_RE.finditer(raw_text):
            citation_inner = match.group(1)
            if "," in citation_inner and expected_separator != ",":
                citation_text = match.group(0)
                issues.append(
                    _issue(
                        "REFERENCE_CITATION_SEPARATOR",
                        Severity.WARNING,
                        "Multiple reference numbers in one citation should use the configured separator.",
                        location=_paragraph_location(paragraph),
                        expected=f"configured separator, e.g. [1{expected_separator}2]",
                        actual=citation_text,
                        evidence=citation_text,
                    )
                )
    return issues


def _check_registry():
    return (
        (
            "structure",
            (
                "STRUCTURE_ABSTRACT_CN",
                "STRUCTURE_ABSTRACT_EN",
                "STRUCTURE_TOC",
                "STRUCTURE_BODY_START",
                "STRUCTURE_REFERENCES",
                "STRUCTURE_THANKS",
            ),
            _check_structure_presence,
        ),
        ("page", ("PAGE_SETUP",), _check_page_settings),
        ("header_text", ("HEADER_TEXT",), _check_header_text),
        (
            "header_static",
            ("STATIC_BODY_HEADER", "STATIC_PAGE_FIELD", "HEADER_LINE_POSITION"),
            _check_static_headers_and_page_numbers,
        ),
        ("header_line", ("HEADER_LINE_WIDTH",), _check_header_line_format),
        ("major_headings", ("MAJOR_HEADING_SPACING",), _check_major_heading_spacing),
        ("abstract", ("ABSTRACT_FORMAT",), _check_abstract_format),
        (
            "headings",
            ("HEADING_PUNCTUATION", "HEADING_FORMAT", "HEADING_SCRIPT_FONT", "HEADING_SPACING"),
            lambda document, rules: _check_headings(document, rules) + _check_heading_script_fonts(document, rules),
        ),
        ("numbering", ("FIGURE_NUMBERING", "TABLE_NUMBERING", "EQUATION_NUMBERING"), _check_numbering_document),
        (
            "keywords",
            ("KEYWORD_LABEL_FORMAT", "KEYWORD_SEPARATOR", "KEYWORD_TERMINATOR", "KEYWORD_COUNT"),
            _check_keywords,
        ),
        (
            "references",
            (
                "REFERENCE_FORMAT",
                "REFERENCE_CITATION_FORMAT",
                "REFERENCE_CITATION_FIELD",
                "REFERENCE_CITATION_TARGET",
                "REFERENCE_HEADING_FORMAT",
                "REFERENCE_LIST_FORMAT",
                "REFERENCE_LIST_SPACING",
            ),
            lambda document, rules: _check_references(document, rules)
            + _check_reference_citations(document, rules)
            + _check_reference_typography(document, rules),
        ),
        ("reference_citation_separator", ("REFERENCE_CITATION_SEPARATOR",), _check_reference_citation_separator),
        ("toc", ("TOC_FIELD",), _check_toc_fields),
        (
            "table_layout",
            (
                "TABLE_BORDER",
                "TABLE_THREE_LINE",
                "TABLE_LINE_COUNT",
                "TABLE_BORDER_WIDTH",
                "TABLE_HEADER_BORDER",
                "TABLE_WIDTH",
                "TABLE_ALIGNMENT",
                "TABLE_CELL_WIDTH",
                "TABLE_CELL_ALIGNMENT",
            ),
            _check_table_borders,
        ),
        (
            "table_cells",
            (
                "TABLE_CELL_FORMAT",
                "TABLE_CELL_FONT",
                "TABLE_CELL_SPACING",
            ),
            _check_table_cell_typography,
        ),
        (
            "captions",
            (
                "CAPTION_SEPARATOR",
                "CAPTION_FORMAT",
                "CAPTION_LINE_SPACING",
                "FIGURE_CAPTION_POSITION",
                "TABLE_CAPTION_POSITION",
                "CONTINUED_TABLE_LAYOUT",
            ),
            lambda document, rules: _check_captions(document, rules)
            + _check_caption_object_order(document, rules)
            + _check_continued_table_layout(document, rules),
        ),
        ("page_numbering", ("PAGE_NUMBERING_STATIC",), _check_page_numbering_static),
        ("empty_paragraphs", ("EMPTY_PARAGRAPHS",), _check_empty_paragraphs),
        ("body", ("BODY_INDENT", "BODY_SPACING", "BODY_FONT"), _check_body_typography),
        ("mixed_language", ("MIXED_LANGUAGE_SPACING",), _check_mixed_language_spacing),
        ("thanks", ("THANKS_HEADING_FORMAT", "THANKS_BODY_FORMAT"), _check_thanks_format),
        ("line_spacing", ("LINE_SPACING",), _check_line_spacing),
    )


CHECK_SELECTOR_ALIASES = {
    "header": {"header_text", "header_static", "header_line"},
    "references": {"references", "reference_citation_separator"},
    "tables": {"table_layout", "table_cells"},
}


def _configured_checks(rules: RuleSet) -> tuple[set[str] | None, set[str]]:
    checks_config = rules.config.get("checks", {}) if isinstance(rules.config, dict) else {}
    if not isinstance(checks_config, dict):
        raise ValueError("checks must be an object")
    enabled_raw = checks_config.get("enabled")
    disabled_raw = checks_config.get("disabled")
    enabled = None
    if enabled_raw is not None:
        if not isinstance(enabled_raw, list):
            raise ValueError("checks.enabled must be an array")
        enabled = {str(item) for item in enabled_raw}
    disabled = set()
    if disabled_raw is not None:
        if not isinstance(disabled_raw, list):
            raise ValueError("checks.disabled must be an array")
        disabled = {str(item) for item in disabled_raw}
    selectors = _known_check_selectors()
    unknown = sorted(((enabled or set()) | disabled) - selectors)
    if unknown:
        raise ValueError(f"unknown checks selector: {', '.join(unknown)}")
    return enabled, disabled


def _known_check_selectors() -> set[str]:
    selectors: set[str] = set()
    for group, items, _runner in _check_registry():
        selectors.add(group)
        selectors.update(items)
    selectors.update(CHECK_SELECTOR_ALIASES)
    return selectors


def _groups_for_selector(selector: str) -> set[str]:
    groups: set[str] = set()
    groups.update(CHECK_SELECTOR_ALIASES.get(selector, set()))
    for group, items, _runner in _check_registry():
        if selector == group or selector in items:
            groups.add(group)
    return groups


def _item_is_selected(item: str, group: str, enabled: set[str] | None, disabled: set[str]) -> bool:
    if _item_is_disabled(item, group, disabled):
        return False
    if enabled is None:
        return True
    return item in enabled or group in enabled or any(group in CHECK_SELECTOR_ALIASES.get(selector, set()) for selector in enabled)


def _item_is_disabled(item: str, group: str, disabled: set[str]) -> bool:
    return item in disabled or group in disabled or any(group in _groups_for_selector(selector) for selector in disabled)


def _active_item_codes(rules: RuleSet) -> tuple[set[str], tuple[str, ...]]:
    enabled, disabled = _configured_checks(rules)
    active: set[str] = set()
    skipped: list[str] = []
    for group, items, _runner in _check_registry():
        for item in items:
            if _item_is_selected(item, group, enabled, disabled):
                active.add(item)
                continue
            reason = (
                "disabled by the active school rules"
                if _item_is_disabled(item, group, disabled)
                else "not enabled by the active school rules"
            )
            skipped.append(f"{item}: {reason}")
    return active, tuple(skipped)


def _group_required_paths(group: str) -> tuple[tuple[str, ...], ...]:
    return {
        "structure": (("structure", "required"),),
        "header_text": (("header", "body_text"),),
        "header_static": (("header", "body_text"),),
        "header_line": (("header", "body_text"), ("header", "line_size_eighths"), ("header", "line_space")),
        "major_headings": (("structure", "major_heading_expected"),),
        "abstract": (("abstract",), ("structure", "headings")),
        "headings": (("heading",), ("structure", "patterns")),
        "numbering": (("numbering",),),
        "keywords": (("keywords",),),
        "references": (("reference",), ("structure", "headings")),
        "toc": (("structure", "headings"),),
        "table_layout": (("table",),),
        "table_cells": (("table",),),
        "captions": (("caption",), ("numbering",)),
        "body": (("body",),),
        "mixed_language": (("structure",),),
        "thanks": (("thanks",), ("structure", "headings")),
        "line_spacing": (("body",),),
    }.get(group, ())


def _item_required_paths(item: str) -> tuple[tuple[str, ...], ...]:
    return {
        "BODY_INDENT": (("body", "first_line_indent_chars"),),
        "BODY_SPACING": (("body", "space_before_pt"), ("body", "space_after_pt")),
        "BODY_FONT": (("body", "size_pt"), ("body", "east_asia"), ("body", "ascii")),
        "KEYWORD_LABEL_FORMAT": (
            ("keywords", "cn_label"),
            ("keywords", "en_label"),
            ("keywords", "label_delimiter"),
            ("keywords", "allow_space_before_delimiter"),
            ("keywords", "allow_space_after_delimiter"),
        ),
        "KEYWORD_SEPARATOR": (("keywords", "separator"),),
        "KEYWORD_TERMINATOR": (("keywords", "separator"), ("keywords", "forbid_trailing_separator")),
        "KEYWORD_COUNT": (("keywords", "separator"), ("keywords", "min_count"), ("keywords", "max_count")),
        "REFERENCE_CITATION_SEPARATOR": (
            ("reference", "citation_separator"),
            ("structure", "patterns", "body_start"),
            ("structure", "headings", "reference"),
        ),
        "HEADER_TEXT": (("header", "body_text"),),
        "STATIC_BODY_HEADER": (("header", "body_text"),),
        "HEADER_LINE_POSITION": (("header", "body_text"),),
        "HEADER_LINE_WIDTH": (("header", "line_size_eighths"), ("header", "line_space")),
        "TABLE_CELL_ALIGNMENT": (("table", "cell_alignment"),),
        "TABLE_CELL_FORMAT": (("table", "cell_size_pt"),),
        "TABLE_CELL_FONT": (("table", "cell_east_asia"), ("table", "cell_ascii")),
        "TABLE_CELL_SPACING": (
            ("table", "cell_space_before_pt"),
            ("table", "cell_space_after_pt"),
            ("table", "cell_line_spacing_pt"),
        ),
    }.get(item, ())


def _missing_config_paths(rules: RuleSet, group: str) -> tuple[str, ...]:
    missing: list[str] = []
    for path in _group_required_paths(group):
        current = rules.config
        found = True
        for item in path:
            if not isinstance(current, dict) or item not in current:
                found = False
                break
            current = current[item]
        if not found:
            missing.append(".".join(path))
    return tuple(missing)


def _missing_item_config_paths(rules: RuleSet, item: str) -> tuple[str, ...]:
    missing: list[str] = []
    for path in _item_required_paths(item):
        current = rules.config
        found = True
        for part in path:
            if not isinstance(current, dict) or part not in current:
                found = False
                break
            current = current[part]
        if not found:
            missing.append(".".join(path))
    return tuple(missing)


def run_checks(document: DocumentInfo, rules: RuleSet) -> CheckResult:
    """Run checks selected by the active school rules."""
    issues: list[Issue] = []
    active_items, skipped_items = _active_item_codes(rules)
    known_items = {item for _group, items, _runner in _check_registry() for item in items}
    checked_items: list[str] = []
    skipped = list(skipped_items)
    for group, items, runner in _check_registry():
        selected_items = tuple(item for item in items if item in active_items)
        if not selected_items:
            continue
        missing_paths = _missing_config_paths(rules, group)
        if missing_paths:
            for item in selected_items:
                skipped.append(f"{item}: missing config path {', '.join(missing_paths)}")
            continue
        runnable_items = []
        for item in selected_items:
            missing_item_paths = _missing_item_config_paths(rules, item)
            if missing_item_paths:
                skipped.append(f"{item}: missing config path {', '.join(missing_item_paths)}")
            else:
                runnable_items.append(item)
        if not runnable_items:
            continue
        group_issues = runner(document, rules)
        runnable_set = set(runnable_items)
        issues.extend(issue for issue in group_issues if issue.code in runnable_set or issue.code not in known_items)
        checked_items.extend(runnable_items)
    return CheckResult(
        issues=tuple(issues),
        checked_items=tuple(checked_items),
        skipped_items=tuple(skipped),
        unsupported_items=rules.manual_review_items,
    )
