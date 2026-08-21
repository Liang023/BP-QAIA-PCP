"""强制在所属分区中使用指定顶点（分支定价）。

该分支决策保留分区内被选中的一个顶点，并移除同分区的其他顶点，
从而确保该分区在当前分支中仅使用该顶点对应的颜色。
"""
from model.vertex import Vertex
from bpc.branching.branching_decision import BranchingDecision
from model.a_graph import AuxiliaryGraph
from cg.column_pool import ColumnPool


class ImposedVertex(BranchingDecision):
    """分支决策：在分区内强制使用给定顶点。"""
    
    def __init__(self, vertex: Vertex):
        """使用需被强制的顶点进行初始化。"""
        self.vertex = vertex
        print(f"ImposedVertex(vertex={self.vertex.id})")
    
    def a_graph_update(self,a_graph:AuxiliaryGraph):
        """从辅助图中移除同分区的其他顶点。"""
        a_graph.remove_other_vertices_in_partition(self.vertex)
    
    def column_filter(self, column_pool: ColumnPool):
        """移除所有包含同分区其他顶点的列。"""
        columns_to_remove = []
        
        for column in column_pool.columns:
            if column.is_artificial_column:
                continue
            for v in self.vertex.associated_partition.vertex_list:
                if v != self.vertex and v in column.vertex_list:
                    columns_to_remove.append(column)
                    break
        
        for column in columns_to_remove:
            column_pool.removeColumn(column)
    
    def __str__(self):
        return f"ImposedVertex(vertex={self.vertex})"

    def __repr__(self):
        return f"ImposedVertex(vertex={self.vertex.id})"