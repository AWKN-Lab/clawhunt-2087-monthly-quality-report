"""S5-EVAL-043 质量月报模板渲染（最小可验证样品）。

只用虚构测试数据；报告中的全部数字由程序从数据集填入，模板里不得出现手写数字。
渲染过程不调用任何 AI 模型；图表用 matplotlib 本地渲染 PNG。
"""

from .render import load_dataset, render_all

__all__ = ["load_dataset", "render_all"]
