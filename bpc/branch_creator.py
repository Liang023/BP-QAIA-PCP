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

    def _get_partition_ids(self, vertex):
        """取得普通顶点或合并顶点代表的全部分区ID。"""

        original_vertices = (
            self.a_graph.get_original_vertices(vertex)
        )

        return {
            original_vertex.associated_partition.id
            for original_vertex in original_vertices
        }


    def _column_contains_vertex(self, column, vertex):
        """
        判断一列是否包含某个活动顶点。

        对合并顶点，要求该列包含其代表的全部原始顶点。
        """
        required_vertices = {
            original_vertex.id
            for original_vertex
            in self.a_graph.get_original_vertices(vertex)
        }

        column_original_vertices = set()

        for column_vertex in column.vertex_list:
            originals = self.a_graph.get_original_vertices(
                column_vertex
            )

            column_original_vertices.update(
                original_vertex.id
                for original_vertex in originals
            )

        return required_vertices.issubset(
            column_original_vertices
        )

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
    
    def check_branch_rule2(self) -> bool:
        """
        规则2：寻找联合选择值为分数的两个活动顶点。

        普通顶点使用一个分区；
        合并顶点使用其全部原始顶点对应的分区集合。
        """
        best_fractionality = 0.0
        checked_pair = None

        active_vertices = list(
            self.a_graph.vertices_map.values()
        )

        for index, vertex_v in enumerate(active_vertices):
            partition_ids_v = self._get_partition_ids(vertex_v)

            for vertex_u in active_vertices[index + 1:]:
                partition_ids_u = self._get_partition_ids(vertex_u)

                # 包含相同原始分区的两个活动顶点不能再做同色分支
                if partition_ids_v.intersection(partition_ids_u):
                    continue

                gamma = 0.0

                for column, column_value in self.solution.items():
                    contains_v = self._column_contains_vertex(
                        column,
                        vertex_v
                    )
                    contains_u = self._column_contains_vertex(
                        column,
                        vertex_u
                    )

                    if contains_v and contains_u:
                        gamma += column_value

                fractionality = abs(
                    gamma - round(gamma)
                )

                if fractionality > best_fractionality + 1e-8:
                    best_fractionality = fractionality
                    checked_pair = (vertex_v, vertex_u)

        if checked_pair is None:
            return False

        self.checked_vertex_v = checked_pair[0]
        self.checked_vertex_u = checked_pair[1]

        print(
            f"规则2分支: "
            f"vertices={self.checked_vertex_v.id}-"
            f"{self.checked_vertex_u.id}, "
            f"fractionality={best_fractionality:.6f}"
        )

        return True
    
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