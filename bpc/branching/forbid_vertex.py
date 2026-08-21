from bpc.branching.branching_decision import BranchingDecision
from model.vertex import Vertex
from model.a_graph import AuxiliaryGraph
from cg.column_pool import ColumnPool

class ForbidVertex(BranchingDecision):
    """分支决策：禁止（移除）指定顶点。

    将该顶点从辅助图中移除，并过滤掉所有包含该顶点的列（保留人工列）。
    """
    def __init__(self, vertex: Vertex):
        self.vertex = vertex
        print(f"ForbidVertex(vertex={self.vertex.id})")
        
    def a_graph_update(self,a_graph:AuxiliaryGraph):
        """在辅助图中移除该顶点。"""
        a_graph.remove_vertex(self.vertex)
    
    def column_filter(self,column_pool:ColumnPool):
        """移除所有包含该顶点的列。"""
        columns_to_remove = []
        for column in column_pool.columns:
            if column.is_artificial_column:
                continue
            if self.vertex in column.vertex_list:
                columns_to_remove.append(column)
        for column in columns_to_remove:
            column_pool.removeColumn(column)
    def __str__(self):
        return f"ForbidVertex(vertex={self.vertex.id})"

    def __repr__(self):
        return f"ForbidVertex(vertex={self.vertex.id})"