from typing import Tuple, Dict
from cg.column_pool import ColumnPool
from bpc.branching.branching_decision import BranchingDecision
from bpc.branching.imposed_vertex import ImposedVertex
from bpc.branching.forbid_vertex import ForbidVertex
from model.vertex import Vertex
from model.a_graph import AuxiliaryGraph
from bpc.branching.same_color import SameColor
from bpc.branching.different_color import DifferentColor

class BranchCreator:
    """分支创建器：根据当前解与图状态生成分支规则。

    规则1：在一个分区中若选择了多个顶点，选取该分区贡献值最大的顶点，
          创建“强制该顶点/禁止该顶点”的二叉分支。
    规则2：在不同分区的两顶点之间，若共同出现的分数值为非整数，
          对这两顶点创建“同色/异色”的二叉分支。
    """

    def __init__(self, solution: Dict[int, float], column_pool: ColumnPool, a_graph: AuxiliaryGraph):
        self.solution = solution
        self.column_pool = column_pool
        self.checked_vertex=None
        self.a_graph=a_graph

    def create_branch(self)->Tuple[BranchingDecision,BranchingDecision]:
        """根据规则依次尝试生成分支决策。"""
        if self.check_branch_rule1():
            return self.create_branch_rule1(self.checked_vertex)
        elif self.check_branch_rule2():
            return self.create_branch_rule2()
        else:
            return None
    
    def check_branch_rule1(self)->bool:
        """规则1检测：某分区被部分选中多个顶点时进行分支。

        计算每个分区当前被“上色”的顶点集合及其分数贡献，若某分区
        含多个顶点被选中，则选择贡献最大的顶点作为分支对象。
        """
        verteices_value={}
        vetices_num_colored_for_each_partition={}
        for column, value in self.solution.items():
            if value <= 1e-9:
                continue

            for vertex in column.vertex_list:
                # 跳过没有单一所属分区的合并顶点
                if not hasattr(vertex, "associated_partition"):
                    continue

                partition = vertex.associated_partition

                if partition not in vetices_num_colored_for_each_partition:
                    vetices_num_colored_for_each_partition[partition] = []

                if vertex not in \
                        vetices_num_colored_for_each_partition[partition]:
                    vetices_num_colored_for_each_partition[
                        partition
                    ].append(vertex)

                verteices_value[vertex] = (
                    verteices_value.get(vertex, 0.0) + value
                )
        if not vetices_num_colored_for_each_partition:
            return False       
        max_num_colored_partition=max(vetices_num_colored_for_each_partition.items(),key=lambda x:len(x[1]))
        
        if len(max_num_colored_partition[1])>1:
            max_value=0
            for vertex,value in verteices_value.items():
                if vertex not in max_num_colored_partition[0].vertex_list:
                    continue
                else:
                    if value>max_value:
                        max_value=value
                        self.checked_vertex=vertex
                    return True
        return False

    
    def create_branch_rule1(self,checked_vertex:Vertex)->Tuple[BranchingDecision,BranchingDecision]:
        """创建规则1的二叉分支：强制该顶点 / 禁止该顶点。"""
        return ImposedVertex(checked_vertex),ForbidVertex(checked_vertex)
    
    def check_branch_rule2(self)->bool:
        """规则2检测：跨分区两顶点的联合选择值为非整数时分支。"""
        max_fraction=0
        for vertex_v in self.a_graph.vertices_map.values():
            for vertex_u in self.a_graph.vertices_map.values():
                if vertex_v.associated_partition.id == vertex_u.associated_partition.id:
                    continue
                gamma=0
                for column in self.solution.keys():
                    if vertex_v in column.vertex_list and vertex_u in column.vertex_list:
                        gamma+=self.solution[column]
                if gamma != int(gamma) and gamma>max_fraction:  # Check if gamma is fractional
                    max_fraction=gamma
                    checked_vertex_v=vertex_v
                    checked_vertex_u=vertex_u
        if max_fraction>0:
            self.checked_vertex_v=checked_vertex_v
            self.checked_vertex_u=checked_vertex_u
            return True        
        return False
    
    def create_branch_rule2(self) -> Tuple[BranchingDecision, BranchingDecision]:
        """创建规则2的二叉分支：同色 / 异色。"""

        vertex_pair = (
            self.checked_vertex_v,
            self.checked_vertex_u
        )

        return (
            SameColor(vertex_pair),
            DifferentColor(vertex_pair)
        )