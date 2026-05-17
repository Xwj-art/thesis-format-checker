from __future__ import annotations

from pathlib import Path
import unittest

from thesis_format_checker.model import RuleSet
from thesis_format_checker.rendered_pdf import _find_body_start_page


class RenderedPdfTests(unittest.TestCase):
    def test_rendered_pdf_body_start_uses_configured_pattern(self) -> None:
        rules = RuleSet(
            source_path=Path("rules.md"),
            raw_markdown="",
            config={"structure": {"patterns": {"body_start": r"^Chapter\s+1\b"}}},
        )
        pages = [
            "Abstract\nfront matter\nii",
            "Chapter 1 Introduction\nbody text\n1",
        ]

        self.assertEqual(_find_body_start_page(pages, rules), 1)


if __name__ == "__main__":
    unittest.main()
