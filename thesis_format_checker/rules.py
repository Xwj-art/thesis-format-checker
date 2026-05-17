from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .model import RuleSet


DEFAULT_RULES_PATH = Path(__file__).resolve().with_name("default_rules.md")
BASE_CONFIG = {
    "tolerances": {
        "page_cm": 0.1,
        "line_spacing_pt": 0.5,
        "line_space_lines": 0.05,
        "font_size_pt": 0.25,
        "indent_chars": 0.25,
    },
    "keywords": {
        "min_count": 1,
        "max_count": 10,
        "cn_label": "关键词",
        "en_label": "Key Words",
        "label_delimiter": "：",
        "allow_space_before_delimiter": False,
        "allow_space_after_delimiter": False,
        "separator": "；",
        "forbid_trailing_separator": True,
    }
}
OBJECT_CONFIG_KEYS = {
    "profile",
    "checks",
    "tolerances",
    "page",
    "header",
    "structure",
    "fonts",
    "heading",
    "abstract",
    "body",
    "caption",
    "keywords",
    "numbering",
    "reference",
    "table",
    "thanks",
}
_CONFIG_BLOCK_RE = re.compile(
    r"```(?:json\s+)?thesis-format-rules\s*\n(.*?)\n```",
    flags=re.IGNORECASE | re.DOTALL,
)


def _extract_config(raw_markdown: str, source_path: Path) -> dict:
    match = _CONFIG_BLOCK_RE.search(raw_markdown)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid thesis-format-rules JSON in {source_path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"thesis-format-rules JSON must be an object in {source_path}")
    return parsed


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(base_value, value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=1)
def default_rules() -> RuleSet:
    return load_rules(DEFAULT_RULES_PATH)


def _default_config() -> dict:
    return default_rules().config


def _profile_extends(config: dict) -> str:
    profile = config.get("profile")
    if not isinstance(profile, dict):
        return "builtin-whut-v1"
    value = profile.get("extends", "builtin-whut-v1")
    if value not in {"builtin-whut-v1", "none"}:
        raise ValueError("profile.extends must be one of: builtin-whut-v1, none")
    return str(value)


def _validate_object_sections(config: dict) -> None:
    for key in OBJECT_CONFIG_KEYS:
        if key not in config:
            continue
        if not isinstance(config[key], dict):
            raise ValueError(f"{key} must be an object in thesis-format-rules")


def _validate_regex_patterns(config: dict) -> None:
    structure = config.get("structure")
    if isinstance(structure, dict):
        patterns = structure.get("patterns")
        if isinstance(patterns, dict):
            for key, pattern in patterns.items():
                if not isinstance(pattern, str):
                    raise ValueError(f"structure.patterns.{key} must be a regex string")
                try:
                    re.compile(pattern)
                except re.error as exc:
                    raise ValueError(f"invalid regex in structure.patterns.{key}: {exc}") from exc

    numbering = config.get("numbering")
    if isinstance(numbering, dict):
        for key, pattern in numbering.items():
            if not isinstance(pattern, str):
                raise ValueError(f"numbering.{key} must be a regex string")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"invalid regex in numbering.{key}: {exc}") from exc


def _validate_config(config: dict) -> None:
    _validate_object_sections(config)
    _validate_regex_patterns(config)


def _extract_manual_review_items(raw: str, config: dict) -> tuple[str, ...]:
    match = re.search(
        r"^## Manual Review Items\s*(.*?)(?:\n## |\Z)",
        raw,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        return tuple(str(item) for item in config.get("manual_review_items", ()))

    items: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        item = stripped[2:].strip()
        if item:
            items.append(item)
    return tuple(items) if items else tuple(str(item) for item in config.get("manual_review_items", ()))


def _extract_expected_page_settings(raw_markdown: str, config: dict) -> dict[str, float]:
    configured_page_keys = set(config.get("page", {})) if isinstance(config.get("page"), dict) else set()
    expected: dict[str, float] = {
        key: float(value)
        for key, value in config.get("page", {}).items()
        if isinstance(value, int | float)
    }

    margin_match = re.search(
        r"页边距：上\s*([0-9.]+)\s*cm，下\s*([0-9.]+)\s*cm，左\s*([0-9.]+)\s*cm，右\s*([0-9.]+)\s*cm",
        raw_markdown,
    )
    if margin_match:
        for key, value in (
            ("margin_top_cm", margin_match.group(1)),
            ("margin_bottom_cm", margin_match.group(2)),
            ("margin_left_cm", margin_match.group(3)),
            ("margin_right_cm", margin_match.group(4)),
        ):
            if key not in configured_page_keys:
                expected[key] = float(value)

    header_distance_match = re.search(r"页眉距离：\s*([0-9.]+)\s*cm", raw_markdown)
    if header_distance_match and "header_distance_cm" not in configured_page_keys:
        expected["header_distance_cm"] = float(header_distance_match.group(1))

    footer_distance_match = re.search(r"页脚距离：\s*([0-9.]+)\s*cm", raw_markdown)
    if footer_distance_match and "footer_distance_cm" not in configured_page_keys:
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
    config = _extract_config(raw, rule_path)
    if rule_path.resolve() != DEFAULT_RULES_PATH.resolve():
        if _profile_extends(config) == "builtin-whut-v1":
            config = _deep_merge(_default_config(), config)
        else:
            config = _deep_merge(BASE_CONFIG, config)
    _validate_config(config)
    expected_header_text = None
    header = config.get("header", {})
    if isinstance(header, dict):
        value = header.get("body_text")
        if isinstance(value, str) and value:
            expected_header_text = value
    if expected_header_text is None:
        expected_header_text = _extract_expected_header_text(raw)
    return RuleSet(
        source_path=rule_path,
        raw_markdown=raw,
        config=config,
        expected_header_text=expected_header_text,
        expected_page=_extract_expected_page_settings(raw, config),
        manual_review_items=_extract_manual_review_items(raw, config),
    )
