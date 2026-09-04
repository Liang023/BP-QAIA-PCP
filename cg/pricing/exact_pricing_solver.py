from cg.column_independent_set import ColumnIndependentSet
from cg.pricing.pricing_problem import PricingProblem
from bpc.branching.branching_decision import BranchingDecision
import gurobipy as grb
from typing import Dict
from model.a_graph import AuxiliaryGraph
import time
import os

class ExactPricingSolver:
    """
    精确定价求解器：基于当前辅助图与对偶信息，求解带冲突约束的最大权稳定集，
    以此生成 reduced cost 为负的列（独立集）。

    - build_model: 搭建子问题模型（二进制变量、冲突约束、目标）。
    - set_objective/solve: 设置目标并调用 Gurobi 求解（支持解池）。
    - generate_columns: 从解池提取解，构造列，并可在调试模式下校验 reduced cost。
    """
    solution = None

    def __init__(
        self, auxiliary_graph: AuxiliaryGraph, pricing_problem: PricingProblem
    ):
        self.pricing_problem = pricing_problem
        self.auxiliary_graph = auxiliary_graph
        self.model = grb.Model("sub")
        self.vars: Dict[int, grb.Var] = {}
        self.cons = {}
        self.pool_sol_num = 10
        self.build_model()
        self.dual = pricing_problem.dual
        # 调试模式：设置环境变量 BPC_DEBUG=1 启用断言校验
        self.debug = bool(int(os.getenv("BPC_DEBUG", "0")))

    def build_model(self):
        # 检查辅助图数据是否一致
        missing_weight_ids = [
            vertex.id
            for vertex in self.auxiliary_graph.vertices_map.values()
            if vertex.id not in self.auxiliary_graph.weight_v
        ]

        if missing_weight_ids:
            raise RuntimeError(
                "辅助图中的顶点缺少定价权重："
                f"{missing_weight_ids}"
            )

        # 创建决策变量
        for v in self.auxiliary_graph.vertices_map.values():
            self.vars[v.id] = self.model.addVar(
                vtype=grb.GRB.BINARY,
                name=f"x_{v.id}"
            )

        # 冲突约束
        for edge in self.auxiliary_graph.auxiliary_edges:
            u = edge.source
            v = edge.target

            self.cons[(u.id, v.id)] = self.model.addConstr(
                self.vars[u.id] + self.vars[v.id] <= 1,
                name=f"cons_({u.id},{v.id})"
            )

        # 初始目标函数
        obj_expr = grb.LinExpr()

        obj_expr += sum(
            self.auxiliary_graph.weight_v[v.id] * self.vars[v.id]
            for v in self.auxiliary_graph.vertices_map.values()
        )

        self.model.setObjective(
            1 - obj_expr,
            grb.GRB.MINIMIZE
        )

    def solve(self,time_end:int):
        """求解子问题：启用解池并设置时间限制。

        Args:
            time_end: 统一的结束时间戳（与主控共享），用于计算剩余时间。
        """
        # 设置 model 参数：使用解池存储多个可行解
        self.model.setParam("PoolSearchMode", 2)  # 系统搜索多个解
        self.model.setParam("PoolSolutions", self.pool_sol_num)  # 最大存储解数量

        # 设置求解器参数
        self.model.setParam("OutputFlag", 0)  # 关闭求解器输出
        time_limit = time_end - time.time()
        self.model.setParam("TimeLimit", time_limit)  # 30秒时间限制

        self.model.update()
        # 求解
        self.model.optimize()

    def set_objective(self):
        """将子问题目标切换为最大化 Σw_v x_v（便于从解池读取）。"""
        obj_expr = grb.LinExpr()
        obj_expr += sum(
            self.auxiliary_graph.weight_v[v.id] * self.vars[v.id]
            for v in self.auxiliary_graph.vertices_map.values()
        )
        self.model.setObjective(obj_expr, grb.GRB.MAXIMIZE)

    def generate_columns(self,time_end:int):
        """生成列：从解池提取可用解并构造独立集列。

        仅保留满足 reduced cost 条件的列；在调试模式下，断言校验子问题
        报告的 reduced cost 与手动计算一致。
        """
        self._update_dual()
        # 设置目标函数
        self.set_objective()

        # 构建和求解子问题
        self.solve(time_end)

        # 处理解池中的解，获取 reduced cost < 0 的多个可行列
        columns = []

        # 检查是否有解
        if self.model.Status != grb.GRB.OPTIMAL and self.model.SolCount == 0:
            raise RuntimeError(
                "Exact Pricing没有获得可行解，也没有取得最优性证明。"
                f"Gurobi status={self.model.Status}"
            )

        # 获取解池中的解数量
        solution_num = self.model.SolCount

        # 遍历解池中所有解
        for i in range(solution_num):
            # 设置当前解的索引
            self.model.setParam(grb.GRB.Param.SolutionNumber, i)

            # 获取当前解的目标值
            obj_val = self.model.PoolObjVal

            # 只考虑 reduced cost < 0 的解（等价于目标值充足大）
            rc=obj_val+self.dual.get('charger', 0.0)
            # print(f"rc: {rc}")
            if rc < 1e-6:  # 考虑数值误差
                continue

            # 提取稳定集（值为1的节点）
            stable_set_list = []
            for v, var in self.vars.items():
                if abs(var.Xn - 1.0) < 1e-6:  # 检查是否为1
                    stable_set_list.append(self.auxiliary_graph.vertices_map[v])

            # 创建列对象
            new_column = ColumnIndependentSet(
                vertex_list=stable_set_list,
                value=0,
                associated_pricing_problem=self.pricing_problem,
                is_artificial=False,
                creator="Exact Pricing Solver",
            )

            columns.append(new_column)

            # 断言校验：将校验逻辑与主流程解耦
            self._assert_reduced_cost_consistency(rc, new_column)

        if len(columns) == 0 and self.model.Status != grb.GRB.OPTIMAL:
            raise RuntimeError(
                "Exact Pricing没有生成改进列，但求解状态不是OPTIMAL，"
                f"Gurobi status={self.model.Status}"
            )
        
        return columns
    def _update_dual(self):
        """从定价问题对象中同步对偶值。"""
        self.dual = self.pricing_problem.dual
    def _calculate_reduced_cost(self, column: ColumnIndependentSet) -> float:
        """
        手动计算 reduced cost
        
        reduced cost = 目标系数 - 分区对偶贡献 + makespan对偶贡献 + 充电桩约束对偶贡献
        对于 EV 问题：rc = 0 - (Σπ_p + Σμ_v * t_v - λ)
        """
        dual_contrib = 0.0

        # 全局充电桩数量约束对偶：每个列的系数为 1
        charger_dual = self.dual.get('charger', 0.0)
        dual_contrib += charger_dual
        for v in column.vertex_list:
            vertex = self.auxiliary_graph.vertices_map[v.id]
            # 分区对偶贡献
            partition_id = vertex.associated_partition.id
            dual_contrib += self.dual['partition'].get(partition_id, 0.0)
            # makespan 对偶贡献（如果有）
            if vertex.id in self.dual.get('makespan', {}) and hasattr(vertex, 'end_time'):
                dual_contrib -= self.dual['makespan'][vertex.id] * vertex.end_time
        
        # 列变量目标系数为 0，reduced cost = 0 - dual_contrib = -dual_contrib
        rc = dual_contrib
        
        return rc

    def _assert_reduced_cost_consistency(self, pool_obj_val: float, column: ColumnIndependentSet) -> None:
        """断言子问题报告的 reduced cost 与手动计算一致。

        Args:
            pool_obj_val: 解池中该列对应的目标值
            column: 列（独立集）对象
        """
        if not self.debug:
            return
        self._update_dual()
        manual_rc = self._calculate_reduced_cost(column)
        diff = abs(pool_obj_val - manual_rc)
        assert diff <= 1e-5, (
            f"Reduced cost 不一致: "
            f"子问题报告={pool_obj_val:.6f}, "
            f"手动计算={manual_rc:.6f}, "
            f"差异={diff:.6f}"
        )

    def branchPerformed(self, branchingDecision: BranchingDecision):
        pass

    def branchReversed(self, branchingDecision: BranchingDecision):
        pass

    def get_solution(self):
        return self.solution
