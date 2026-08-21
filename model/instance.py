"""
问题算例封装：用于统一管理 PCP 图与 EV 充电桩数量等元信息。

目前主要用于：
- 从 PCP 文件读入 Graph；
- 按简单规则派生充电桩数量 charger_num；
- 在分支定价入口处传递一个整体的 Instance，而不是散乱的参数。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from model.graph import Graph


@dataclass
class Instance:
    """统一封装一个 PCP / EV 算例。"""
    
    def __init__(self, graph: Graph, charger_num: int, name: Optional[str] = None):
        self.graph = graph
        self.charger_num = charger_num
        self.name = name

    def __str__(self) -> str:
        return (
            f"Instance(name={self.name}, "
            f"|V|={len(self.graph.vertices)}, "
            f"|E|={len(self.graph.edges)}, "
            f"|P|={len(self.graph.partitions)}, "
            f"chargers={self.charger_num})"
        )

    __repr__ = __str__


