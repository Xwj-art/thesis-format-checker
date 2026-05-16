from __future__ import annotations

from datetime import datetime

from .model import CheckResult, DocumentInfo, RuleSet, Severity


def render_markdown_report(document: DocumentInfo, rules: RuleSet, result: CheckResult) -> str:
    """Render a human-readable Markdown report."""
    issues_by_severity: dict[Severity, list] = {severity: [] for severity in Severity}
    for issue in result.issues:
        issues_by_severity[issue.severity].append(issue)

    counts = {severity: len(issues_by_severity[severity]) for severity in Severity}

    lines = [
        "# 毕业论文格式检查报告",
        "",
        f"- 论文文件：`{document.path}`",
        f"- 规则文件：`{rules.source_path}`",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 汇总",
        "",
        f"- 错误：{counts[Severity.ERROR]}",
        f"- 警告：{counts[Severity.WARNING]}",
        f"- 信息：{counts[Severity.INFO]}",
        "",
        "## 按严重性分组的问题",
        "",
    ]

    severity_labels = {
        Severity.ERROR: "错误",
        Severity.WARNING: "警告",
        Severity.INFO: "信息",
    }
    for severity in (Severity.ERROR, Severity.WARNING, Severity.INFO):
        lines.extend([f"### {severity_labels[severity]}", ""])
        if not issues_by_severity[severity]:
            lines.append("无")
            lines.append("")
            continue
        for issue in issues_by_severity[severity]:
            lines.append(f"- `{issue.code}`：{issue.message}")
            if issue.location:
                lines.append(f"  - 位置：{issue.location}")
            if issue.expected:
                lines.append(f"  - 期望：{issue.expected}")
            if issue.actual:
                lines.append(f"  - 实际：{issue.actual}")
            if issue.evidence:
                lines.append(f"  - 证据：`{issue.evidence}`")
        lines.append("")

    lines.extend(["## 已检查项", ""])
    if result.checked_items:
        for item in result.checked_items:
            lines.append(f"- {item}")
    else:
        lines.append("无")
    lines.append("")

    lines.extend(["## 不支持自动检查项", ""])
    if result.unsupported_items:
        for item in result.unsupported_items:
            lines.append(f"- {item}")
    else:
        lines.append("无")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"
