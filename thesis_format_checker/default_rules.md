# 毕业论文格式检查规则

本文件既是可读的格式规则说明，也是程序默认加载的检查配置。程序读取下面
`thesis-format-rules` JSON 代码块中的值作为期望格式；修改规则时优先改这里，
不要把学校格式要求写回 Python 检查逻辑。

## 检测规则补充

- 英文摘要关键词行应写作 `Key Words：`：`Key` 与 `Words` 之间使用 1 个半角空格，
  `Words` 后直接使用中文全角冒号 `：`，冒号前后不再添加半角空格。
- 正文参考文献上标若一次引用多个编号，应使用中文全角逗号分隔，例如 `[1，2]`；
  不应使用英文半角逗号 `[1,2]`。

```json thesis-format-rules
{
  "tolerances": {
    "page_cm": 0.1,
    "line_spacing_pt": 0.5,
    "line_space_lines": 0.05,
    "font_size_pt": 0.25,
    "indent_chars": 0.25
  },
  "page": {
    "page_width_cm": 21.0,
    "page_height_cm": 29.7,
    "margin_top_cm": 2.54,
    "margin_bottom_cm": 2.54,
    "margin_left_cm": 3.17,
    "margin_right_cm": 3.17,
    "header_distance_cm": 1.27,
    "footer_distance_cm": 1.27
  },
  "header": {
    "body_text": "武汉理工大学本科毕业设计（论文）",
    "line_size_eighths": 6,
    "line_space": 1
  },
  "structure": {
    "headings": {
      "abstract_cn": ["摘  要", "摘要"],
      "abstract_en": ["Abstract"],
      "toc": ["目　　录", "目录"],
      "reference": ["参考文献"],
      "thanks": ["致  谢", "致谢"],
      "line_spacing_start": ["学位论文原创性声明", "摘  要", "摘要"],
      "line_spacing_excluded": [
        "学位论文原创性声明",
        "学位论文版权使用授权书",
        "摘  要",
        "摘要",
        "Abstract",
        "目　　录",
        "目录",
        "参考文献",
        "致  谢",
        "致谢"
      ],
      "terminal": ["致  谢", "致谢", "附录", "附录A", "附录B"]
    },
    "patterns": {
      "body_start": "^第\\s*1\\s*章\\b",
      "heading_level_1": "^第\\s*\\d+\\s*章(?:\\s+.+)?$",
      "heading_level_2": "^\\d+\\.\\d+(?:\\s+.+)?$",
      "heading_level_3": "^\\d+\\.\\d+\\.\\d+(?:\\s+.+)?$"
    },
    "required": {
      "STRUCTURE_ABSTRACT_CN": [
        "摘  要",
        "Chinese abstract heading was not detected."
      ],
      "STRUCTURE_ABSTRACT_EN": [
        "Abstract",
        "English abstract heading was not detected."
      ],
      "STRUCTURE_TOC": ["目录", "Table of contents heading was not detected."],
      "STRUCTURE_BODY_START": ["第1章", "Chapter 1 heading was not detected."],
      "STRUCTURE_REFERENCES": [
        "参考文献",
        "References heading was not detected."
      ],
      "STRUCTURE_THANKS": ["致谢", "Acknowledgements heading was not detected."]
    },
    "major_heading_expected": {
      "摘要": "摘  要",
      "目录": "目　　录",
      "参考文献": "参考文献",
      "致谢": "致  谢"
    }
  },
  "fonts": {
    "songti": "宋体",
    "heiti": "黑体",
    "times_new_roman": "Times New Roman"
  },
  "heading": {
    "space_lines": 0.5,
    "line_spacing_pt": 20.0,
    "punctuation_suffix": "：:。.;；、,，!！?？",
    "levels": {
      "1": {
        "size_pt": 18.0,
        "east_asia": "黑体",
        "ascii": "黑体",
        "alignment": "center",
        "bold": true,
        "line_spacing": "no_explicit_override"
      },
      "2": {
        "size_pt": 16.0,
        "east_asia": "黑体",
        "ascii": "黑体",
        "alignment": ["left", "both"],
        "first_line_indent_chars": 0.0,
        "bold": false,
        "line_spacing": "fixed"
      },
      "3": {
        "size_pt": 14.0,
        "east_asia": "黑体",
        "ascii": "黑体",
        "alignment": ["left", "both"],
        "first_line_indent_chars": 0.0,
        "bold": false,
        "line_spacing": "fixed"
      }
    }
  },
  "abstract": {
    "heading_size_pt": 18.0,
    "alignment": "center",
    "cn_font": "黑体",
    "en_font": "Times New Roman",
    "en_bold": true
  },
  "body": {
    "first_line_indent_chars": 2.0,
    "space_before_pt": 0.0,
    "space_after_pt": 0.0,
    "size_pt": 12.0,
    "east_asia": "宋体",
    "ascii": "Times New Roman",
    "line_spacing_pt": 20.0,
    "bold": false,
    "italic": false
  },
  "caption": {
    "size_pt": 12.0,
    "east_asia": "宋体",
    "ascii": "宋体",
    "alignment": "center",
    "first_line_indent_chars": 0.0,
    "line_spacing_pt": 20.0,
    "separator": " "
  },
  "keywords": {
    "min_count": 3,
    "max_count": 5,
    "cn_label": "关键词",
    "en_label": "Key Words",
    "label_delimiter": "：",
    "allow_space_before_delimiter": false,
    "allow_space_after_delimiter": false,
    "separator": "；",
    "forbid_trailing_separator": true
  },
  "numbering": {
    "figure_dot_pattern": "图\\s*\\d+\\.\\d+",
    "table_dot_pattern": "表\\s*\\d+\\.\\d+",
    "equation_dot_pattern": "[（(]\\s*[1-9]\\d{0,1}\\.\\d{1,2}\\s*[）)]",
    "figure_caption_pattern": "^图\\s*\\d+-\\d+(?:\\s+|$)",
    "table_caption_pattern": "^表\\s*\\d+-\\d+(?:\\s+|$)",
    "continued_table_caption_pattern": "^续表\\s*\\d+-\\d+(?:\\s+|$)",
    "caption_pattern": "^(图|表|续表)\\s*(\\d+-\\d+)(\\s+)(.+)$",
    "caption_prefix_pattern": "^(?:图|表|续表)\\s*\\d+-\\d+(?:\\s+|$)"
  },
  "reference": {
    "heading_size_pt": 18.0,
    "heading_east_asia": "黑体",
    "heading_alignment": "center",
    "list_size_pt": 10.5,
    "list_east_asia": "宋体",
    "list_ascii": "宋体",
    "list_alignment": ["left", "both"],
    "list_first_line_indent_chars": 0.0,
    "list_space_before_pt": 0.0,
    "list_space_after_pt": 0.0,
    "list_line_spacing_pt": 20.0,
    "list_bold": false,
    "list_italic": false,
    "citation_separator": "，"
  },
  "table": {
    "width_type": "pct",
    "width_value": 5000,
    "alignment": "center",
    "cell_vertical_alignment": "center",
    "outer_border_size_eighths": 18,
    "header_bottom_border_size_eighths": 6,
    "horizontal_line_count": 3,
    "cell_alignment": "center",
    "cell_size_pt": 12.0,
    "cell_east_asia": "宋体",
    "cell_ascii": "Times New Roman",
    "cell_space_before_pt": 0.0,
    "cell_space_after_pt": 0.0,
    "cell_line_spacing_pt": 20.0
  },
  "thanks": {
    "heading_size_pt": 18.0,
    "heading_east_asia": "黑体",
    "heading_alignment": "center",
    "body_size_pt": 12.0,
    "body_east_asia": "宋体",
    "body_first_line_indent_chars": 2.0
  },
  "manual_review_items": [
    "cover page exact layout",
    "electronic signatures",
    "precise table border style / three-line table validation",
    "image-internal text size or embedded captions",
    "visual large whitespace caused by pagination"
  ]
}
```
