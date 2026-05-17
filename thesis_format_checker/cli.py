from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checks import run_checks
from .docx_reader import DocxReadError, read_docx
from .model import CheckResult, Issue, Severity
from .report import render_markdown_report
from .rendered_pdf import run_rendered_pdf_checks
from .rules import load_rules
from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="thesis-format-checker",
        description="Check thesis DOCX formatting against Markdown requirements.",
    )
    parser.add_argument("rules_md", help="Path to the school format requirements Markdown file.")
    parser.add_argument("thesis_docx", help="Path to the thesis DOCX file.")
    parser.add_argument(
        "-o",
        "--output",
        default="reports/thesis-format-report.md",
        help="Path for the generated Markdown report.",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print a JSON summary to stdout after writing the report.",
    )
    parser.add_argument(
        "--rendered-pdf",
        help="Optional Word-exported PDF for rendered page header/page-number checks.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _validate_path(path_text: str, expected_suffix: str, label: str) -> Path | None:
    path = Path(path_text)
    if path.suffix.lower() != expected_suffix:
        print(
            f"error: {label} must end with {expected_suffix}: {path}",
            file=sys.stderr,
        )
        return None
    if not path.exists():
        print(f"error: {label} does not exist: {path}", file=sys.stderr)
        return None
    if not path.is_file():
        print(f"error: {label} is not a file: {path}", file=sys.stderr)
        return None
    return path


def _severity_counts(result) -> dict[str, int]:
    counts = {severity.value: 0 for severity in Severity}
    for issue in result.issues:
        counts[issue.severity.value] += 1
    return counts


def _print_summary(output_path: Path, result, json_summary: bool) -> None:
    counts = _severity_counts(result)
    summary = {
        "output_path": str(output_path),
        "warning": counts[Severity.WARNING.value],
        "info": counts[Severity.INFO.value],
        "total": counts[Severity.WARNING.value] + counts[Severity.INFO.value],
        "checked_items": len(result.checked_items),
        "unsupported_items": len(result.unsupported_items),
    }
    if json_summary:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return
    print(
        "Report written to "
        f"{summary['output_path']} "
        f"(warning={summary['warning']}, info={summary['info']}, "
        f"total={summary['total']})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    rules_path = _validate_path(args.rules_md, ".md", "rules Markdown file")
    if rules_path is None:
        return 2

    docx_path = _validate_path(args.thesis_docx, ".docx", "thesis DOCX file")
    if docx_path is None:
        return 2
    pdf_path = None
    if args.rendered_pdf:
        pdf_path = _validate_path(args.rendered_pdf, ".pdf", "rendered PDF file")
        if pdf_path is None:
            return 2

    output_path = Path(args.output)

    try:
        document = read_docx(docx_path)
        rules = load_rules(rules_path)
        result = run_checks(document, rules)
        if pdf_path is not None:
            pdf_result = run_rendered_pdf_checks(pdf_path, rules)
            result = _merge_results(result, pdf_result)
        else:
            result = _add_rendered_pdf_missing_notice(result, rules)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_markdown_report(document, rules, result), encoding="utf-8")
    except DocxReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: unexpected failure while checking documents: {exc}", file=sys.stderr)
        return 2

    _print_summary(output_path, result, args.json_summary)

    error_count = sum(1 for issue in result.issues if issue.severity is Severity.ERROR)
    if error_count:
        return 1
    return 0


def _merge_results(left: CheckResult, right: CheckResult) -> CheckResult:
    return CheckResult(
        issues=tuple(left.issues) + tuple(right.issues),
        checked_items=tuple(left.checked_items) + tuple(
            item for item in right.checked_items if item not in left.checked_items
        ),
        unsupported_items=tuple(left.unsupported_items),
    )


def _add_rendered_pdf_missing_notice(result: CheckResult, rules) -> CheckResult:
    if not rules.expected_header_text:
        return result

    notice = Issue(
        code="RENDERED_HEADER_CHECK_SKIPPED",
        severity=Severity.INFO,
        message=(
            "Rendered page header check was not run; provide --rendered-pdf to verify "
            "body-page headers and page numbers after Word/WPS pagination."
        ),
        expected=f"--rendered-pdf with header `{rules.expected_header_text}` on body pages",
        actual="not provided",
    )
    unsupported_item = "rendered body-page header/page-number validation requires --rendered-pdf"
    unsupported_items = tuple(result.unsupported_items)
    if unsupported_item not in unsupported_items:
        unsupported_items = unsupported_items + (unsupported_item,)
    return CheckResult(
        issues=tuple(result.issues) + (notice,),
        checked_items=tuple(result.checked_items),
        unsupported_items=unsupported_items,
    )
