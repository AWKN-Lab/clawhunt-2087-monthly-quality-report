#!/usr/bin/env bash
# 一键复跑：建 venv → 装依赖 → 生成模板 → 渲染全部样张 → 跑测试 → 变异自证 → 生成 MANIFEST
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python scripts/make_template.py
.venv/bin/python scripts/render_all.py
mkdir -p evidence
.venv/bin/python -m pytest -q 2>&1 | tee evidence/pytest.log
.venv/bin/python scripts/mutation_proof.py 2>&1 | tee evidence/mutation_proof.log
.venv/bin/python scripts/make_manifest.py
echo "ALL DONE"
