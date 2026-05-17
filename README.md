# WHUT Thesis Format Checker

一个用于武汉理工大学本科毕业论文格式初筛的 `.docx` 静态检测工具。

本项目的核心定位不是把某一版学校格式要求写死在代码里，而是把“学校格式要求”沉淀为可读、可版本管理、可替换的 Markdown 文件。仓库中的 [whut毕业论文格式要求.md](./whut毕业论文格式要求.md) 是武汉理工大学毕业论文格式要求的规则说明文件，也是其他学校定制规则文件时可以参考的模板。

检测器读取“格式要求 Markdown + 论文 DOCX”，输出一份 Markdown 检测报告。工具只做静态检查，不会修改论文文件。

## 格式要求文件

[whut毕业论文格式要求.md](./whut毕业论文格式要求.md) 是本项目最重要的规则入口，承担三个角色：

- 面向人的格式说明：记录页面设置、页眉页码、摘要、目录、正文、图表、参考文献、致谢等要求。
- 面向工具的规则来源：检测脚本会读取传入的 Markdown 文件，并从其中抽取可解析的配置或格式约束。
- 面向其他学校的定制模板：其他学校可以复制这个文件，改成自己的 `xx大学毕业论文格式要求.md`，再传给检测命令，实现个性化格式检测。

仓库内还包含 `thesis_format_checker/default_rules.md`。它是程序包内置的默认规则配置，包含 `thesis-format-rules` JSON 配置块。自定义学校规则时，建议保留可读说明，并按需增加同名 JSON 配置块来覆盖默认值。

最小示例：

````markdown
```json thesis-format-rules
{
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
  },
  "reference": {
    "citation_separator": "，"
  }
}
```
````

如果没有提供某个配置项，检测器会回退到内置默认规则。

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
3. 修改 Markdown 中的格式说明。
4. 如需改变检测器实际使用的数值或关键词、参考文献等规则，在文件中加入或修改 `thesis-format-rules` JSON 配置块。
5. 运行：

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
