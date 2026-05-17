from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class RunInfo:
    text: str
    font_ascii: str | None = None
    font_east_asia: str | None = None
    size_pt: float | None = None
    bold: bool | None = None
    italic: bool | None = None
    vertical_align: str | None = None


@dataclass(frozen=True)
class ParagraphInfo:
    index: int
    text: str
    block_index: int | None = None
    style: str | None = None
    style_name: str | None = None
    alignment: str | None = None
    line_spacing_pt: float | None = None
    line_spacing_multiple: float | None = None
    line_spacing_rule: str | None = None
    first_line_indent_chars: float | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    space_before_lines: float | None = None
    space_after_lines: float | None = None
    has_page_break_before: bool = False
    has_page_break: bool = False
    has_drawing: bool = False
    field_instructions: tuple[str, ...] = ()
    runs: tuple[RunInfo, ...] = ()


@dataclass(frozen=True)
class SectionInfo:
    index: int
    page_width_cm: float | None = None
    page_height_cm: float | None = None
    margin_top_cm: float | None = None
    margin_bottom_cm: float | None = None
    margin_left_cm: float | None = None
    margin_right_cm: float | None = None
    header_distance_cm: float | None = None
    footer_distance_cm: float | None = None
    page_number_start: int | None = None
    page_number_format: str | None = None
    header_texts: tuple[str, ...] = ()
    header_border_positions: tuple[str, ...] = ()
    header_bottom_border_sizes: tuple[int, ...] = ()
    header_bottom_border_spaces: tuple[int, ...] = ()
    footer_texts: tuple[str, ...] = ()
    footer_field_instructions: tuple[str, ...] = ()


@dataclass(frozen=True)
class TableInfo:
    index: int
    block_index: int | None = None
    rows: tuple[tuple[str, ...], ...] = ()
    paragraphs: tuple[ParagraphInfo, ...] = ()
    border_values: tuple[str, ...] = ()
    border_sizes: tuple[str, ...] = ()
    horizontal_line_count: int | None = None
    horizontal_line_positions: tuple[str, ...] = ()
    header_bottom_border_sizes: tuple[int, ...] = ()
    cell_width_types: tuple[tuple[str | None, ...], ...] = ()
    cell_width_values: tuple[tuple[int | None, ...], ...] = ()
    cell_vertical_alignments: tuple[str | None, ...] = ()
    has_vertical_borders: bool | None = None
    alignment: str | None = None
    width_type: str | None = None
    width_value: int | None = None


@dataclass(frozen=True)
class DocumentInfo:
    path: Path
    paragraphs: tuple[ParagraphInfo, ...] = ()
    sections: tuple[SectionInfo, ...] = ()
    tables: tuple[TableInfo, ...] = ()
    headers: tuple[str, ...] = ()
    footers: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n".join(paragraph.text for paragraph in self.paragraphs)


@dataclass(frozen=True)
class RuleSet:
    source_path: Path
    raw_markdown: str
    config: dict[str, Any] = field(default_factory=dict)
    expected_header_text: str | None = None
    expected_page: dict[str, float] = field(default_factory=dict)
    manual_review_items: tuple[str, ...] = ()


@dataclass(frozen=True)
class Issue:
    code: str
    severity: Severity
    message: str
    location: str | None = None
    expected: str | None = None
    actual: str | None = None
    evidence: str | None = None


@dataclass(frozen=True)
class CheckResult:
    issues: tuple[Issue, ...]
    checked_items: tuple[str, ...] = ()
    skipped_items: tuple[str, ...] = ()
    unsupported_items: tuple[str, ...] = ()
