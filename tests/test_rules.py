from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from thesis_format_checker.rules import load_rules


class RulesTests(unittest.TestCase):
    def test_load_rules_extracts_undergraduate_header_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                "- 正文页眉内容：`武汉理工大学本科毕业设计（论文）`。\n",
                encoding="utf-8",
            )

            rules = load_rules(rules_path)

            self.assertEqual(rules.expected_header_text, "武汉理工大学本科毕业设计（论文）")

    def test_load_rules_merges_markdown_config_with_default_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{"body": {"first_line_indent_chars": 3.0}}
```
""",
                encoding="utf-8",
            )

            rules = load_rules(rules_path)

            self.assertEqual(rules.config["body"]["first_line_indent_chars"], 3.0)
            self.assertEqual(rules.config["body"]["size_pt"], 12.0)


if __name__ == "__main__":
    unittest.main()
