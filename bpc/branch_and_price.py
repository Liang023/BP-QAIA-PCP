"""
分支定价算法主类
"""
import heapq
import copy
from cg.anytime import IncumbentRecorder
from cg.master.restricted_integer_master import solve_restricted_mip
from typing import List, Optional, Dict, Any, Set
from model.a_graph import AuxiliaryGraph
from bpc.bpc_node import BPCNode
from cg.column_generation import ColumnGeneration
from cg.pricing.pricing_problem import PricingProblem
from cg.pricing.exact_pricing_solver import ExactPricingSolver
from cg.master.master_problem import MasterProblem
from bpc.branch_creator import BranchCreator
from cg.column_independent_set import ColumnIndependentSet
from model.graph import Graph
from cg.column_pool import ColumnPool
from cg.primal_completion import complete_root_pool
import math
import gurobipy
import os
from cg.pricing.qaia_exact_pricing_solver import QAIAExactPricingSolver
from config.qaia_runtime import pricing_options
from cg.deadline import remaining_seconds
from cg.makespan_bounds import capacity_bound
from validation.ev_solution import validate_schedule
import builtins
from cg import budget_clock

def print(*args, **kwargs):
    # 仅覆盖本模块中的print，不改全局builtins.print。
    if os.getenv("BPC_VERBOSE", "0") == "1":
        builtins.print(*args, **kwargs)

class BoundClosed(Exception):
    """A validated incumbent meets a globally valid lower bound."""


class CapacityInfeasible(Exception):
    """Required work exceeds all available candidate completion horizons."""


class BranchAndPrice:
    """
    分支定价算法实现
    
    使用优先队列管理分支节点，按照目标值（下界）从小到大处理节点。
    这样可以优先处理最有希望的节点，提高算法效率。
    """
    
    def __init__(self, graph: Graph, charger_num:int, time_limit: int, use_qaia: bool = True, qaia_seed: int = 42):
        """
        初始化分支定价算法
        
        Args:
            graph: 原始图对象
            charger_num: 充电桩数量
            time_limit: 时间限制（秒）
            use_qaia: 是否使用 QAIA 加速定价求解器（默认 True）
        """
        self.graph = graph
        self.problem_lower_bound = self._compute_problem_lower_bound()
        self.capacity_bound_info = None
        self.proof_source = None
        self.charger_num = charger_num
        self.time_limit = time_limit
        self.use_qaia = use_qaia
        self.qaia_seed = int(qaia_seed)
        self.best_schedule = None   
        self.best_schedule_makespan = None
        
        # 使用最小堆作为优先队列，按objective_value排序
        self.node_queue: List[BPCNode] = []
        
        # 算法状态跟踪
        self.best_solution: Optional[Dict[str, Any]] = None
        self.best_objective: float = float('inf')  # 上界
        self.global_lower_bound: float = float('-inf')  # 全局下界
        self.optimal: bool = False
        self.current_node: Optional[BPCNode] = None
        # 统计信息
        self.nodes_processed: int = 0
        self.nodes_created: int = 0
        self.nodes_pruned: int = 0
        self.total_solve_time: float = 0.0
        
        # 定价阶段统计
        self.total_pricing_time: float = 0.0
        self.total_qaia_time: float = 0.0
        self.total_hybrid_exact_time: float = 0.0

        self.total_qaia_calls: int = 0
        self.total_hybrid_exact_calls: int = 0
        self.qaia_nodes: int = 0
        self.exact_only_nodes: int = 0

        self.total_master_time = 0.0
        self.total_node_setup_time = 0.0
        self.root_initialization_seconds = 0.0
        self.root_diagnostics = None
        self.total_branch_time = 0.0
        self.recorder = None
        self.deadline = None
        self.rmp_mip_seconds = 0.0
        self.rmp_mip_calls = 0
        self.primal_enabled = os.getenv("BPC_PRIMAL_COMPLETION", "0") == "1"
        self.primal_attempts = int(os.getenv("BPC_PRIMAL_ATTEMPTS", "20"))
        self.primal_slice = float(os.getenv("BPC_PRIMAL_SECONDS", "2"))
        self.primal_metrics = dict(calls=0, attempts=0, columns_added=0,
                                  complete_schedules=0, improvements=0, seconds=0.0,
                                  seeded_from_incumbent=0)
        self.incumbent_input_creators = []
        self.rmp_mip_enabled = os.getenv("BPC_RMP_MIP", "1") == "1"
        self.rmp_mip_every = int(os.getenv("BPC_RMP_MIP_EVERY", "20"))
        self.rmp_mip_slice = float(os.getenv("BPC_RMP_MIP_SECONDS", "0.5"))
        self.rmp_mip_fraction = float(os.getenv("BPC_RMP_MIP_FRACTION", "0.1"))
        if (self.rmp_mip_every <= 0 or not math.isfinite(self.rmp_mip_slice)
                or self.rmp_mip_slice <= 0 or not 0 <= self.rmp_mip_fraction <= 1):
            raise ValueError("invalid restricted MIP settings")

    def solve(self, *, start_time=None, deadline=None, recorder=None) -> Dict[str, Any]:
        """Global budget starts before graph conversion in run_instance."""
        start_time = budget_clock.now() if start_time is None else float(start_time)
        time_end = start_time + self.time_limit if deadline is None else float(deadline)
        if not (math.isfinite(start_time) and math.isfinite(time_end) and time_end > start_time):
            raise ValueError("invalid BP deadline")
        self.deadline = time_end
        self.recorder = recorder or IncumbentRecorder(start_time, time_end)
        if abs(self.recorder.deadline-time_end) > 1e-6:
            raise ValueError("recorder and BP must share a deadline")
        status, error = "no_solution", None
        try:
            if os.getenv("BPC_CAPACITY_BOUND", "1") == "1":
                lp_seconds = float(os.getenv("BPC_BOUND_LP_SECONDS", "2"))
                if not math.isfinite(lp_seconds) or lp_seconds < 0:
                    raise ValueError("BPC_BOUND_LP_SECONDS must be finite and nonnegative")
                self.capacity_bound_info = capacity_bound(
                    self.graph, self.charger_num, time_end, lp_seconds)
                self.problem_lower_bound = max(self.problem_lower_bound,
                                               self.capacity_bound_info["lower_bound"])
                if self.capacity_bound_info["lp_status"] == "capacity_infeasible":
                    raise CapacityInfeasible()
            remaining_seconds(time_end, "Before root construction")
            started = budget_clock.now()
            try:
                root = self.generate_root_node()
            finally:
                self.root_initialization_seconds = budget_clock.now() - started
            self.add_node(root)
            remaining_seconds(time_end, "After root construction")
            # Register existing greedy columns if they already form a full schedule.
            initial = {c: 1.0 for c in root.column_pool.columns if not c.is_artificial_column}
            if initial and len(initial) <= self.charger_num:
                upper = max(v.end_time for c in initial for v in c.vertex_list)
                self.update_best_solution(upper, initial, a_graph=root.a_graph,
                                          source="initial", node_id=root.nodeid)
            while not self.is_queue_empty():
                self.current_node = self.get_next_node()
                remaining_seconds(time_end, "Before processing node")
                self.nodes_processed += 1
                if self.is_prunable_node(self.current_node):
                    continue
                self.process_node(self.current_node, time_end)
                remaining_seconds(time_end, "After node certification")
                if self.is_prunable_node(self.current_node):
                    continue
                if self.is_infeasible_solution(self.current_node):
                    # A finite artificial penalty is NOT a general infeasibility proof.
                    # Preserve incumbents, stop conservatively instead of false optimal.
                    raise RuntimeError("Artificial columns remain after CG; Phase-I proof required")
                if self.is_integer_solution(self.current_node.solution):
                    self.update_best_solution(self.current_node.objective_value,
                        self.current_node.solution, source="bp_integer")
                    continue
                started = budget_clock.now()
                try:
                    self.branch_node(self.current_node)
                finally:
                    self.total_branch_time += budget_clock.now()-started
            remaining_seconds(time_end, "Before declaring optimal")
            self.update_global_lower_bound()
            status = "optimal" if self.optimal else "no_solution"
            if self.optimal:
                self.proof_source = "branch_tree_exhausted"
        except BoundClosed:
            self.optimal = True
            self.proof_source = "validated_incumbent_matches_global_bound"
            self.global_lower_bound = self.best_objective
            self.nodes_pruned += len(self.node_queue)
            self.node_queue.clear()
            self.current_node = None
            status, error = "optimal", None
        except CapacityInfeasible:
            self.global_lower_bound = self.problem_lower_bound
            self.proof_source = "capacity_infeasible"
            status, error = "infeasible_proven", None
        except TimeoutError as exc:
            self.optimal = False
            status, error = "time_limit", str(exc)
            self._restore_active_node()
            self.update_global_lower_bound()
        except Exception as exc:
            self.optimal = False
            status, error = "error", repr(exc)
            self._restore_active_node()
            self.update_global_lower_bound()
        self.total_solve_time = budget_clock.now()-start_time
        return dict(status=status, termination_reason=status, error=error,
                    objective_value=self.best_objective if self.best_solution is not None else None,
                    solution=self.best_solution, statistics=self.get_statistics(),
                    **self.recorder.fields())

    def _restore_active_node(self):
        if (self.current_node is not None and
                not any(node is self.current_node for node in self.node_queue)):
            heapq.heappush(self.node_queue, self.current_node)

    def _compute_problem_lower_bound(self) -> float:
        """当前EV makespan整数问题的下界，不是RMP的LP目标。"""
        if not self.graph.partitions:
            raise ValueError("车辆集合为空")
        earliest = []
        for partition in self.graph.partitions:
            if not partition.vertex_list:
                raise ValueError("车辆没有候选区间")
            values = [float(v.end_time) for v in partition.vertex_list]
            if any(not math.isfinite(v) or v < 0 for v in values):
                raise ValueError("候选结束时间非法")
            earliest.append(min(values))
        return max(earliest)
    
    def branch_node(self, current_node: BPCNode) -> None:
        """
        对当前节点进行分支
        
        Args:
            current_node: 需要分支的节点
        """
        branch_creator = BranchCreator(
            current_node.solution, 
            current_node.column_pool, 
            current_node.a_graph
        )
        if self.deadline is not None:
            remaining_seconds(self.deadline, "Before branching")
        branches = branch_creator.create_branch()
        if not branches:
            raise RuntimeError("Fractional node has no branch; cannot certify optimality")
        
        print(f"  创建了 {len(branches)} 个分支")
        for i, branch in enumerate(branches):
            if self.deadline is not None:
                remaining_seconds(self.deadline, "Branch construction")
            # 复制当前节点的图和列池
            
            a_graph = current_node.a_graph.copy()
            branch.a_graph_update(a_graph)
            
            column_pool = current_node.column_pool.copy()
            branch.column_filter(column_pool)
            
            # 创建新的分支节点
            new_node = BPCNode(
                parent=current_node,
                a_graph=a_graph,
                column_pool=column_pool,
                objective_value=current_node.objective_value,
                solution=current_node.solution
            )
            self.add_node(new_node)
            if self.deadline is not None:
                remaining_seconds(self.deadline, "After branch construction")
            print(f"    添加分支节点 {i+1}: ID={new_node.nodeid}")
    
    def process_node(self, current_node: BPCNode, time_end: float) -> bool:
        remaining_seconds(time_end, "Before node construction")
        master_problem = pricing_solver = column_generation = None
        setup_start = budget_clock.now()
        setup_recorded = False
        completed = False
        try:
            pricing_problem = PricingProblem(
                auxiliary_graph=current_node.a_graph, name="main_pricing", dual={})
            master_problem = MasterProblem(
                graph=self.graph, charger_num=self.charger_num,
                pricing_problem=pricing_problem, column_pool=current_node.column_pool,
                a_graph=current_node.a_graph)
            # Valid for every integer schedule; common to Exact, QAIA and CIM.
            if self.capacity_bound_info is not None:
                master_problem.T.LB = self.problem_lower_bound
            remaining_seconds(time_end, "After master construction")
            if self.use_qaia and current_node.parent is None:
                pricing_solver = QAIAExactPricingSolver(
                    auxiliary_graph=current_node.a_graph,
                    pricing_problem=pricing_problem,
                    column_pool=current_node.column_pool,
                    random_seed=self.qaia_seed, **pricing_options())
            else:
                pricing_solver = ExactPricingSolver(
                    auxiliary_graph=current_node.a_graph, pricing_problem=pricing_problem)
            column_generation = ColumnGeneration(
                master_problem, pricing_problem, pricing_solver,
                current_node.column_pool, self.best_objective, self.global_lower_bound,
                on_candidate=lambda solution, objective, iteration: self._consider_candidate(
                    current_node, solution, objective, "rmp_integer", iteration),
                after_master=lambda master, iteration, end: self._maybe_restricted_mip(
                    current_node, master, iteration, end))
            self.total_node_setup_time += budget_clock.now() - setup_start
            setup_recorded = True
            remaining_seconds(time_end, "After pricing construction")
            # Assignment occurs only after a fully certified CG return.
            current_node.solution, current_node.objective_value = column_generation.solve(time_end)
            completed = True
            # Also use the final root column pool, even if iteration is not a multiple.
            if current_node.parent is None:
                self._complete_root(current_node, master_problem, time_end)
                self._maybe_restricted_mip(current_node, master_problem,
                    column_generation.iteration, time_end, force=True)
            return True
        finally:
            if not setup_recorded:
                self.total_node_setup_time += budget_clock.now() - setup_start
            if column_generation is not None:
                self.total_master_time += column_generation.masterSolveTime
                self.total_pricing_time += column_generation.pricingSolveTime
                if current_node.parent is None:
                    self.root_diagnostics = dict(
                        cg_certified=completed,
                        cg_iterations=column_generation.iteration,
                        lp_objective=current_node.objective_value if completed else None,
                        integer_solution=self.is_integer_solution(current_node.solution) if completed else None,
                        columns_in_pool=len(current_node.column_pool.columns),
                        master_seconds=column_generation.masterSolveTime,
                        pricing_seconds=column_generation.pricingSolveTime,
                        heuristic_metrics=(pricing_solver.get_metrics()
                            if isinstance(pricing_solver, QAIAExactPricingSolver) else None))
            if isinstance(pricing_solver, QAIAExactPricingSolver):
                self.qaia_nodes += 1
                self.total_qaia_time += pricing_solver.qaia_solve_time
                self.total_hybrid_exact_time += pricing_solver.exact_solve_time
                self.total_qaia_calls += pricing_solver.qaia_calls
                self.total_hybrid_exact_calls += pricing_solver.exact_calls
            elif pricing_solver is not None:
                self.exact_only_nodes += 1
            # Models are local to this node; columns do not store Gurobi Var objects.
            if pricing_solver is not None:
                exact = getattr(pricing_solver, "exact_solver", pricing_solver)
                exact.model.dispose()
            if master_problem is not None:
                master_problem._rmp.dispose()
    
    def _consider_candidate(self, node, solution, objective, source, iteration=None):
        if not self.is_integer_solution(solution):
            return False
        if any(c.is_artificial_column and x > 1e-6 for c, x in solution.items()):
            return False
        return self.update_best_solution(objective, solution, a_graph=node.a_graph,
                    source=source, node_id=node.nodeid, cg_iteration=iteration)

    def _complete_root(self, node, master, deadline):
        if not self.primal_enabled:
            return
        started = budget_clock.now()
        self.primal_metrics["calls"] += 1
        self.primal_metrics["seeded_from_incumbent"] += int(self.best_solution is not None)
        try:
            added, schedules, attempts = complete_root_pool(
                self.graph, self.charger_num, node.solution, node.column_pool,
                master.pricing_problem, min(deadline, started+self.primal_slice),
                self.primal_attempts, self.qaia_seed,
                incumbent=self.best_solution, upper_bound=self.best_objective)
            for column in added:
                node.column_pool.addColumn(column)
                master.add_column_to_rmp(column)
            self.primal_metrics["attempts"] += attempts
            self.primal_metrics["columns_added"] += len(added)
            self.primal_metrics["complete_schedules"] += len(schedules)
            for solution in schedules:
                remaining_seconds(deadline, "Primal completion validation")
                objective = max(v.end_time for c in solution for v in c.vertex_list)
                before = self.best_objective
                self._consider_candidate(node, solution, objective, "primal_completion")
                self.primal_metrics["improvements"] += int(self.best_objective < before)
            # New columns warrant another MIP even at the same CG iteration.
            if added:
                self._last_mip_iteration = None
        finally:
            self.primal_metrics["seconds"] += budget_clock.now()-started

    def _maybe_restricted_mip(self, node, master, iteration, deadline, force=False):
        # Same policy for Exact, QAIA and greedy; root-only first implementation.
        if not self.rmp_mip_enabled or node.parent is not None:
            return
        if not force and iteration % self.rmp_mip_every:
            return
        if getattr(self, "_last_mip_iteration", None) == iteration:
            return
        cap = (self.recorder.deadline-self.recorder.start_time)*self.rmp_mip_fraction
        seconds = min(self.rmp_mip_slice, cap-self.rmp_mip_seconds,
                      deadline-budget_clock.now())
        if seconds <= 1e-3:
            return
        self._last_mip_iteration = iteration
        self.rmp_mip_calls += 1
        started = budget_clock.now()
        try:
            solve_restricted_mip(master, deadline, seconds,
                lambda solution, objective: self._consider_candidate(
                    node, solution, objective, "restricted_mip", iteration))
        finally:
            self.rmp_mip_seconds += budget_clock.now()-started

    def is_prunable_node(self, current_node: BPCNode) -> bool:
        if not math.isfinite(self.best_objective):
            return False
        node_bound = max(self.problem_lower_bound, current_node.objective_value)
        if node_bound >= self.best_objective:
            self.nodes_pruned += 1
            return True
        return False
    
    def update_global_lower_bound(self) -> None:
        if not self.node_queue and self.best_solution is not None:
            self.optimal = True
            self.global_lower_bound = self.best_objective
        else:
            self.optimal = False
            # Queue entries hold certified LP bounds, or their parent's certified
            # bound if processing/branching was interrupted. The objective of an
            # incomplete restricted master is never used as a lower bound.
            frontier_bound = min(
                (max(self.problem_lower_bound, node.objective_value)
                 for node in self.node_queue),
                default=self.problem_lower_bound)
            # A previously found incumbent can lie in an already closed subtree.
            self.global_lower_bound = min(self.best_objective, frontier_bound)

    def is_infeasible_solution(self, current_node: BPCNode) -> bool:
        """
        检查解是否不可行（包含人工列）
        
        Args:
            current_node: 当前节点
            
        Returns:
            解是否不可行
        """
        if not current_node.solution:
            return True
            
        return any(
            column_independent_set.is_artificial_column 
            for column_independent_set in current_node.solution.keys()
        )
    
    def generate_root_node(self) -> BPCNode:
        """
        生成根节点
        
        Returns:
            初始的根节点，包含原始图和空的列池
        """
        
        # 创建空的列池作为根节点的初始状态
        a_graph = self._create_auxiliary_graph()
        root_column_pool=self._add_artificial_columns(a_graph)
        self.build_greedy_initial_columns(a_graph,root_column_pool)
        return BPCNode(
            parent=None, 
            a_graph=a_graph, 
            column_pool=root_column_pool, 
            objective_value=0,  # 根节点下界设为负无穷
            solution={}
        )
    
    def _create_auxiliary_graph(self) -> AuxiliaryGraph:
        """
        创建辅助图
        
        Returns:
            辅助图对象
        """
        # 创建顶点映射
        
        
        return AuxiliaryGraph(
            graph=self.graph,
            vertices_map=self.graph.vertex_map,
            auxiliary_edges=None,
            merged_vertices_map=None
        )
    
    def _add_artificial_columns(self, a_graph: AuxiliaryGraph) -> ColumnPool:
        """
        为每个分区添加人工列以确保主问题可行
        
        Args:
            a_graph: 辅助图
            
        Returns:
            包含人工列的列池
        """
        root_column_pool = ColumnPool()

        # 安全起见，将 charger_num 转为整数（外部应保证为整数）
        charger_num = int(self.charger_num)

        count = 0
        artificial_columns: List[ColumnIndependentSet] = []

        # 1. 先创建 charger_num 个“空”的人工列，每列代表一个充电桩
        for _ in range(charger_num):
            column = ColumnIndependentSet(
                vertex_list=[],  # 顶点稍后再按轮分配进去
                associated_pricing_problem="artificial",
                is_artificial=True,
                creator="artificial_initialization",
                value=1000.0  # 高代价确保只在必要时使用
            )
            artificial_columns.append(column)

        # 2. 将每个分区挑选一个代表顶点，按轮分配到各个人工列中
        while count < len(self.graph.partitions):
            partition = self.graph.partitions[count]
            if not partition.vertex_list:
                count += 1
                continue
            column = artificial_columns[count % charger_num]
            # 这里简单取该分区的第一个顶点作为代表
            column.vertex_list.append(partition.vertex_list[0])
            count += 1

        # 3. 把所有人工列加入列池
        for column in artificial_columns:
            root_column_pool.addColumn(column)
        return root_column_pool

    def build_greedy_initial_columns(self, a_graph: AuxiliaryGraph,root_column_pool: ColumnPool) :
        """
        使用一个简单的贪心图着色算法，构造一组“真实列”的初始解（可选）。
        
        思路：
        - 把每个 partition 看成一辆车，每个顶点是该车的一个候选时段；
        - 为每个 partition 选择一个代表顶点（这里用 end_time 最早的那个）；
        - 对这些代表顶点做贪心着色：依次为每个顶点分配一个列（颜色），
          保证同一列内任意两顶点之间无边（即是独立集），且不来自同一 partition；
        - 每个颜色对应一个 `ColumnIndependentSet`，作为主问题的初始“真实列”。
        
        注意：
        - 本函数不会自动被调用，仅作为一种可选的启发式初始解；
        - 人工列 `_add_artificial_columns` 仍然保留，用于严格保证可行性。
        """

        # 1. 建立邻接表，便于快速判断冲突
        #    注意：必须使用辅助图 a_graph，而不是原始图 self.graph，
        #    因为 a_graph 中已经包含了分区内部的互斥边和分支产生的额外边。
        adjacency: Dict[int, Set[int]] = {v_id: set() for v_id in a_graph.vertices_map.keys()}
        for edge in a_graph.auxiliary_edges:
            u_id = edge.source.id
            v_id = edge.target.id
            adjacency[u_id].add(v_id)
            adjacency[v_id].add(u_id)

        # 2. 为每个 partition 选一个代表顶点（end_time 最早）
        representative_vertices: List = []
        for partition in self.graph.partitions:
            if not partition.vertex_list:
                continue
            rep_vertex = min(
                partition.vertex_list,
                key=lambda v: getattr(v, "end_time", 0.0),
            )
            representative_vertices.append(rep_vertex)

        # 3. 贪心着色：为代表顶点分配列（颜色），保证列内顶点两两不相邻，且分区不同
        columns: List[List] = []  # 每个元素是一个顶点列表，表示一个独立集列
        columns_partitions: List[Set[int]] = []  # 跟踪每列中已使用的 partition id

        for vertex in representative_vertices:
            placed = False
            part_id = vertex.associated_partition.id

            # 尝试放入已有列
            for col_idx, col_vertices in enumerate(columns):
                # 同一列中不能有相同 partition
                if part_id in columns_partitions[col_idx]:
                    continue

                # 检查与该列中所有顶点是否冲突
                conflict = False
                for other in col_vertices:
                    if other.id in adjacency[vertex.id]:
                        conflict = True
                        break

                if not conflict:
                    col_vertices.append(vertex)
                    columns_partitions[col_idx].add(part_id)
                    placed = True
                    break

            # 若无法放入任何已有列，则创建一个新列
            if not placed:
                columns.append([vertex])
                columns_partitions.append({part_id})

        # 4. 把每个颜色（独立集）转换成列对象加入列池
        for col_vertices in columns:
            column = ColumnIndependentSet(
                vertex_list=col_vertices,
                associated_pricing_problem="greedy_initial",
                is_artificial=False,
                creator="greedy_initialization",
                value=0.0,
            )
            root_column_pool.addColumn(column)

    
    def is_integer_solution(self, solution) -> bool:
        if not solution:
            return False
        try:
            values = [float(x) for x in solution.values()]
        except (TypeError, ValueError):
            return False
        return all(math.isfinite(x) and min(abs(x), abs(x-1)) <= 1e-6 for x in values)

    def add_node(self, node: BPCNode) -> None:
        """
        向优先队列添加节点
        
        Args:
            node: 要添加的分支节点
        """
        heapq.heappush(self.node_queue, node)
        self.nodes_created += 1
        
    def get_next_node(self) -> Optional[BPCNode]:
        """
        从优先队列中取出目标值最小的节点
        
        Returns:
            目标值最小的节点，如果队列为空则返回None
        """
        if self.node_queue:
            return heapq.heappop(self.node_queue)
        return None
        
    def is_queue_empty(self) -> bool:
        """
        检查队列是否为空
        
        Returns:
            队列是否为空
        """
        return len(self.node_queue) == 0
        
    def queue_size(self) -> int:
        """
        获取队列中节点数量
        
        Returns:
            队列中的节点数量
        """
        return len(self.node_queue)
    
    def prune_nodes(self) -> int:
        """
        剪枝：移除下界大于等于当前最优解的节点
        
        Returns:
            被剪枝的节点数量
        """
        if self.best_objective == float('inf'):
            return 0
            
        pruned_count = 0
        remaining_nodes = []
        
        # 重新构建队列，只保留有希望的节点
        while self.node_queue:
            node = heapq.heappop(self.node_queue)
            if max(self.problem_lower_bound, node.objective_value) < self.best_objective:
                remaining_nodes.append(node)
            else:
                pruned_count += 1
        
        # 重新建堆
        self.node_queue = remaining_nodes
        heapq.heapify(self.node_queue)
        
        self.nodes_pruned += pruned_count
        return pruned_count
    
    def update_best_solution(self, objective_value, solution, *, a_graph=None,
                             source="bp_integer", node_id=None, cg_iteration=None):
        """Only validated physical schedules update UB; LP bounds are untouched."""
        if self.deadline is not None and budget_clock.now() > self.deadline:
            return False
        graph = a_graph if a_graph is not None else self.current_node.a_graph
        checked = validate_schedule(solution, graph, self.graph, self.charger_num, objective_value)
        physical_objective = float(checked["makespan"])
        if physical_objective >= self.best_objective-1e-6:
            return False
        # Store canonical original-vertex columns matching the deduplicated schedule.
        canonical = {}
        for row in checked["schedule"]:
            column = ColumnIndependentSet(
                vertex_list=[self.graph.vertex_map[c["vertex_id"]] for c in row],
                associated_pricing_problem="validated_incumbent", is_artificial=False,
                creator=source, value=0.0)
            canonical[column] = 1.0
        if self.recorder is None:
            raise RuntimeError("Call solve before updating incumbent")
        if node_id is None and self.current_node is not None:
            node_id = self.current_node.nodeid
        if not self.recorder.record(checked["schedule"], physical_objective, source,
                                    node_id=node_id, cg_iteration=cg_iteration):
            return False
        self.best_objective = physical_objective
        self.incumbent_input_creators = [c.creator for c, x in solution.items() if x > 1e-6]
        self.best_solution = canonical
        self.best_schedule = copy.deepcopy(checked)
        self.best_schedule_makespan = physical_objective
        if physical_objective <= self.problem_lower_bound+1e-7:
            raise BoundClosed()
        self.prune_nodes()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取算法运行统计信息
        
        Returns:
            统计信息字典
        """
        column_num = max(0, ColumnIndependentSet._next_column_id - 1)
    
        return {
            "nodes_processed": self.nodes_processed,
            "nodes_created": self.nodes_created,
            "nodes_pruned": self.nodes_pruned,
            "nodes_remaining": self.queue_size(),
            "best_objective": self.best_objective,
            "global_lower_bound": self.global_lower_bound,
            "gap": ((self.best_objective - self.global_lower_bound) / max(abs(self.best_objective), 1e-6)
                    if math.isfinite(self.best_objective) and math.isfinite(self.global_lower_bound) else None),
            "total_solve_time": self.total_solve_time,
            "problem_lower_bound": self.problem_lower_bound,
            "capacity_bound": self.capacity_bound_info,
            "proof_source": self.proof_source,
            "column_num": column_num,
            "master_seconds": self.total_master_time,
            "node_setup_seconds": self.total_node_setup_time,
            "root_initialization_seconds": self.root_initialization_seconds,
            "pricing_seconds": self.total_pricing_time,
            "branch_seconds": self.total_branch_time,
            "restricted_mip_seconds": self.rmp_mip_seconds,
            "restricted_mip_calls": self.rmp_mip_calls,
            "primal_completion": dict(self.primal_metrics),
            "incumbent_input_column_creators": self.incumbent_input_creators,
            "root_diagnostics": self.root_diagnostics
        }
