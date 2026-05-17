from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .model import CheckResult, Issue, RuleSet, Severity


_ROMAN_RE = re.compile(r"^[ivxlcdmIVXLCDM]+$")
_ARABIC_RE = re.compile(r"^\d+$")


def run_rendered_pdf_checks(pdf_path: str | Path, rules: RuleSet) -> CheckResult:
    """Check rendered PDF text for page-level header and page-number evidence."""
    path = Path(pdf_path)
    if not path.exists():
        return CheckResult(
            issues=(
                Issue(
                    code="PDF_INPUT",
                    severity=Severity.ERROR,
                    message="Rendered PDF file does not exist.",
                    actual=str(path),
                ),
            ),
            checked_items=("PDF_INPUT",),
        )

    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return CheckResult(
            issues=(
                Issue(
                    code="PDF_TEXT_EXTRACTOR",
                    severity=Severity.INFO,
                    message="pdftotext was not found; rendered PDF checks were skipped.",
                    expected="pdftotext on PATH",
                    actual="not found",
                ),
            ),
            checked_items=("PDF_TEXT_EXTRACTOR",),
        )

    try:
        completed = subprocess.run(
            [pdftotext, "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except OSError as exc:
        return CheckResult(
            issues=(
                Issue(
                    code="PDF_TEXT_EXTRACTOR",
                    severity=Severity.ERROR,
                    message="Failed to run pdftotext.",
                    actual=str(exc),
                ),
            ),
            checked_items=("PDF_TEXT_EXTRACTOR",),
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            issues=(
                Issue(
                    code="PDF_TEXT_EXTRACTOR",
                    severity=Severity.ERROR,
                    message="pdftotext timed out while extracting rendered PDF text.",
                    actual=str(path),
                ),
            ),
            checked_items=("PDF_TEXT_EXTRACTOR",),
        )

    if completed.returncode != 0:
        return CheckResult(
            issues=(
                Issue(
                    code="PDF_TEXT_EXTRACTOR",
                    severity=Severity.ERROR,
                    message="pdftotext failed to extract rendered PDF text.",
                    actual=completed.stderr.strip() or f"exit code {completed.returncode}",
                ),
            ),
            checked_items=("PDF_TEXT_EXTRACTOR",),
        )

    pages = _split_pages(completed.stdout)
    issues: list[Issue] = []
    body_page_index = _find_body_start_page(pages, rules)
    if body_page_index is None:
        issues.append(
            Issue(
                code="PDF_BODY_START",
                severity=Severity.WARNING,
                message="Rendered PDF text does not contain a detectable Chapter 1 heading.",
                expected="第1章",
                actual="not found",
            )
        )
        return CheckResult(issues=tuple(issues), checked_items=_checked_items())

    expected_header = rules.expected_header_text
    if expected_header:
        for page_index, page in enumerate(pages[body_page_index:], start=body_page_index + 1):
            top_text = "\n".join(_nonempty_lines(page)[:5])
            if expected_header not in top_text:
                issues.append(
                    Issue(
                        code="PDF_BODY_HEADER",
                        severity=Severity.WARNING,
                        message="Rendered body page header does not contain the expected text.",
                        location=f"PDF page {page_index}",
                        expected=expected_header,
                        actual=top_text or "no top text",
                    )
                )

    expected_number = 1
    for page_index, page in enumerate(pages[body_page_index:], start=body_page_index + 1):
        footer = _bottom_page_number(page)
        if footer is None:
            issues.append(
                Issue(
                    code="PDF_BODY_PAGE_NUMBER",
                    severity=Severity.WARNING,
                    message="Rendered body page does not expose an Arabic page number at the bottom.",
                    location=f"PDF page {page_index}",
                    expected=str(expected_number),
                    actual="not found",
                )
            )
            expected_number += 1
            continue
        if footer != str(expected_number):
            issues.append(
                Issue(
                    code="PDF_BODY_PAGE_NUMBER",
                    severity=Severity.WARNING,
                    message="Rendered body page number is not consecutive from 1.",
                    location=f"PDF page {page_index}",
                    expected=str(expected_number),
                    actual=footer,
                )
            )
        expected_number += 1

    for page_index, page in enumerate(pages[:body_page_index], start=1):
        lines = _nonempty_lines(page)
        if not any("摘" in line and "要" in line or "Abstract" in line or "目录" in line for line in lines):
            continue
        footer = _bottom_page_number(page)
        if footer is not None and not _ROMAN_RE.match(footer):
            issues.append(
                Issue(
                    code="PDF_FRONT_PAGE_NUMBER",
                    severity=Severity.WARNING,
                    message="Rendered front-matter page number is not Roman numeral text.",
                    location=f"PDF page {page_index}",
                    expected="Roman numeral",
                    actual=footer,
                )
            )

    return CheckResult(issues=tuple(issues), checked_items=_checked_items())


def _checked_items() -> tuple[str, ...]:
    return (
        "PDF_TEXT_EXTRACTOR",
        "PDF_BODY_START",
        "PDF_BODY_HEADER",
        "PDF_BODY_PAGE_NUMBER",
        "PDF_FRONT_PAGE_NUMBER",
    )


def _split_pages(text: str) -> list[str]:
    pages = text.split("\f")
    return [page for page in pages if page.strip()]


def _nonempty_lines(page: str) -> list[str]:
    return [line.strip() for line in page.splitlines() if line.strip()]


def _find_body_start_page(pages: list[str], rules: RuleSet | None = None) -> int | None:
    pattern = _body_start_pattern(rules)
    for index, page in enumerate(pages):
        if pattern is not None:
            if any(pattern.search(line.strip()) for line in _nonempty_lines(page)):
                return index
        compact = re.sub(r"\s+", "", page)
        if "第1章" in compact or "第1章绪论" in compact:
            return index
    return None


def _body_start_pattern(rules: RuleSet | None) -> re.Pattern[str] | None:
    if rules is None:
        return None
    try:
        pattern = rules.config["structure"]["patterns"]["body_start"]
    except (KeyError, TypeError):
        return None
    if not isinstance(pattern, str):
        return None
    try:
        return re.compile(pattern)
    except re.error:
        return None


def _bottom_page_number(page: str) -> str | None:
    for line in reversed(_nonempty_lines(page)[-8:]):
        compact = line.strip()
        if _ARABIC_RE.match(compact) or _ROMAN_RE.match(compact):
            return compact
    return None
