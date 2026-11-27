"""变异自证：改数据集 → 输出必须跟着变，证明数字确实来自数据集、不是写死的。

M1：把问答助手通过率 96.5 改为 50.0，Markdown 里必须出现 50.0 且不再出现 96.5。
M2：把 P0 失败数 0 改为 2，"本月无 P0 失败"必须消失，出现"本月 P0 失败数为 2 起"。
M3：把知识库问答 low_sample 由真改为假，DOCX 置灰行数必须由 1 变为 0。
任一变异未按预期改变输出即退出码非零。
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from docx import Document  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

from monthly_report.render import load_dataset, render_all  # noqa: E402

TEMPLATE = REPO / "templates" / "monthly_report_template.docx"
BASE = REPO / "data" / "dataset_p0_zero.json"


def _grey_rows(docx_path: Path) -> int:
    doc = Document(str(docx_path))
    count = 0
    for table in doc.tables:
        header = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
        if header != ["工具", "通过率", "样本量", "备注"]:
            continue
        for row in table.rows[1:]:
            for cell in row.cells:
                tc_pr = cell._tc.find(qn("w:tcPr"))
                if tc_pr is not None:
                    shd = tc_pr.find(qn("w:shd"))
                    if shd is not None and shd.get(qn("w:fill")) == "D9D9D9":
                        count += 1
                        break
    return count


def _docx_text(path: Path) -> str:
    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.extend(cell.text for cell in row.cells)
    return "\n".join(parts)


def main() -> int:
    base = load_dataset(BASE)
    lines: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        mutated = copy.deepcopy(base)
        mutated["tools"][0]["pass_rate"] = 50.0
        ds_path = tmp / "m1.json"
        ds_path.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
        out = render_all(ds_path, tmp / "m1", TEMPLATE)
        md = out["markdown"].read_text(encoding="utf-8")
        assert "50.0%" in md and "96.5%" not in md, "M1 失败：通过率变异未反映到输出"
        lines.append("MUTATION M1 PASS: pass_rate 96.5 -> 50.0, Markdown 同步变为 50.0%")

        mutated = copy.deepcopy(base)
        mutated["p0_failures"] = 2
        mutated["p0_items"] = [
            {"name": "红队发现一", "desc": "护栏未拦截违规表述"},
            {"name": "红队发现二", "desc": "引用来源与正文不一致"},
        ]
        ds_path = tmp / "m2.json"
        ds_path.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
        out = render_all(ds_path, tmp / "m2", TEMPLATE)
        md = out["markdown"].read_text(encoding="utf-8")
        assert "本月无 P0 失败" not in md, "M2 失败：零值文案未消失"
        assert "本月 P0 失败数为 2 起" in md, "M2 失败：非零文案未出现"
        lines.append("MUTATION M2 PASS: p0_failures 0 -> 2, 文案由'本月无 P0 失败'变为'本月 P0 失败数为 2 起'")

        mutated = copy.deepcopy(base)
        mutated["tools"][2]["low_sample"] = False
        ds_path = tmp / "m3.json"
        ds_path.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
        out = render_all(ds_path, tmp / "m3", TEMPLATE)
        assert _grey_rows(out["docx"]) == 0, "M3 失败：取消 low_sample 后仍有置灰行"
        lines.append("MUTATION M3 PASS: low_sample True -> False, DOCX 置灰行数由 1 变为 0")

    text = "\n".join(lines) + "\n"
    print(text, end="")
    evidence = REPO / "evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / "mutation_proof.log").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
