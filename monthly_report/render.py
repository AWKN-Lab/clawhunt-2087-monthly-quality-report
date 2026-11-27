"""渲染：Markdown 与 DOCX（docxtpl 模板 + python-docx 后处理灰色行）。

规则（与平台 AC 对齐）：
- 报告中的全部数字由程序从数据集填入；渲染代码只格式化数据集原值，
  不做任何会产生新数字的运算后写入正文（平均值等不在正文中出现）。
- 章节号用中文数字，不在正文里写阿拉伯数字序号。
- low_sample 行在 DOCX 表格中置灰并带脚注；Markdown 中以 ※ 标记并加脚注。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from .charts import render_reject_chart, render_trend_chart

CHAPTERS = ["一、本月结论", "二、能力评测", "三、护栏与红队", "四、采纳与修改幅度", "五、Top 失败模式", "六、下月改进事项", "七、附录"]
GREY_FILL = "D9D9D9"
FOOTNOTE = "注：灰色行为样本量不足（low_sample）的行，数据仅供参考。"
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


def load_dataset(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt_num(value) -> str:
    """只做字符串化，不改值：92.0 仍是 92.0，不产生数据集之外的新数字。"""
    return str(value)


def allowed_number_tokens(dataset: dict) -> set[str]:
    """数据集中全部数字 token（AC2 的来源集合：数字必须能在这里找到）。"""
    return set(NUMBER_RE.findall(json.dumps(dataset, ensure_ascii=False)))


def conclusion_facts(dataset: dict) -> list[str]:
    """本月结论预填的数据事实（审阅人填写结论，系统只预填事实）。只用数据集原值。"""
    tools = dataset["tools"]
    best = max(tools, key=lambda t: t["pass_rate"])
    worst = min(tools, key=lambda t: t["pass_rate"])
    low = [t for t in tools if t["low_sample"]]
    facts = [
        "本月最高通过率为 %s%%，来自%s；最低通过率为 %s%%，来自%s。"
        % (fmt_num(best["pass_rate"]), best["name"], fmt_num(worst["pass_rate"]), worst["name"]),
        "P0 失败数为 %s 起。" % fmt_num(dataset["p0_failures"]),
    ]
    if low:
        facts.append(
            "%s样本量为 %s，已标记为样本量不足。" % (low[0]["name"], fmt_num(low[0]["samples"]))
        )
    return facts


def render_markdown(dataset: dict, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(
        "# %s（%s年%s月）"
        % (dataset["report_title"], fmt_num(dataset["report_year"]), fmt_num(dataset["report_month"]))
    )
    lines.append("")
    lines.append("## 一、本月结论")
    lines.append("本月结论三至五条，由审阅人填写，系统只预填数据事实作为提示：")
    for fact in conclusion_facts(dataset):
        lines.append("- " + fact)
    lines.append("")
    lines.append("## 二、能力评测")
    lines.append("| 工具 | 通过率 | 样本量 | 备注 |")
    lines.append("| --- | --- | --- | --- |")
    for tool in dataset["tools"]:
        mark = "※" if tool["low_sample"] else ""
        note = "样本量不足" if tool["low_sample"] else "正常"
        lines.append(
            "| %s%s | %s%% | %s | %s |"
            % (tool["name"], mark, fmt_num(tool["pass_rate"]), fmt_num(tool["samples"]), note)
        )
    lines.append("")
    lines.append("![通过率趋势](charts/trend.png)")
    lines.append("")
    lines.append("## 三、护栏与红队")
    if dataset["p0_failures"] == 0:
        lines.append("本月无 P0 失败")
    else:
        lines.append("本月 P0 失败数为 %s 起，需逐项跟进。" % fmt_num(dataset["p0_failures"]))
        for item in dataset["p0_items"]:
            lines.append("- %s：%s" % (item["name"], item["desc"]))
    lines.append("")
    lines.append("## 四、采纳与修改幅度")
    lines.append("| 工具 | 使用次数 | 修改次数 | 拒绝次数 |")
    lines.append("| --- | --- | --- | --- |")
    for row in dataset["adoption"]:
        lines.append(
            "| %s | %s | %s | %s |"
            % (row["tool"], fmt_num(row["uses"]), fmt_num(row["edits"]), fmt_num(row["rejects"]))
        )
    lines.append("")
    lines.append("![拒绝原因分布](charts/reject.png)")
    lines.append("")
    lines.append("## 五、Top 失败模式")
    lines.append("| 失败模式 | 出现次数 | 是否已人工复核 |")
    lines.append("| --- | --- | --- | --- |")
    for row in dataset["top_failures"]:
        reviewed = "已人工复核" if row["reviewed"] else "待人工复核"
        lines.append("| %s | %s | %s |" % (row["mode"], fmt_num(row["count"]), reviewed))
    lines.append("")
    lines.append("## 六、下月改进事项")
    lines.append("下月改进事项从未关闭的红队发现与退化事件自动列出，负责人角色可编辑：")
    for imp in dataset["improvements"]:
        lines.append("- %s（负责人：%s，%s）" % (imp["item"], imp["owner_role"], imp["due"]))
    lines.append("")
    lines.append("## 七、附录")
    lines.append("口径说明：通过率等于通过样本数除以样本总数；样本量不足的行以灰色显示并加脚注；报告中的所有数字均由程序从数据集填入。")
    lines.append("数据截至时间：%s" % dataset["cutoff"])
    lines.append("套件版本清单：")
    for suite in dataset["suite_versions"]:
        lines.append("- %s %s" % (suite["name"], suite["version"]))
    lines.append("")
    lines.append(FOOTNOTE)
    path = out_dir / "report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _shade_low_sample_rows(docx_path: Path, dataset: dict) -> int:
    """后处理：low_sample 工具所在行整行置灰。返回置灰行数。"""
    low_names = {t["name"] for t in dataset["tools"] if t["low_sample"]}
    doc = Document(str(docx_path))
    shaded = 0
    for table in doc.tables:
        header = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
        if header != ["工具", "通过率", "样本量", "备注"]:
            continue
        for row in table.rows[1:]:
            first = row.cells[0].text.strip()
            if any(first.startswith(name) for name in low_names):
                for cell in row.cells:
                    tc_pr = cell._tc.get_or_add_tcPr()
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:fill"), GREY_FILL)
                    tc_pr.append(shd)
                shaded += 1
    doc.save(str(docx_path))
    return shaded


def render_docx(dataset: dict, template_path: Path, charts_dir: Path, out_path: Path) -> Path:
    tpl = DocxTemplate(str(template_path))
    context = {
        "report_title": dataset["report_title"],
        "report_year": dataset["report_year"],
        "report_month": dataset["report_month"],
        "conclusion_facts": conclusion_facts(dataset),
        "tools": dataset["tools"],
        "p0_failures": dataset["p0_failures"],
        "p0_items": dataset["p0_items"],
        "adoption": dataset["adoption"],
        "top_failures": dataset["top_failures"],
        "improvements": dataset["improvements"],
        "cutoff": dataset["cutoff"],
        "suite_versions": dataset["suite_versions"],
        "chart_trend": InlineImage(tpl, str(charts_dir / "trend.png"), width=Mm(150)),
        "chart_reject": InlineImage(tpl, str(charts_dir / "reject.png"), width=Mm(150)),
    }
    tpl.render(context)
    tpl.save(str(out_path))
    shaded = _shade_low_sample_rows(out_path, dataset)
    expected = sum(1 for t in dataset["tools"] if t["low_sample"])
    if shaded != expected:
        raise RuntimeError("置灰行数 %d 与 low_sample 工具数 %d 不一致" % (shaded, expected))
    return out_path


def render_all(dataset_path: str | Path, out_dir: str | Path, template_path: str | Path) -> dict:
    """渲染一份数据集：图表 PNG + Markdown + DOCX。返回各产物路径。"""
    dataset = load_dataset(dataset_path)
    out_dir = Path(out_dir)
    charts_dir = out_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    trend = render_trend_chart(dataset["weekly_pass_rates"], charts_dir / "trend.png")
    reject = render_reject_chart(dataset["reject_reasons"], charts_dir / "reject.png")
    md = render_markdown(dataset, out_dir)
    docx = render_docx(dataset, Path(template_path), charts_dir, out_dir / "report.docx")
    return {"dataset": dataset, "markdown": md, "docx": docx, "charts": [trend, reject]}
