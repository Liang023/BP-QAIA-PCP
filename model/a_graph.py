"""
辅助图类 - 用于分支定价算法中的列生成
"""
from typing import List, Dict, Optional
from model.edge import Edge
from model.vertex import Vertex
from model.graph import Graph


class AuxiliaryGraph:
    """
    辅助图类
    
    在分支定价算法中，辅助图用于定价问题的求解。
    它在原图的基础上添加了同分区内顶点间的边，确保每个分区最多选择一个顶点。
    支持两类关键操作：
    - same_color: 合并顶点，使其在模型中共享同一颜色/选择状态；
    - different_color: 在两顶点间添加边，禁止同时选择。
    """
    
    def __init__(self, 
                 graph: Graph, 
                 vertices_map: Dict[int, Vertex],
                 auxiliary_edges: Optional[List[Edge]] = None,
                 merged_vertices_map: Optional[Dict[Vertex, List[Vertex]]] = None):
        """
        初始化辅助图
        
        Args:
            graph: 原始图对象
            vertices_map: 顶点ID到顶点对象的映射
            auxiliary_edges: 辅助边列表，如果为None则自动生成
            merged_vertices_map: 合并顶点映射，用于分支操作
        """
        self.graph = graph

        if merged_vertices_map is None:
            self.merged_vertices_map = {}
        else:
            self.merged_vertices_map = merged_vertices_map
        
        self.vertices_map = vertices_map.copy()
        
        if auxiliary_edges is None:
            self.auxiliary_edges = graph.edges.copy()
            self._get_auxiliary_edges()
        else:
            self.auxiliary_edges = auxiliary_edges
        # 初始化权重字典，使用顶点ID作为键
        self.weight_v = {v.id: 0.0 for v in vertices_map.values()}

    def _get_auxiliary_edges(self):
        """
        生成辅助边（同一分区内顶点间的边）
        
        在PCP问题中，同一分区内的顶点不能同时被选择，
        因此需要在它们之间添加边来表示这种约束。
        """
        vertex_list = list(self.vertices_map.values())
        for i in range(len(vertex_list)):
            for j in range(i + 1, len(vertex_list)):
                vertex_i = vertex_list[i]
                vertex_j = vertex_list[j]
                
                if vertex_i.associated_partition.id == vertex_j.associated_partition.id:
                    aux_edge = Edge(vertex_i, vertex_j)
                    # 检查是否已存在该边
                    if not any(e.source == vertex_i and e.target == vertex_j or 
                              e.source == vertex_j and e.target == vertex_i 
                              for e in self.auxiliary_edges):
                        self.auxiliary_edges.append(aux_edge)
    
    def get_auxiliary_edges(self) -> List[Edge]:
        """
        获取辅助边列表
        
        Returns:
            辅助边列表
        """
        return self.auxiliary_edges
    
    def update_weightf(self, dual: Dict):
        """
        更新顶点权重
        
        根据主问题的对偶变量更新顶点权重，用于定价问题的目标函数。
        权重 = π_partition - μ_v * t_v（如果有 makespan 约束）
        普通顶点直接计算；合并顶点使用其包含的所有原始顶点权重之和。
        
        Args:
            dual: 主问题的对偶变量字典 {'partition': {...}, 'makespan': {...}, 'charger': λ}
        """
        # 预取对偶字典，避免 KeyError
        partition_duals = dual.get('partition', {})
        makespan_duals = dual.get('makespan', {})

        # 更新普通顶点的权重
        for vertex in self.graph.vertices:
            pi = partition_duals.get(vertex.associated_partition.id, 0.0)
            mu = makespan_duals.get(vertex.id, 0.0)
            t_v = getattr(vertex, 'end_time', 0.0)
            self.weight_v[vertex.id] = pi - mu * t_v
            
        # 更新合并顶点的权重
        for vertex in self.merged_vertices_map.keys():
            self.weight_v[vertex.id] = sum(
                self.weight_v[merged_vertex.id] 
                for merged_vertex in self.merged_vertices_map[vertex]
            )
    
    def remove_other_vertices_in_partition(self, vertex: Vertex):
        """
        移除同分区中的其他顶点
        
        当强制选择某个顶点时，需要移除同分区中的其他顶点，
        确保该分区只能使用这一个顶点的颜色。
        
        Args:
            vertex: 被保留的顶点
        """
        removed_vertices = []
        
        if vertex in self.merged_vertices_map.keys():
            # 如果是合并顶点，移除不在合并集合中的其他顶点
            for v in self.graph.partitions[vertex.associated_partition.id].vertex_list:
                if v not in self.merged_vertices_map[vertex]:
                    removed_vertices.append(v)
        else:
            # 普通顶点，移除同分区的其他所有顶点
            for v in self.graph.partitions[vertex.associated_partition.id].vertex_list:
                if v != vertex:
                    removed_vertices.append(v)
        
        # 批量移除顶点
        for v in removed_vertices:
            self.remove_vertex(v)
            
    def remove_vertex(self, vertex: Vertex):
        """
        从辅助图中移除指定顶点
        
        移除顶点及其相关的所有边和权重信息。
        若为合并顶点，则移除其包含的所有原始顶点及相关边。
        
        Args:
            vertex: 要移除的顶点
        """
        if vertex in self.merged_vertices_map.keys():
            # 移除合并顶点及其包含的所有顶点
            for v in self.merged_vertices_map[vertex]:
                if v.id in self.vertices_map:
                    del self.vertices_map[v.id]
                if v.id in self.weight_v:
                    del self.weight_v[v.id]
                self.auxiliary_edges = [
                    e for e in self.auxiliary_edges 
                    if e.source != v and e.target != v
                ]
            # 移除合并顶点本身
            del self.merged_vertices_map[vertex]
        else:
            # 移除普通顶点
            if vertex.id in self.vertices_map:
                del self.vertices_map[vertex.id]
            if vertex.id in self.weight_v:
                del self.weight_v[vertex.id]
            self.auxiliary_edges = [
                e for e in self.auxiliary_edges 
                if e.source != vertex and e.target != vertex
            ]
            # print(len(self.vertices_map), sorted(self.vertices_map.keys()))
    def same_color(self, vertex_v: Vertex, vertex_u: Vertex):
        """
        强制两个顶点使用相同颜色
        
        创建一个新的合并顶点来代表这两个顶点，并更新所有相关的边。
        新的合并顶点会记录其包含的原始顶点，供后续操作（如权重、移除）使用。
        
        Args:
            vertex_v: 第一个顶点
            vertex_u: 第二个顶点
        """
        # 创建新的合并顶点
        end_time=max(vertex_v.end_time, vertex_u.end_time)
        vertex_z = Vertex(end_time)
        self.vertices_map[vertex_z.id] = vertex_z
        
        # 更新所有边，将涉及到这两个顶点的边都指向新顶点
        for edge in self.auxiliary_edges:
            if edge.source == vertex_v or edge.source == vertex_u:
                edge.source = vertex_z
            if edge.target == vertex_v or edge.target == vertex_u:
                edge.target = vertex_z
        
        # 移除原来的两个顶点
        self.remove_vertex(vertex_v)
        self.remove_vertex(vertex_u)
        
        # 在合并映射中记录这个操作
        if vertex_z not in self.merged_vertices_map:
            self.merged_vertices_map[vertex_z] = []
        self.merged_vertices_map[vertex_z].extend([vertex_v, vertex_u])
        
    def different_color(self, vertex_v: Vertex, vertex_u: Vertex):
        """
        强制两个顶点使用不同颜色
        
        在两个顶点之间添加边，确保它们不能同时被选择。
        
        Args:
            vertex_v: 第一个顶点
            vertex_u: 第二个顶点
        """
        # 在两个顶点之间添加边
        new_edge = Edge(vertex_v, vertex_u)
        
        # 检查是否已存在该边
        edge_exists = any(
            (e.source == vertex_v and e.target == vertex_u) or 
            (e.source == vertex_u and e.target == vertex_v)
            for e in self.auxiliary_edges
        )
        
        if not edge_exists:
            self.auxiliary_edges.append(new_edge)
    
    def copy(self):
        copied_edges = [
            Edge(edge.source, edge.target)
            for edge in self.auxiliary_edges
        ]

        copied_merged_vertices_map = {
            merged_vertex: list(original_vertices)
            for merged_vertex, original_vertices
            in self.merged_vertices_map.items()
        }

        copied_graph = AuxiliaryGraph(
            graph=self.graph,
            vertices_map=self.vertices_map.copy(),
            auxiliary_edges=copied_edges,
            merged_vertices_map=copied_merged_vertices_map
        )

        copied_graph.weight_v = self.weight_v.copy()

        return copied_graph