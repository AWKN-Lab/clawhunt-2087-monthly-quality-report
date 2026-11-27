"""渲染全部样张：两个数据集（P0 为 0 / 不为 0）各出一份 Markdown + DOCX + PDF + 图表。

输出：samples/dataset_p0_zero/ 与 samples/dataset_p0_nonzero/，每份含
report.md、report.docx、report.pdf、charts/trend.png、charts/reject.png、
page1.png（PDF 首页截图，供 AC1 核对）。
PDF 由 LibreOffice headless 从 DOCX 转换；渲染过程不调用任何 AI 模型。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from monthly_report.render import render_all  # noqa: E402

DATASETS = [REPO / "data" / "dataset_p0_zero.json", REPO / "data" / "dataset_p0_nonzero.json"]
TEMPLATE = REPO / "templates" / "monthly_report_template.docx"


def _to_pdf(docx_path: Path, out_dir: Path) -> Path:
    conv = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(out_dir), str(docx_path)],
        capture_output=True, text=True, timeout=180,
    )
    if conv.returncode != 0:
        raise RuntimeError("LibreOffice 转换失败：%s" % conv.stderr[-500:])
    pdf = out_dir / "report.pdf"
    if not pdf.exists():
        raise RuntimeError("PDF 未生成：%s" % pdf)
    return pdf


def _page1_png(pdf_path: Path, out_dir: Path) -> Path:
    subprocess.run(
        ["pdftoppm", "-png", "-f", "1", "-l", "1", "-r", "100", str(pdf_path), str(out_dir / "page")],
        check=True, timeout=120,
    )
    raw = out_dir / "page-1.png"
    png = out_dir / "page1.png"
    if raw.exists():
        raw.rename(png)
    if not png.exists():
        raise RuntimeError("首页截图未生成")
    return png


def main() -> None:
    log_lines: list[str] = []
    for dataset_path in DATASETS:
        out_dir = REPO / "samples" / dataset_path.stem
        out = render_all(dataset_path, out_dir, TEMPLATE)
        pdf = _to_pdf(out["docx"], out_dir)
        shot = _page1_png(pdf, out_dir)
        for path in [out["markdown"], out["docx"], pdf, *out["charts"], shot]:
            line = "%s %d bytes" % (path.relative_to(REPO), path.stat().st_size)
            print(line)
            log_lines.append(line)
    evidence = REPO / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "render.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print("render done: %d datasets" % len(DATASETS))


if __name__ == "__main__":
    main()
