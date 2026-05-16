# thesis-format-checker

一个尽量简单的毕业论文 DOCX 格式检查命令行工具。

输入学校格式要求 Markdown 文件和论文 `.docx` 文件，输出一份 Markdown
检查报告。工具只做静态检查，不会修改论文文件。

## 当前能力

- 读取 `.docx` 内部 XML，不依赖 Word、WPS 或 LibreOffice。
- 检查页面尺寸、页边距、页眉页脚距离。
- 检查正文页眉文本。
- 检查标题末尾标点。
- 检查图、表、公式编号是否误用点号格式。
- 检查中英文关键词分隔符、数量、末尾分号。
- 检查参考文献编号格式和连续性。
- 检查连续空段落。
- 检查可识别的正文固定行距是否为 20 磅。

## 使用

直接从仓库运行：

```bash
python3 -m thesis_format_checker 毕业论文格式要求.md 我的论文.docx -o reports/report.md
```

查看帮助：

```bash
python3 -m thesis_format_checker --help
```

输出 JSON 摘要：

```bash
python3 -m thesis_format_checker 毕业论文格式要求.md 我的论文.docx \
  -o reports/report.md \
  --json-summary
```

如果已经从 Word/WPS 导出了 PDF，可以增加渲染后逐页检查：

```bash
python3 -m thesis_format_checker 毕业论文格式要求.md 我的论文.docx \
  --rendered-pdf 我的论文.pdf \
  -o reports/report.md
```

`--rendered-pdf` 会使用本机 `pdftotext` 提取 PDF 逐页文本，检查正文页页眉和正文页底部阿拉伯页码是否从 1 连续。它不会替代 Word 视觉检查，但比单纯读取 `.docx` XML 更接近真实分页结果。

## 退出码

- `0`：检查完成，没有 error 级别问题。
- `1`：检查完成，存在 error 级别问题。
- `2`：输入路径错误、DOCX 无法读取或运行失败。

当前多数格式问题会以 warning 输出，因为 DOCX XML 中很多格式继承自样式，
第一版不会完全展开样式继承。

## 测试

```bash
python3 -m unittest discover
```

## 暂不自动检查

- 封面精确布局。
- 原创性声明、授权书签名是否完整。
- 表格是否严格为三线表。
- 图片内部文字大小、图片内部是否写入图题。
- 由分页和图片位置造成的大面积视觉留白。
