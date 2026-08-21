from bpc.branching.branching_decision import BranchingDecision
from model.vertex import Vertex
from model.a_graph import AuxiliaryGraph
from cg.column_pool import ColumnPool
from typing import Tuple


class DifferentColor(BranchingDecision):
    """分支决策：强制两顶点使用不同的颜色。

    该决策会更新辅助图，禁止这两个顶点使用同一颜色，并过滤掉所有
    违反该约束的列。
    """

    def __init__(self, vertex_pair: Tuple[Vertex, Vertex]):
        """使用需要强制不同颜色的一对顶点进行初始化。"""
        self.vertex_pair = vertex_pair
        print(f"DifferentColor(vertex_pair={self.vertex_pair[0].id}-{self.vertex_pair[1].id})")
        
    def a_graph_update(self, a_graph: AuxiliaryGraph):
        """在辅助图中应用该约束。"""
        a_graph.different_color(self.vertex_pair[0], self.vertex_pair[1])

    def column_filter(self, column_pool: ColumnPool):
        """移除将两顶点放入同一独立集的列。

        人工列将被保留，以维持主问题的可行性。
        """
        columns_to_remove = []
        
        for column in column_pool.columns:
            if column.is_artificial_column:
                continue
            if self.vertex_pair[0] in column.vertex_list and self.vertex_pair[1] in column.vertex_list:
                columns_to_remove.append(column)
        for column in columns_to_remove:
            column_pool.removeColumn(column)

    def __str__(self):
        return f"DifferentColor(vertex_pair={self.vertex_pair[0].id}-{self.vertex_pair[1].id})"

    def __repr__(self):
        return f"DifferentColor(vertex_pair={self.vertex_pair[0].id}-{self.vertex_pair[1].id})"