"""生成 MANIFEST.md：交付文件清单 + SHA256，供验收方逐字节核对。"""

from __future__ import annotations

import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
SKIP_FILES = {"MANIFEST.md"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rows: list[tuple[str, int, str]] = []
    for path in sorted(REPO.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(REPO).parts):
            continue
        if path.name in SKIP_FILES:
            continue
        rel = str(path.relative_to(REPO))
        rows.append((rel, path.stat().st_size, _sha256(path)))
    lines = ["# MANIFEST", "", "交付文件清单（SHA256 逐字节核对用）。", "", "| 文件 | 大小（字节） | SHA256 |", "| --- | --- | --- |"]
    for rel, size, digest in rows:
        lines.append("| %s | %d | %s |" % (rel, size, digest))
    lines.append("")
    lines.append("共 %d 个文件。" % len(rows))
    (REPO / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("manifest written: %d files" % len(rows))


if __name__ == "__main__":
    main()
