"""生成 DOCX 模板（docxtpl 用）：templates/monthly_report_template.docx。

模板里不写任何手写数字：章节号用中文数字，数字只以 Jinja 占位符形式出现。
"本月无 P0 失败"里的 P0 是术语（数据集 p0_term 字段有来源），不是手写数字。

docxtpl 循环写法（以源码 patch_xml 为准）：
- 表格行循环：{%tr for ... %} 独占一行，数据行，{%tr endfor %} 独占一行；
- 段落循环：{%p for ... %} 独占一段，内容段，{%p endfor %} 独占一段。
普通 {% for %} 只在单元格/段落内重复文本，不会复制行，切勿使用。
"""

from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

FONT = "Noto Serif CJK SC"


def _set_font(run, size=12):
    run.font.name = FONT
    run.font.size = Pt(size)
    r_fonts = run._element.get_or_add_rPr().get_or_add_rFonts()
    r_fonts.set(qn("w:eastAsia"), FONT)


def _para(doc, text, size=12):
    p = doc.add_paragraph()
    _set_font(p.add_run(text), size)
    return p


def _heading(doc, text):
    p = doc.add_heading(level=1)
    _set_font(p.add_run(text), size=16)
    return p


def _loop_para(doc, for_tag, text, size=12):
    """段落循环：for 段 + 内容段 + endfor 段。"""
    _para(doc, "{%%p for %s %%}" % for_tag, size)
    _para(doc, text, size)
    _para(doc, "{%p endfor %}", size)


def _loop_table(doc, headers, for_tag, row_cells):
    """表格行循环：表头行 + for 行 + 数据行 + endfor 行。"""
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        _set_font(table.rows[0].cells[i].paragraphs[0].add_run(h), size=12)
    row = table.add_row()
    _set_font(row.cells[0].paragraphs[0].add_run("{%%tr for %s %%}" % for_tag), size=12)
    row = table.add_row()
    for i, cell_text in enumerate(row_cells):
        _set_font(row.cells[i].paragraphs[0].add_run(cell_text), size=12)
    row = table.add_row()
    _set_font(row.cells[0].paragraphs[0].add_run("{%tr endfor %}"), size=12)
    return table


def build_template(path: Path) -> Path:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    _para(doc, "{{ report_title }}（{{ report_year }}年{{ report_month }}月）", size=20)

    _heading(doc, "一、本月结论")
    _para(doc, "本月结论三至五条，由审阅人填写，系统只预填数据事实作为提示：")
    _loop_para(doc, "fact in conclusion_facts", "- {{ fact }}")

    _heading(doc, "二、能力评测")
    _para(doc, "各工具通过率表与趋势图如下：")
    _loop_table(
        doc,
        ["工具", "通过率", "样本量", "备注"],
        "tool in tools",
        [
            "{{ tool.name }}{% if tool.low_sample %}※{% endif %}",
            "{{ tool.pass_rate }}%",
            "{{ tool.samples }}",
            "{% if tool.low_sample %}样本量不足{% else %}正常{% endif %}",
        ],
    )
    _para(doc, "{{ chart_trend }}")

    _heading(doc, "三、护栏与红队")
    _para(
        doc,
        "{% if p0_failures == 0 %}本月无 P0 失败{% else %}本月 P0 失败数为 {{ p0_failures }} 起，需逐项跟进。{% endif %}",
    )
    _loop_para(doc, "item in p0_items", "- {{ item.name }}：{{ item.desc }}")

    _heading(doc, "四、采纳与修改幅度")
    _para(doc, "按工具的表格与拒绝原因分布图如下：")
    _loop_table(
        doc,
        ["工具", "使用次数", "修改次数", "拒绝次数"],
        "row in adoption",
        ["{{ row.tool }}", "{{ row.uses }}", "{{ row.edits }}", "{{ row.rejects }}"],
    )
    _para(doc, "{{ chart_reject }}")

    _heading(doc, "五、Top 失败模式")
    _loop_table(
        doc,
        ["失败模式", "出现次数", "是否已人工复核"],
        "row in top_failures",
        [
            "{{ row.mode }}",
            "{{ row.count }}",
            "{% if row.reviewed %}已人工复核{% else %}待人工复核{% endif %}",
        ],
    )

    _heading(doc, "六、下月改进事项")
    _para(doc, "下月改进事项从未关闭的红队发现与退化事件自动列出，负责人角色可编辑：")
    _loop_para(doc, "imp in improvements", "- {{ imp.item }}（负责人：{{ imp.owner_role }}，{{ imp.due }}）")

    _heading(doc, "七、附录")
    _para(doc, "口径说明：通过率等于通过样本数除以样本总数；样本量不足的行以灰色显示并加脚注；报告中的所有数字均由程序从数据集填入。")
    _para(doc, "数据截至时间：{{ cutoff }}")
    _para(doc, "套件版本清单：")
    _loop_para(doc, "s in suite_versions", "- {{ s.name }} {{ s.version }}")
    _para(doc, "注：灰色行为样本量不足（low_sample）的行，数据仅供参考。")

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    return path


if __name__ == "__main__":
    out = build_template(Path(__file__).resolve().parents[1] / "templates" / "monthly_report_template.docx")
    print("template written:", out)
