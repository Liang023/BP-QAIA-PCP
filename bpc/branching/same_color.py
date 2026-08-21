from bpc.branching.branching_decision import BranchingDecision
from model.vertex import Vertex
from model.a_graph import AuxiliaryGraph
from cg.column_pool import ColumnPool
from typing import Tuple



class SameColor(BranchingDecision):
    """分支决策：强制两顶点使用相同的颜色。

    更新辅助图以绑定两顶点同色，并移除与之冲突的列。
    """
    def __init__(self, vertex_pair: Tuple[Vertex, Vertex]):
        """使用需要同色的一对顶点进行初始化。"""
        self.vertex_pair = vertex_pair
        print(f"SameColor(vertex_pair={self.vertex_pair[0].id}-{self.vertex_pair[1].id})")

    def a_graph_update(self,a_graph:AuxiliaryGraph):
        """在辅助图中创建一个新的合并顶点来代表这两个顶点。"""
        a_graph.same_color(self.vertex_pair[0], self.vertex_pair[1])

    def column_filter(self, column_pool: ColumnPool):
        """移除只包含二者之一的列（与同色约束冲突）。"""
        columns_to_remove = []
        
        for column in column_pool.columns:
            if column.is_artificial_column:
                continue
            if self.vertex_pair[0] in column.vertex_list and self.vertex_pair[1] not in column.vertex_list:
                columns_to_remove.append(column)
            elif  self.vertex_pair[0] not in column.vertex_list and self.vertex_pair[1] in column.vertex_list:
                columns_to_remove.append(column)
        for column in columns_to_remove:
            column_pool.removeColumn(column)
                
    def __str__(self):
        return f"SameColor(vertex_pair={self.vertex_pair[0].id}-{self.vertex_pair[1].id})"

    def __repr__(self):
        return f"SameColor(vertex_pair={self.vertex_pair[0].id}-{self.vertex_pair[1].id})"