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

    def test_extends_none_does_not_merge_whut_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "page": {"margin_top_cm": 2.5}
}
```
""",
                encoding="utf-8",
            )

            rules = load_rules(rules_path)

            self.assertEqual(rules.config["profile"]["extends"], "none")
            self.assertEqual(rules.expected_page["margin_top_cm"], 2.5)
            self.assertIsNone(rules.expected_header_text)
            self.assertNotEqual(
                rules.config.get("header", {}).get("body_text"),
                "武汉理工大学本科毕业设计（论文）",
            )
            self.assertNotIn("thanks", rules.config)
            self.assertNotIn("table", rules.config)
            self.assertNotIn("required", rules.config.get("structure", {}))

    def test_invalid_profile_extends_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{"profile": {"extends": "unknown"}}
```
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "profile\\.extends"):
                load_rules(rules_path)

    def test_invalid_regex_reports_rule_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "structure": {
    "patterns": {
      "body_start": "["
    }
  }
}
```
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "structure\\.patterns\\.body_start"):
                load_rules(rules_path)

    def test_null_config_reports_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "keywords": null
}
```
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "keywords"):
                load_rules(rules_path)

    def test_json_page_settings_take_priority_over_markdown_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

- 页边距：上 9 cm，下 9 cm，左 9 cm，右 9 cm。

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "page": {
    "margin_top_cm": 2.5,
    "margin_bottom_cm": 2.0,
    "margin_left_cm": 2.5,
    "margin_right_cm": 2.0
  }
}
```
""",
                encoding="utf-8",
            )

            rules = load_rules(rules_path)

            self.assertEqual(rules.expected_page["margin_top_cm"], 2.5)
            self.assertEqual(rules.expected_page["margin_bottom_cm"], 2.0)
            self.assertEqual(rules.expected_page["margin_left_cm"], 2.5)
            self.assertEqual(rules.expected_page["margin_right_cm"], 2.0)

    def test_json_header_text_takes_priority_over_markdown_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_path = Path(tmpdir) / "rules.md"
            rules_path.write_text(
                """# Requirements

- 正文页眉内容：`残留学校页眉`。

```json thesis-format-rules
{
  "profile": {"extends": "none"},
  "header": {
    "body_text": "某大学本科毕业论文"
  }
}
```
""",
                encoding="utf-8",
            )

            rules = load_rules(rules_path)

            self.assertEqual(rules.expected_header_text, "某大学本科毕业论文")


if __name__ == "__main__":
    unittest.main()
