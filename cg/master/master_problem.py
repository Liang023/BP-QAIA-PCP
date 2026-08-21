from cg.pricing.pricing_problem import PricingProblem
from cg.column_pool import ColumnPool
import gurobipy as grb
from cg.column_independent_set import ColumnIndependentSet
import time
from model.a_graph import AuxiliaryGraph
from model.graph import Graph

class MasterProblem:
    """
    主问题（Restricted Master Problem, RMP）模型封装。

    - 负责构建"每个分区至少被染色一次"的约束；
    - 维护列（独立集）到变量的映射，并将新列增广到模型中；
    - 调用 Gurobi 求解并返回解、对偶信息以及当前目标值。
    
    EV 充电调度扩展：
    - 新增 makespan 变量 T，目标为 min T；
    - 每个顶点 v 对应一个 makespan 约束：sum_{col: v in col} t_v * x_col - T <= 0。
    - 充电桩数量限制约束：sum_{col} x_col <= charger_num
    """
    def __init__(
        self,
        graph: Graph,
        charger_num: int,
        pricing_problem: PricingProblem,
        column_pool: ColumnPool,
        a_graph: AuxiliaryGraph,
    ):
        self.graph = graph
        self.charger_num = charger_num
        self.pricing_problem = pricing_problem
        self.column_pool = column_pool
        self.a_graph = a_graph
        self._rmp = grb.Model("master")
        # key: 定价问题实例 → value: {列对象 → Gurobi变量}
        self.varMap = {}  # 存储定价问题到变量映射的字典
        # 对偶变量统一结构：
        # {
        #   'partition': {partition_id: dual},
        #   'makespan': {vertex_id: dual},
        #   'charger': λ  # 充电桩数量约束的对偶
        # }
        self.dual = {'partition': {}, 'makespan': {}, 'charger': 0.0}
        self.each_partition_colored_once_constraint = dict()
        # makespan 相关
        self.T = None  # makespan 变量
        self.vertex_makespan_constraints = {}  # vertex_id → makespan 约束
        # 充电桩数量约束：sum_col x_col <= charger_num
        self.charger_capacity_constraint = None
        self.solution = None
        self.objective = 0.0
        self.buildModel()

    def buildModel(self):
        """初始化求解参数并构建基础约束。"""
        self._rmp.Params.LogToConsole = 0
        self._rmp.Params.DualReductions = 0
        # 创建 makespan 变量 T，目标系数为 1（min T）
        self.T = self._rmp.addVar(lb=0.0, obj=1.0, vtype=grb.GRB.CONTINUOUS, name="T")
        self._build_constraints()
        # self._add_feasible_initial_columns(self.column_pool)

    def _add_feasible_initial_columns(self, column_pool: ColumnPool):
        """（可选）为模型添加一批初始可行列。"""
        for column in column_pool.columns:
            self.add_column_to_rmp(column)

    def add_column_to_rmp(self, column_independent_set: ColumnIndependentSet):
        """将表示"独立集"的列增广到 RMP 中并创建对应变量。
        
        通过 grb.Column 机制同时加入：
        1. 分区约束（系数 1）
        2. makespan 约束（系数 t_v = vertex.end_time）
        3. 充电桩数量约束（系数 1）
        """
        name = f"column_{column_independent_set.columnid}"

        c = grb.Column()
        for vertex in column_independent_set.vertex_list:
            if vertex not in self.a_graph.merged_vertices_map:
                # 加入分区约束
                partition_id = vertex.associated_partition.id
                constr = self.each_partition_colored_once_constraint[partition_id]
                c.addTerms(1.0, constr)
                # 加入 makespan 约束（如果该顶点有 makespan 约束）
                if vertex.id in self.vertex_makespan_constraints:
                    makespan_constr = self.vertex_makespan_constraints[vertex.id]
                    t_v = vertex.end_time
                    c.addTerms(-t_v, makespan_constr)
            else:
                merged_vertices = self.a_graph.merged_vertices_map[vertex]
                for merged_vertex in merged_vertices:
                    # 加入分区约束
                    partition_id = merged_vertex.associated_partition.id
                    constr = self.each_partition_colored_once_constraint[partition_id]
                    c.addTerms(1.0, constr)
                    # 加入 makespan 约束（如果该顶点有 makespan 约束）
                    if merged_vertex.id in self.vertex_makespan_constraints:
                        makespan_constr = self.vertex_makespan_constraints[merged_vertex.id]
                        t_v = merged_vertex.end_time
                        c.addTerms(-t_v, makespan_constr)

        # 充电桩数量约束：每个列变量在该约束中的系数为 1
        if self.charger_capacity_constraint is not None:
            c.addTerms(1.0, self.charger_capacity_constraint)

        # 列变量目标系数为 0（目标由 T 承担）
        var = self._rmp.addVar(
            lb=0.0,
            obj=column_independent_set.value,#人工列1000，非人工列0
            vtype=grb.GRB.CONTINUOUS,
            name=name,
            column=c,
        )

        # 确保定价问题的键存在
        if column_independent_set.associated_pricing_problem not in self.varMap:
            self.varMap[column_independent_set.associated_pricing_problem] = {}
        
        self.varMap[column_independent_set.associated_pricing_problem][column_independent_set] = var

    def _build_constraints(self):
        """构建基础约束骨架。
        
        1. 每个分区至少被染色一次的约束：sum_{col} a_{partition,col} * x_col >= 1
        2. 每个顶点的 makespan 约束：sum_{col: v in col}  T-t_v * x_col >= 0
           初始时左侧只有 -T，后续通过 grb.Column 机制加入 t_v * x_col 项。
        3. 全局充电桩数量约束：sum_col x_col <= charger_num
        """
        partition_number = len(self.graph.partitions)
        # 构建每个partition被染色一次的约束
        for partition_id in range(partition_number):
            lhs = grb.quicksum([])
            rhs = 1
            name = f"each_partition_colored_once_constraint{partition_id}"
            c = self._rmp.addConstr(lhs >= rhs, name=name)
            self.each_partition_colored_once_constraint[partition_id] = c
        
        # 构建每个顶点的 makespan 约束：T - sum_{col: v in col} t_v * x_col >= 0
        # 初始时只有 T >= 0，后续加列时通过 Column 机制添加 -t_v * x_col
        for vertex in self.graph.vertices:
            if hasattr(vertex, 'end_time') and vertex.end_time > 0:
                name = f"makespan_vertex_{vertex.id}"
                # 约束：1*T + (-t_v)*x_col + ... >= 0
                # 初始：1*T >= 0，后续通过 Column 添加 (-t_v)*x_col 项
                constr = self._rmp.addConstr(1.0 * self.T >= 0, name=name)
                self.vertex_makespan_constraints[vertex.id] = constr

        # 全局充电桩数量约束：sum_col x_col <= charger_num
        # 初始时左侧为空，后续通过 Column 机制为每个列变量添加系数 1
        name = "charger_capacity_constraint"
        lhs = grb.quicksum([])
        self.charger_capacity_constraint = self._rmp.addConstr(
            lhs <= self.charger_num, name=name
        )

    def solveMaster(self, time_end: int):
        """求解主问题并返回（解、对偶、目标值）。"""
        # 设置求解器参数
        self._rmp.Params.DualReductions = 0  # 禁用对偶约减

        # 提高求解精度
        self._rmp.Params.OptimalityTol = 1e-9
        self._rmp.Params.FeasibilityTol = 1e-9
        self._rmp.Params.BarConvTol = 1e-9

        # 强制使用数值稳定的求解方法
        self._rmp.Params.Method = 1  # 强制使用对偶单纯形法（更稳定）
        # # 或者
        # self.model.Params.Method = 2  # 内点法（更适合病态问题）

        # 设置时间限制
        time_limit = time_end - time.time()
        self._rmp.Params.TimeLimit = time_limit

        self._rmp.update()

        # 在优化前导出模型（调试/排错用）
        self._rmp.write("model_info/master.lp")

        try:
            self._rmp.setObjective(self._rmp.getObjective(), grb.GRB.MINIMIZE)
            self._rmp.optimize()
        except grb.GurobiError as e:
            # 将求解器异常直接抛出
            raise e

        # 根据求解状态处理结果
        if self._rmp.status == grb.GRB.OPTIMAL:
            # 获取解
            self.solution = {}
            for pricing_problem, var_dict in self.varMap.items():
                for col, var in var_dict.items():
                    if var.X > 1e-6:  # 只保存非零解
                        self.solution[col] = var.X
            # 获取对偶变量（假设约束顺序与添加顺序一致）
            self._get_dual_variables()

            return self.solution, self.dual, self._rmp.ObjVal
        elif self._rmp.status == grb.GRB.INFEASIBLE:
            raise grb.GurobiError(grb.GRB.INFEASIBLE, "Master problem is infeasible")
        elif self._rmp.status == grb.GRB.INF_OR_UNBD:
            raise grb.GurobiError(
                grb.GRB.INF_OR_UNBD, "Master problem is infeasible or unbounded"
            )
        elif self._rmp.status == grb.GRB.UNBOUNDED:
            raise grb.GurobiError(grb.GRB.UNBOUNDED, "Master problem is unbounded")
        elif self._rmp.status == grb.GRB.TIME_LIMIT:
            # 时间限制达到但未找到最优解
            if self._rmp.SolCount > 0:  # 有可行解
                self.solution = {}
                for pricing_problem, var_dict in self.varMap.items():
                    for col_id, var in var_dict.items():
                        if var.X > 1e-6:  # 只保存非零解
                            self.solution[col_id] = var.X
                self._get_dual_variables()
                return self.solution, self.dual, self._rmp.ObjVal
            else:
                raise grb.GurobiError(
                    grb.GRB.TIME_LIMIT, "Time limit reached without solution"
                )
        else:
            # 其他未处理状态
            status_name = self._rmp.status
            raise RuntimeError(f"Master problem solve failed with status {status_name}")

    def _get_dual_variables(self):
        """提取对偶变量值到统一结构 self.dual。
        
        self.dual = {
            'partition': {partition_id: π, ...},  # 分区约束对偶，用于定价问题顶点权重
            'makespan': {vertex_id: μ, ...},      # makespan 约束对偶，用于定价问题时间惩罚
            'charger': λ                          # 充电桩数量约束的对偶
        }
        """
        # 分区约束对偶
        partition_duals = {}
        for partition_id in range(len(self.graph.partitions)):
            partition_duals[partition_id] = self.each_partition_colored_once_constraint[partition_id].Pi
        
        # makespan 约束对偶
        makespan_duals = {}
        for vertex_id, constr in self.vertex_makespan_constraints.items():
            makespan_duals[vertex_id] = constr.Pi

        # 充电桩数量约束对偶
        charger_dual = 0.0
        if self.charger_capacity_constraint is not None:
            charger_dual = self.charger_capacity_constraint.Pi
        
        self.dual = {
            'partition': partition_duals,
            'makespan': makespan_duals,
            'charger': charger_dual,
        }
