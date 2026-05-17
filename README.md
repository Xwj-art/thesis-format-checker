# WHUT Thesis Format Checker

一个用于武汉理工大学本科毕业论文格式初筛的 `.docx` 静态检测工具。

本项目的核心定位不是把某一版学校格式要求写死在代码里，而是把“学校格式要求”沉淀为可读、可版本管理、可替换的 Markdown 文件。仓库中的 [whut毕业论文格式要求.md](./whut毕业论文格式要求.md) 是武汉理工大学毕业论文格式要求的规则说明文件，也是其他学校定制规则文件时可以参考的模板。

检测器读取“格式要求 Markdown + 论文 DOCX”，输出一份 Markdown 检测报告。工具只做静态检查，不会修改论文文件。

## 格式要求文件

[whut毕业论文格式要求.md](./whut毕业论文格式要求.md) 是本项目最重要的规则入口，承担三个角色：

- 面向人的格式说明：记录页面设置、页眉页码、摘要、目录、正文、图表、参考文献、致谢等要求。
- 面向工具的规则来源：检测脚本会读取传入的 Markdown 文件，并从其中抽取可解析的配置或格式约束。
- 面向其他学校的定制模板：其他学校可以复制这个文件，改成自己的 `xx大学毕业论文格式要求.md`，再传给检测命令，实现个性化格式检测。

小提示：格式要求 `.md` 文件非常重要。不同学校的格式要求可能散落在 Word 模板、PDF 手册、网页通知或学院补充说明里，承载形式差异很大，所以本项目没有制作“自动解析学校格式要求”的脚本。定制外校规则时，建议务必参考当前仓库里的 [whut毕业论文格式要求.md](./whut毕业论文格式要求.md)，把学校原始要求和这个 Markdown 模板一起交给 AI，让 AI 对照模板中列出的项目逐项填写，再人工核对关键数值和启用的检查项。

仓库内还包含 `thesis_format_checker/default_rules.md`。它是程序包内置的 WHUT 默认规则配置，包含 `thesis-format-rules` JSON 配置块。规则文件可以选择两种继承方式：

- `profile.extends: "builtin-whut-v1"`：继承 WHUT 默认规则，再覆盖局部字段。适合 WHUT 规则微调或同校不同模板。
- `profile.extends: "none"`：不继承 WHUT 学校规则，只使用本文件显式启用和配置的检查。适合其他学校从少量规则开始定制。

`checks.enabled` 可以限制实际运行的检查项或检查组，`checks.disabled` 可以关闭继承规则中的某些检查。常用检查组包括 `structure`、`page`、`header`、`keywords`、`references`、`tables`、`captions`、`body`、`mixed_language`、`thanks`、`line_spacing`。

外校独立规则最小示例：

````markdown
```json thesis-format-rules
{
  "profile": {
    "school_name": "某大学",
    "extends": "none"
  },
  "checks": {
    "enabled": ["page", "keywords"]
  },
  "page": {
    "margin_top_cm": 2.5,
    "margin_bottom_cm": 2.0,
    "margin_left_cm": 2.5,
    "margin_right_cm": 2.0
  },
  "keywords": {
    "en_label": "Key Words",
    "label_delimiter": "：",
    "separator": "；"
  }
}
```
````

如果不写 `profile.extends`，检测器会保持向后兼容，按 `builtin-whut-v1` 继承 WHUT 默认规则。其他学校建议显式写 `extends: "none"`，避免未声明的 WHUT 摘要、致谢、三线表、页眉等规则造成误报。

## 当前能力

- 读取 `.docx` 内部 XML，不依赖 Word、WPS 或 LibreOffice。
- 检查页面尺寸、页边距、页眉页脚距离。
- 检查正文页眉文本、页码静态元数据，并可结合导出的 PDF 做渲染后页眉页码初筛。
- 检查摘要、目录、正文标题、正文段落、图题、表题、续表、参考文献、致谢等可静态识别的格式。
- 检查 `Key Words：`、关键词数量、中文分号、末尾分号等关键词规则。
- 检查参考文献上标是否使用中文逗号分隔，如 `[1，2]`，并识别 `[1,2]` 这类英文逗号问题。
- 检查图、表、公式编号是否误用点号格式。
- 输出统一 Markdown 报告，默认建议命名为 `reports/report.md`。

## 使用

使用 WHUT 规则检测论文：

```bash
python3 -m thesis_format_checker whut毕业论文格式要求.md 毕业论文.docx -o reports/report.md
```

输出 JSON 摘要：

```bash
python3 -m thesis_format_checker whut毕业论文格式要求.md 毕业论文.docx \
  -o reports/report.md \
  --json-summary
```

如果已经从 Word/WPS 导出了 PDF，可以增加渲染后逐页检查：

```bash
python3 -m thesis_format_checker whut毕业论文格式要求.md 毕业论文.docx \
  --rendered-pdf 毕业论文.pdf \
  -o reports/report.md
```

`--rendered-pdf` 会使用本机 `pdftotext` 提取 PDF 逐页文本，检查正文页页眉和正文页底部阿拉伯页码是否从 1 连续。它不会替代 Word 视觉检查，但比单纯读取 `.docx` XML 更接近真实分页结果。

查看帮助：

```bash
python3 -m thesis_format_checker --help
```

## 其他学校如何定制

1. 复制 [whut毕业论文格式要求.md](./whut毕业论文格式要求.md)。
2. 改名为本校规则文件，例如 `某大学毕业论文格式要求.md`。
3. 收集本校格式要求原文，例如 Word 模板、PDF 手册、网页通知、学院补充说明等。
4. 推荐把“本校格式要求原文 + 复制出来的 Markdown 模板”交给 AI，让它按模板已经列出的项目逐项填写或标注“不要求/未找到”。
5. 人工核对页面设置、页眉页码、关键词、正文、图表、参考文献等关键数值。
6. 修改 Markdown 中的格式说明。
7. 在 `thesis-format-rules` JSON 配置块中设置 `profile.extends`。其他学校建议使用 `"none"`。
8. 用 `checks.enabled` 启用本校明确要求的检查项或检查组；未启用的检查会进入报告的“已跳过项”。
9. 按需填写页面、关键词、正文、参考文献等具体规则。
10. 运行：

```bash
python3 -m thesis_format_checker 某大学毕业论文格式要求.md 我的论文.docx -o reports/report.md
```

这种方式可以把学校格式要求和检测代码分离：代码负责通用 DOCX 解析和检查能力，Markdown 负责描述不同学校的规则。

## 退出码

- `0`：检查完成，没有 error 级别问题。
- `1`：检查完成，存在 error 级别问题。
- `2`：输入路径错误、DOCX 无法读取或运行失败。

当前多数格式问题会以 warning 输出，因为 DOCX XML 中很多格式继承自样式，静态检查无法百分百还原 Word/WPS 的最终渲染。

## 测试

```bash
pytest
```

## 暂不自动检查

- 封面、声明页、授权书的精确视觉布局。
- 学生、导师电子签名是否真实签入。
- 目录域是否已经刷新，以及目录页码是否和最终分页完全一致。
- 表格是否在 Word/WPS 渲染后严格呈现为三线表。
- 图片内部文字大小、图片内部是否写入图题。
- 图表跨页、续表是否在最终分页中真实成立。
- 由分页、图片、表格位置造成的大面积视觉留白。

这些项目会尽量在规则文件和报告中列为人工复核项，而不是假装已经被静态检测完全覆盖。
