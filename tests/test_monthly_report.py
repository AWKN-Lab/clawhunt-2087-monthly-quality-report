"""S5-EVAL-043 样品测试：AC 逐条对照 + 模板无手写数字 + 渲染确定性。

只用虚构测试数据（data/dataset_p0_*.json）；不出现客户名称。
"""

import re
import subprocess
from pathlib import Path

import pytest
from docx import Document
from docx.oxml.ns import qn

from monthly_report.render import (
    CHAPTERS,
    FOOTNOTE,
    NUMBER_RE,
    allowed_number_tokens,
    load_dataset,
    render_all,
)

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "templates" / "monthly_report_template.docx"
DATASETS = [REPO / "data" / "dataset_p0_zero.json", REPO / "data" / "dataset_p0_nonzero.json"]
NUMBER_IN_P0 = re.compile(r"\d+(?:\.\d+)?")


def _docx_text(path: Path) -> str:
    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def _render(tmp_path: Path, dataset_path: Path) -> dict:
    out_dir = tmp_path / dataset_path.stem
    return render_all(dataset_path, out_dir, TEMPLATE)


def test_markdown_has_seven_chapters(tmp_path):
    out = _render(tmp_path, DATASETS[0])
    text = out["markdown"].read_text(encoding="utf-8")
    for chapter in CHAPTERS:
        assert chapter in text, "Markdown 缺章节：%s" % chapter


def test_docx_has_seven_chapters(tmp_path):
    out = _render(tmp_path, DATASETS[0])
    text = _docx_text(out["docx"])
    for chapter in CHAPTERS:
        assert chapter in text, "DOCX 缺章节：%s" % chapter


@pytest.mark.parametrize("dataset_path", DATASETS)
def test_all_docx_numbers_traceable_to_dataset(tmp_path, dataset_path):
    """AC2：从 DOCX 中解析出的全部数字都能在数据集中找到来源。"""
    out = _render(tmp_path, dataset_path)
    dataset = load_dataset(dataset_path)
    allowed = allowed_number_tokens(dataset)
    found = NUMBER_RE.findall(_docx_text(out["docx"]))
    assert found, "DOCX 中未解析出任何数字"
    untraced = sorted(set(found) - allowed)
    assert not untraced, "DOCX 中有数据集之外来源的数字：%s" % untraced


@pytest.mark.parametrize("dataset_path", DATASETS)
def test_markdown_numbers_traceable(tmp_path, dataset_path):
    out = _render(tmp_path, dataset_path)
    dataset = load_dataset(dataset_path)
    allowed = allowed_number_tokens(dataset)
    found = NUMBER_RE.findall(out["markdown"].read_text(encoding="utf-8"))
    assert found, "Markdown 中未解析出任何数字"
    untraced = sorted(set(found) - allowed)
    assert not untraced, "Markdown 中有数据集之外来源的数字：%s" % untraced


def test_p0_zero_copy(tmp_path):
    """AC3（一）：P0 失败数为 0 时渲染对应文案。"""
    out = _render(tmp_path, DATASETS[0])
    assert "本月无 P0 失败" in _docx_text(out["docx"])
    assert "本月无 P0 失败" in out["markdown"].read_text(encoding="utf-8")


def test_p0_nonzero_copy(tmp_path):
    """AC3（二）：P0 失败数不为 0 时渲染对应文案。"""
    out = _render(tmp_path, DATASETS[1])
    docx_text = _docx_text(out["docx"])
    assert "本月 P0 失败数为 3 起" in docx_text
    assert "本月无 P0 失败" not in docx_text
    assert "本月 P0 失败数为 3 起" in out["markdown"].read_text(encoding="utf-8")


@pytest.mark.parametrize("dataset_path", DATASETS)
def test_low_sample_rows_grey_with_footnote(tmp_path, dataset_path):
    """AC4：low_sample 行在表格中为灰色并带脚注。"""
    out = _render(tmp_path, dataset_path)
    dataset = load_dataset(dataset_path)
    doc = Document(str(out["docx"]))
    low_names = {t["name"] for t in dataset["tools"] if t["low_sample"]}
    grey_rows = 0
    for table in doc.tables:
        header = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
        if header != ["工具", "通过率", "样本量", "备注"]:
            continue
        for row in table.rows[1:]:
            first = row.cells[0].text.strip()
            fills = set()
            for cell in row.cells:
                tc_pr = cell._tc.find(qn("w:tcPr"))
                if tc_pr is not None:
                    shd = tc_pr.find(qn("w:shd"))
                    if shd is not None:
                        fills.add(shd.get(qn("w:fill")))
            is_low = any(first.startswith(name) for name in low_names)
            if is_low:
                assert fills == {"D9D9D9"}, "low_sample 行未整行置灰：%s 实际 %s" % (first, fills)
                grey_rows += 1
            else:
                assert "D9D9D9" not in fills, "非 low_sample 行被置灰：%s" % first
    assert grey_rows == len(low_names) == 1, "置灰行数 %d 与 low_sample 数 %d 不一致" % (grey_rows, len(low_names))
    assert FOOTNOTE in _docx_text(out["docx"])
    assert "※" in out["markdown"].read_text(encoding="utf-8")


def test_template_has_no_hardcoded_digits():
    """模板里不得出现手写数字：除去 Jinja 占位符与术语 P0 后，模板文本中无数字。"""
    doc = Document(str(TEMPLATE))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    raw = "\n".join(parts)
    no_tags = re.sub(r"\{\{.*?\}\}|\{%.*?%\}", "", raw)
    no_p0 = no_tags.replace("P0", "")
    assert not NUMBER_IN_P0.search(no_p0), "模板含手写数字：%s" % no_p0[:200]


@pytest.mark.parametrize("dataset_path", DATASETS)
def test_charts_rendered(tmp_path, dataset_path):
    out = _render(tmp_path, dataset_path)
    for chart in out["charts"]:
        raw = chart.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", "图表不是有效 PNG：%s" % chart
        assert len(raw) > 1024, "图表文件过小，可能为空图：%s" % chart
    doc = Document(str(out["docx"]))
    assert len(doc.inline_shapes) == 2, "DOCX 应内嵌两张图，实际 %d 张" % len(doc.inline_shapes)


@pytest.mark.parametrize("dataset_path", DATASETS)
def test_pdf_has_seven_chapters_no_garbled(tmp_path, dataset_path):
    """AC1：样张 PDF 含 7 个章节且中文无乱码（pdftotext 提取核对）。"""
    out = _render(tmp_path, dataset_path)
    pdf_dir = tmp_path / (dataset_path.stem + "_pdf")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    conv = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(pdf_dir), str(out["docx"])],
        capture_output=True, text=True, timeout=180,
    )
    assert conv.returncode == 0, "LibreOffice 转换失败：%s" % conv.stderr[-500:]
    pdf = pdf_dir / "report.pdf"
    assert pdf.exists() and pdf.stat().st_size > 1024
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, timeout=60)
    assert text.returncode == 0
    assert "\ufffd" not in text.stdout, "PDF 文本含替换字符，可能中文乱码"
    for chapter in CHAPTERS:
        assert chapter in text.stdout, "PDF 缺章节：%s" % chapter


def test_render_markdown_deterministic(tmp_path):
    first = _render(tmp_path / "a", DATASETS[0])["markdown"].read_text(encoding="utf-8")
    second = _render(tmp_path / "b", DATASETS[0])["markdown"].read_text(encoding="utf-8")
    assert first == second, "同一数据集两次渲染的 Markdown 不一致"


@pytest.mark.parametrize("dataset_path", DATASETS)
def test_no_client_name_in_outputs(tmp_path, dataset_path):
    """只用虚构测试数据；交付物中不出现客户名称。"""
    out = _render(tmp_path, dataset_path)
    combined = out["markdown"].read_text(encoding="utf-8") + "\n" + _docx_text(out["docx"])
    assert "客户" not in combined
    assert "有限公司" not in combined
    raw = dataset_path.read_text(encoding="utf-8")
    assert "客户" not in raw and "有限公司" not in raw
