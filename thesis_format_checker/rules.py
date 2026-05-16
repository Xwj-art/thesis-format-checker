from __future__ import annotations

import re
from pathlib import Path

from .model import RuleSet


_A4_WIDTH_CM = 21.0
_A4_HEIGHT_CM = 29.7


def _extract_manual_review_items() -> tuple[str, ...]:
    plan_path = Path(__file__).resolve().parent.parent / "DEVELOPMENT_PLAN.md"
    if not plan_path.exists():
        return (
            "cover page exact layout",
            "electronic signatures",
            "precise table border style / three-line table validation",
            "image-internal text size or embedded captions",
            "visual large whitespace caused by pagination",
        )

    raw = plan_path.read_text(encoding="utf-8")
    match = re.search(
        r"^## Manual Review Items\s*(.*?)(?:\n## |\Z)",
        raw,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return (
            "cover page exact layout",
            "electronic signatures",
            "precise table border style / three-line table validation",
            "image-internal text size or embedded captions",
            "visual large whitespace caused by pagination",
        )

    items: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        item = stripped[2:].strip()
        if item:
            items.append(item)
    return tuple(items)


def _extract_expected_page_settings(raw_markdown: str) -> dict[str, float]:
    expected: dict[str, float] = {
        "page_width_cm": _A4_WIDTH_CM,
        "page_height_cm": _A4_HEIGHT_CM,
    }

    margin_match = re.search(
        r"页边距：上\s*([0-9.]+)\s*cm，下\s*([0-9.]+)\s*cm，左\s*([0-9.]+)\s*cm，右\s*([0-9.]+)\s*cm",
        raw_markdown,
    )
    if margin_match:
        expected["margin_top_cm"] = float(margin_match.group(1))
        expected["margin_bottom_cm"] = float(margin_match.group(2))
        expected["margin_left_cm"] = float(margin_match.group(3))
        expected["margin_right_cm"] = float(margin_match.group(4))

    header_distance_match = re.search(r"页眉距离：\s*([0-9.]+)\s*cm", raw_markdown)
    if header_distance_match:
        expected["header_distance_cm"] = float(header_distance_match.group(1))

    footer_distance_match = re.search(r"页脚距离：\s*([0-9.]+)\s*cm", raw_markdown)
    if footer_distance_match:
        expected["footer_distance_cm"] = float(footer_distance_match.group(1))

    return expected


def _extract_expected_header_text(raw_markdown: str) -> str | None:
    match = re.search(r"正文页眉内容：`([^`]+)`", raw_markdown)
    if match:
        return match.group(1).strip()

    match = re.search(r"页眉从第\s*1\s*章正文开始设置。.*?`([^`]+)`", raw_markdown)
    if match:
        return match.group(1).strip()

    return None


def load_rules(path: str | Path) -> RuleSet:
    """Load Markdown requirements into a compact rule model."""
    rule_path = Path(path)
    raw = rule_path.read_text(encoding="utf-8")
    return RuleSet(
        source_path=rule_path,
        raw_markdown=raw,
        expected_header_text=_extract_expected_header_text(raw),
        expected_page=_extract_expected_page_settings(raw),
        manual_review_items=_extract_manual_review_items(),
    )
