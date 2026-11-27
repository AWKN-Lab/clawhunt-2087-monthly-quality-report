"""图表：matplotlib 本地渲染 PNG，内置中文字体，不调用任何外部服务。"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

FONT = "Noto Serif CJK SC"


def _setup_font() -> None:
    try:
        font_manager.findfont(FONT, fallback_to_default=False)
    except Exception:
        return
    plt.rcParams["font.family"] = FONT
    plt.rcParams["axes.unicode_minus"] = False


_setup_font()


def render_trend_chart(weekly_rates, out_path: Path) -> Path:
    """通过率趋势图：横轴为周次，纵轴为通过率（百分点取自数据集原文）。"""
    weeks = [w["week"] for w in weekly_rates]
    rates = [w["rate"] for w in weekly_rates]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(weeks, rates, marker="o")
    ax.set_title("能力评测通过率趋势")
    ax.set_ylabel("通过率")
    ax.set_ylim(0, 100)
    for x, y in zip(weeks, rates):
        ax.annotate(str(y), (x, y))
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def render_reject_chart(reject_reasons, out_path: Path) -> Path:
    """拒绝原因分布图：横轴为原因，纵轴为次数（取自数据集原文）。"""
    reasons = [r["reason"] for r in reject_reasons]
    counts = [r["count"] for r in reject_reasons]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(reasons, counts)
    ax.set_title("拒绝原因分布")
    ax.set_ylabel("次数")
    for x, y in zip(reasons, counts):
        ax.annotate(str(y), (x, y))
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
