# 会员空间平台 · 质量月报模板渲染（S5-EVAL-043 样品）

把评测数据集与归因结果按固定模板渲染为质量月报：七章结构，图表用 matplotlib
本地渲染 PNG 并内置中文字体；DOCX 用 docxtpl 生成，PDF 由 LibreOffice headless
转换，同时导出 Markdown 版本。

## 样品说明

- 只用虚构测试数据（`data/dataset_p0_zero.json`、`data/dataset_p0_nonzero.json`），
  不含任何真实个人信息或企业信息；交付物中不出现客户名称。
- 报告中的所有数字由程序从数据集填入，模板里不得出现手写数字
  （`tests/test_monthly_report.py::test_template_has_no_hardcoded_digits` 逐字核对）。
- 渲染过程不调用任何 AI 模型；依赖其他工单接口时用接口桩或 mock 先行，
  本样品无外部依赖，对接点见下。

## 一键复跑

```bash
bash scripts/run_all.sh
```

等价于：建 venv → 装依赖 → 生成模板 → 渲染全部样张 → 跑测试 → 变异自证 → 生成 MANIFEST。
单步命令：

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/make_template.py
.venv/bin/python scripts/render_all.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/mutation_proof.py
```

另需本机装好 LibreOffice（`soffice`）与 `pdftotext`、`pdftoppm`（poppler-utils），
用于 PDF 转换与测试核对；中文字体用 Noto Serif CJK SC。

## 目录

- `data/`：两份虚构数据集（P0 失败数为 0 / 不为 0 各一份）
- `monthly_report/`：渲染代码（`render.py`、`charts.py`）
- `templates/`：DOCX 模板（由 `scripts/make_template.py` 生成）
- `scripts/`：模板生成、全部渲染、变异自证、MANIFEST 生成、一键复跑
- `tests/`：pytest 测试（AC 逐条对照）
- `samples/`：已渲染的样张（每份数据集各一份 Markdown、DOCX、PDF、图表与 PDF 首页截图）
- `evidence/`：渲染日志、测试日志、变异自证日志
- `MANIFEST.md`：交付文件清单与 SHA256

## 验收标准逐条对照

1. 样张 PDF 含 7 个章节且中文无乱码（截图）——`samples/*/report.pdf` 与
   `samples/*/page1.png`；测试 `test_pdf_has_seven_chapters_no_garbled` 用
   pdftotext 提取核对七章标题且无替换字符。
2. 从 DOCX 中解析出的全部数字都能在数据集中找到来源（测试断言）——
   测试 `test_all_docx_numbers_traceable_to_dataset` 对两份数据集逐一断言。
3. P0 失败数为 0 与不为 0 两种数据集分别渲染出对应文案（测试通过）——
   测试 `test_p0_zero_copy` / `test_p0_nonzero_copy`；样张见 `samples/` 下两份。
4. low_sample 行在表格中为灰色并带脚注（截图）——测试
   `test_low_sample_rows_grey_with_footnote` 核对整行灰色填充与脚注；
   灰色由 `render.py` 后处理写入单元格底纹，脚注在模板末尾。

## 变异自证

`scripts/mutation_proof.py` 改数据集重渲染，证明数字确实来自数据集：

- M1：通过率 96.5 改为 50.0，输出同步变为 50.0%
- M2：P0 失败数 0 改为 2，文案由“本月无 P0 失败”变为“本月 P0 失败数为 2 起”
- M3：low_sample 由真改为假，DOCX 置灰行数由 1 变为 0

日志见 `evidence/mutation_proof.log`。

## 对接点

- 本单无依赖；EVAL-041 的数据集与 EVAL-042 的归因结果接入时，只需按
  `data/dataset_p0_zero.json` 的字段结构替换输入文件，模板与渲染代码不用改。
