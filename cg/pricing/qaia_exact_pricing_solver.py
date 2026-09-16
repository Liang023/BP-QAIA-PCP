"""

混合定价序列如下：

1. 使用 MindQuantum QAIA 求解最大权独立集定价问题的 QUBO/Ising 近似；
2. 将每个 QAIA 样本解码并修复为可行的独立集；
3. 将最佳 QAIA 列作为 MIP 启动点传递给 Gurobi；
4. 调用现有的精确定价求解器；
5. 返回前删除重复/非改进的列。

"""

from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import gurobipy as grb
import numpy as np
from scipy.sparse import csr_matrix

from cg.column_independent_set import ColumnIndependentSet
from cg.column_pool import ColumnPool
from cg.pricing.exact_pricing_solver import ExactPricingSolver
from cg.pricing.pricing_problem import PricingProblem
from model.a_graph import AuxiliaryGraph

import os
from cg.deadline import remaining_seconds


class PricingNotCertifiedError(RuntimeError):
    """当精确定价无法证明不存在改进列时引发。"""


class QAIAPricingSolver:
    """使用 MindQuantum QAIA 算法生成可行的定价列。

    当前定价问题是最大权独立集问题

        max  sum_v w_v x_v
        s.t. x_u + x_v <= 1,  (u, v) in E^A,

    其中 ``w_v`` 已经由 ``PricingProblem.update_pricing_problem`` 更新。
    我们最小化 QUBO

        -sum_v w_v x_v + penalty * sum_(u,v) x_u x_v

    并将其转换为 MindQuantum QAIA 使用的 Ising 约定：

        H(s) = -0.5 * s.T @ J @ s - h.T @ s,
        x = (1 + s) / 2.

    QAIA 是启发式的，因此每个解码的样本都会使用原始图和原始约化成本表达式进行修复和检查。
    """

    def __init__(
        self,
        auxiliary_graph: AuxiliaryGraph,
        pricing_problem: PricingProblem,
        *,
        provider: str = "qaia",
        algorithm: str = "BSB",
        n_iter: int = 1000,
        batch_size: int = 50,
        backend: str = "cpu-float32",
        penalty_margin: float = 1.0,
        epsilon: float = 1e-6,
        max_columns: int = 10,
        random_seed: Optional[int] = None,
        normalize_ising: bool = True,
        algorithm_kwargs: Optional[Dict] = None,
    ) -> None:
        if n_iter <= 0:
            raise ValueError("n_iter 必须为正")
        if batch_size <= 0:
            raise ValueError("batch_size 必须为正")
        if penalty_margin <= 0:
            raise ValueError("penalty_margin 必须为正")
        if max_columns <= 0:
            raise ValueError("max_columns 必须为正")

        self.auxiliary_graph = auxiliary_graph
        self.pricing_problem = pricing_problem
        if provider not in {"qaia", "greedy"}:
            raise ValueError("Unknown heuristic provider")
        self.provider = provider
        self.profile = dict(build_seconds=0.0, search_seconds=0.0,
                            repair_seconds=0.0, raw_samples=0,
                            improving_unique=0, pool_duplicates=0,
                            returned_columns=0, nonfinite_samples=0)
        self.algorithm = algorithm
        self.n_iter = int(n_iter)
        self.batch_size = int(batch_size)
        self.backend = backend
        self.penalty_margin = float(penalty_margin)
        self.epsilon = float(epsilon)
        self.max_columns = int(max_columns)
        self.random_seed = random_seed
        self.normalize_ising = bool(normalize_ising)
        self.algorithm_kwargs = dict(algorithm_kwargs or {})

        reserved = {"J", "h", "n_iter", "batch_size", "backend"}
        overlap = reserved.intersection(self.algorithm_kwargs)
        if overlap:
            names = ", ".join(sorted(overlap))
            raise ValueError(
                f"algorithm_kwargs 无法覆盖保留的参数： {names}"
            )

        self.solve_time = 0.0
        self.calls = 0

    def generate_columns(self, time_end: float, *, exclude_signatures=None):
        remaining_seconds(time_end, "Before heuristic")
        started = time.perf_counter()
        self.calls += 1
        excluded = set(exclude_signatures or ())
        try:
            t0 = time.perf_counter()
            vertex_ids, weights, adjacency, forbidden, j_mat, h_vec = self._build_ising_model()
            self.profile["build_seconds"] += time.perf_counter() - t0
            if not vertex_ids:
                return []
            remaining_seconds(time_end, "After Ising construction")
            t0 = time.perf_counter()
            if self.provider == "greedy":
                seed = None if self.random_seed is None else self.random_seed + self.calls - 1
                rng = np.random.default_rng(seed)
                samples = rng.integers(0, 2, size=(len(vertex_ids), self.batch_size), dtype=np.int8)
                samples[:, 0] = 0  # First start is deterministic weight-ordered greedy.
            else:
                raw = self._run_qaia(j_mat, h_vec)
                if hasattr(raw, "detach"):
                    raw = raw.detach().cpu().numpy()
                state = np.asarray(raw)
                if state.ndim == 1:
                    state = state[:, None]
                if state.ndim != 2 or state.shape[0] != len(vertex_ids):
                    raise ValueError(f"Unexpected QAIA shape: {state.shape}")
                valid = np.isfinite(state).all(axis=0)
                self.profile["nonfinite_samples"] += int((~valid).sum())
                samples = self._decode_state(state[:, valid], len(vertex_ids))
            self.profile["search_seconds"] += time.perf_counter() - t0
            remaining_seconds(time_end, "After heuristic search")
            t0 = time.perf_counter()
            self.profile["raw_samples"] += samples.shape[1]
            candidates = {}
            for sample in samples.T:
                remaining_seconds(time_end, "Heuristic repair")
                initial = {vertex_ids[i] for i, value in enumerate(sample) if value == 1}
                repaired = self._repair_independent_set(
                    initial, vertex_ids, weights, adjacency, forbidden)
                signature = tuple(sorted(repaired))
                violation = self._pricing_violation(signature)
                if signature and violation > self.epsilon:
                    candidates[signature] = violation
            self.profile["improving_unique"] += len(candidates)
            self.profile["pool_duplicates"] += sum(s in excluded for s in candidates)
            # Remove existing columns BEFORE selecting the best k new columns.
            ranked = sorted(((s, v) for s, v in candidates.items() if s not in excluded),
                            key=lambda item: (-item[1], item[0]))[:self.max_columns]
            columns = [self._make_column(s) for s, _ in ranked]
            self.profile["returned_columns"] += len(columns)
            self.profile["repair_seconds"] += time.perf_counter() - t0
            return columns
        finally:
            self.solve_time += time.perf_counter() - started

    def _build_ising_model(
        self,
    ) -> Tuple[
        List[int],
        Dict[int, float],
        Dict[int, Set[int]],
        Set[int],
        csr_matrix,
        np.ndarray,
    ]:
        """构建对称的、零对角线的 Ising 矩阵和外场。"""
        vertex_ids = sorted(self.auxiliary_graph.vertices_map.keys())
        index_of = {vertex_id: index for index, vertex_id in enumerate(vertex_ids)}
        weights = {
            vertex_id: float(self.auxiliary_graph.weight_v.get(vertex_id, 0.0))
            for vertex_id in vertex_ids
        }
        adjacency: Dict[int, Set[int]] = {
            vertex_id: set() for vertex_id in vertex_ids
        }
        self_forbidden: Set[int] = set()
        unique_edges: Set[Tuple[int, int]] = set()

        for edge in self.auxiliary_graph.auxiliary_edges:
            source_id = edge.source.id
            target_id = edge.target.id
            if source_id not in index_of or target_id not in index_of:
                continue
            if source_id == target_id:
                # ExactPricingSolver 为这样的边创建 2*x_v <= 1，所以
                # 这个顶点绝不能被选中。
                self_forbidden.add(source_id)
                continue
            u, v = sorted((source_id, target_id))
            unique_edges.add((u, v))

        for u, v in unique_edges:
            adjacency[u].add(v)
            adjacency[v].add(u)

        positive_max = max((max(weight, 0.0) for weight in weights.values()), default=0.0)
        penalty = max(1.0, positive_max) + self.penalty_margin

        # 对于 x=(1+s)/2 和 QUBO
        #   -sum_i w_i*x_i + P*sum_(i,j) x_i*x_j,
        # MindQuantum 的约定要求
        #   J_ij = -P/4,
        #   h_i  = w_i/2 - P*degree(i)/4.
        h_vec = np.asarray(
            [weights[vertex_id] / 2.0 for vertex_id in vertex_ids],
            dtype=np.float64,
        )
        rows: List[int] = []
        cols: List[int] = []
        data: List[float] = []

        coupling = -penalty / 4.0
        field_edge_shift = penalty / 4.0
        for u, v in unique_edges:
            i = index_of[u]
            j = index_of[v]
            rows.extend((i, j))
            cols.extend((j, i))
            data.extend((coupling, coupling))
            h_vec[i] -= field_edge_shift
            h_vec[j] -= field_edge_shift

        # 自环对应于 QUBO 中的 P*x_i。其非常数
        # 贡献是 +(P/2)*s_i，因此 h_i 接收 -P/2。
        for vertex_id in self_forbidden:
            h_vec[index_of[vertex_id]] -= penalty / 2.0

        size = len(vertex_ids)
        j_mat = csr_matrix((data, (rows, cols)), shape=(size, size), dtype=np.float64)

        if self.normalize_ising:
            max_j = float(np.max(np.abs(j_mat.data))) if j_mat.nnz else 0.0
            max_h = float(np.max(np.abs(h_vec))) if h_vec.size else 0.0
            scale = max(max_j, max_h, 1.0)
            if scale > 1.0:
                j_mat = j_mat / scale
                h_vec = h_vec / scale

        return vertex_ids, weights, adjacency, self_forbidden, j_mat, h_vec

    def _run_qaia(self, j_mat: csr_matrix, h_vec: np.ndarray):
        """实例化配置的QAIA求解器并运行。"""

        # Exact/greedy 不依赖 MindQuantum；只在实际运行 QAIA 时加载。
        import qaia
        names = ("CAC", "CFC", "LQA", "NMFA", "ASB", "BSB", "DSB",
                 "TSB", "USB", "LSB", "SFC", "SimCIM")
        algorithm_classes = {name: getattr(qaia, name) for name in names}

        solver_class = algorithm_classes.get(self.algorithm)

        if solver_class is None:
            raise ValueError(
                f"未知的QAIA算法 {self.algorithm!r}；"
                f"可用算法：{sorted(algorithm_classes)}"
            )

        if self.random_seed is not None:
            # 不同调用使用不同种子，同时保持实验可复现
            call_seed = self.random_seed + self.calls - 1
            np.random.seed(call_seed)

        solver = solver_class(
            J=j_mat,
            h=h_vec,
            n_iter=self.n_iter,
            batch_size=self.batch_size,
            backend=self.backend,
            **self.algorithm_kwargs,
        )

        solver.update()
        return solver.x
    
    @staticmethod
    def _decode_state(raw_state, number_of_vertices: int) -> np.ndarray:
        """将 NumPy/Torch QAIA 状态转换为 {0,1} 样本矩阵。"""
        if hasattr(raw_state, "detach"):
            raw_state = raw_state.detach().cpu().numpy()
        state = np.asarray(raw_state)
        if state.ndim == 1:
            state = state[:, np.newaxis]
        if state.ndim != 2 or state.shape[0] != number_of_vertices:
            raise ValueError(
                "意料之外的 QAIA 状态形状："
                f"预计 ({number_of_vertices}, batch_size)，得到 {state.shape}"
            )
        if not np.isfinite(state).all():
            raise ValueError("Non-finite QAIA state")
        spins = np.where(state >= 0.0, 1, -1)
        return ((spins + 1) // 2).astype(np.int8)

    @staticmethod
    def _repair_independent_set(
        initially_selected: Set[int],
        vertex_ids: Sequence[int],
        weights: Dict[int, float],
        adjacency: Dict[int, Set[int]],
        self_forbidden: Set[int],
    ) -> Set[int]:
        """修复冲突並贪心扩展 QAIA 样本。

        QAIA 选中的正权重顶点会率先考虑。然后与正权重
        顶点一起考虑以获得最大可行集。负权重/非正权重
        顶点不能改进这个最大权重独立集目标，与之被逝潢。
        """
        selected_order = sorted(
            (
                vertex_id
                for vertex_id in initially_selected
                if vertex_id not in self_forbidden and weights[vertex_id] > 0.0
            ),
            key=lambda vertex_id: (-weights[vertex_id], vertex_id),
        )
        remaining_order = sorted(
            (
                vertex_id
                for vertex_id in vertex_ids
                if vertex_id not in initially_selected
                and vertex_id not in self_forbidden
                and weights[vertex_id] > 0.0
            ),
            key=lambda vertex_id: (-weights[vertex_id], vertex_id),
        )

        repaired: Set[int] = set()
        for vertex_id in selected_order + remaining_order:
            if adjacency[vertex_id].isdisjoint(repaired):
                repaired.add(vertex_id)
        return repaired

    def _pricing_violation(self, signature: Iterable[int]) -> float:
        vertex_part = sum(
            float(self.auxiliary_graph.weight_v.get(vertex_id, 0.0))
            for vertex_id in signature
        )
        charger_dual = float(self.pricing_problem.dual.get("charger", 0.0))
        return vertex_part + charger_dual

    def _make_column(self, signature: Sequence[int]) -> ColumnIndependentSet:
        vertices = [
            self.auxiliary_graph.vertices_map[vertex_id]
            for vertex_id in signature
        ]
        return ColumnIndependentSet(
            vertex_list=vertices,
            value=0.0,
            associated_pricing_problem=self.pricing_problem,
            is_artificial=False,
            creator=f"QAIA-{self.algorithm}" if self.provider == "qaia" else "Greedy-multistart",
        )


class QAIAExactPricingSolver:
    """QAIA与精确定价相结合的混合定价求解器。

    Parameters
    ----------
    exact_mode:
        ``"always"``：
        每次先运行QAIA，然后始终运行Exact Pricing。
        该模式主要用于比较QAIA提供的MIP Start能否加速Exact，
        但通常会增加额外计算开销。

        ``"on_qaia_failure"``：
        如果QAIA找到至少一条未进入列池的有效改进列，
        则本轮直接返回QAIA列，不调用Exact Pricing；
        如果QAIA没有找到有效新列，则调用Exact Pricing，
        搜索遗漏的改进列或提供不存在改进列的最优性证明。

        ``"on_qaia_failure"``不会牺牲整个列生成过程的精确性，
        因为只有Exact Pricing证明不存在改进列后，
        当前节点的列生成才会终止。
    """

    VALID_EXACT_MODES = {"always", "on_qaia_failure"}

    def __init__(
        self,
        auxiliary_graph: AuxiliaryGraph,
        pricing_problem: PricingProblem,
        column_pool: Optional[ColumnPool] = None,
        *,
        exact_mode: str = "always",
        heuristic_provider: str = "qaia",
        max_heuristic_streak: int = 3,
        qaia_algorithm: str = "BSB",
        qaia_n_iter: int = 1000,
        qaia_batch_size: int = 50,
        qaia_backend: str = "cpu-float32",
        qaia_penalty_margin: float = 1.0,
        qaia_max_columns: int = 10,
        epsilon: float = 1e-6,
        random_seed: Optional[int] = None,
        normalize_ising: bool = True,
        qaia_algorithm_kwargs: Optional[Dict] = None,
    ) -> None:
        if exact_mode not in self.VALID_EXACT_MODES:
            raise ValueError(
                f"exact_mode \u5fc5\u987b\u662f\u4ee5\u4e0b\u4e4b\u4e00 {sorted(self.VALID_EXACT_MODES)}"
            )

        self.auxiliary_graph = auxiliary_graph
        self.pricing_problem = pricing_problem
        self.column_pool = column_pool
        self.exact_mode = exact_mode
        if max_heuristic_streak <= 0:
            raise ValueError("max_heuristic_streak must be positive")
        self.max_heuristic_streak = int(max_heuristic_streak)
        self.heuristic_streak = 0
        self.exact_skips = 0
        self.hit_calls = 0
        self.column_policy = os.getenv("QAIA_COLUMN_POLICY", "combined")
        if self.column_policy not in {"combined", "warm_start_only"}:
            raise ValueError("Unknown QAIA_COLUMN_POLICY")
        if self.column_policy == "warm_start_only" and exact_mode != "always":
            raise ValueError("warm_start_only requires exact_mode=always")
        self.epsilon = float(epsilon)

        self.qaia_solver = QAIAPricingSolver(
            auxiliary_graph=auxiliary_graph,
            pricing_problem=pricing_problem,
            provider=heuristic_provider,
            algorithm=qaia_algorithm,
            n_iter=qaia_n_iter,
            batch_size=qaia_batch_size,
            backend=qaia_backend,
            penalty_margin=qaia_penalty_margin,
            epsilon=epsilon,
            max_columns=qaia_max_columns,
            random_seed=random_seed,
            normalize_ising=normalize_ising,
            algorithm_kwargs=qaia_algorithm_kwargs,
        )
        self.exact_solver = ExactPricingSolver(
            auxiliary_graph=auxiliary_graph,
            pricing_problem=pricing_problem,
        )

        self.qaia_solve_time = 0.0
        self.exact_solve_time = 0.0
        self.qaia_calls = 0
        self.exact_calls = 0

    def generate_columns(self, time_end: float):
        remaining_seconds(time_end, "Before hybrid pricing")
        qaia_columns = []
        forced_exact = (self.exact_mode == "on_qaia_failure"
                        and self.heuristic_streak >= self.max_heuristic_streak)
        if not forced_exact:
            start = time.perf_counter()
            self.qaia_calls += 1  # Legacy name: counts the selected heuristic provider.
            try:
                qaia_columns = self.qaia_solver.generate_columns(
                    time_end, exclude_signatures=self._existing_signatures())
            finally:
                self.qaia_solve_time += time.perf_counter() - start
            remaining_seconds(time_end, "After heuristic")
            qaia_columns = self._deduplicate(qaia_columns, exclude_existing=True)
            if qaia_columns:
                self.hit_calls += 1
                if self.exact_mode == "on_qaia_failure":
                    self.heuristic_streak += 1
                    self.exact_skips += 1
                    return qaia_columns
        self.heuristic_streak = 0
        # A start is useful only if Exact will actually run with these weights.
        for variable in self.exact_solver.vars.values():
            variable.Start = grb.GRB.UNDEFINED
        if qaia_columns:
            self._set_exact_mip_start(qaia_columns)
        start = time.perf_counter()
        self.exact_calls += 1
        try:
            exact_columns = self.exact_solver.generate_columns(time_end)
        finally:
            self.exact_solve_time += time.perf_counter() - start
        selected = (exact_columns if self.column_policy == "warm_start_only"
                    else [*qaia_columns, *exact_columns])
        combined = self._deduplicate(selected, exclude_existing=True)
        model = self.exact_solver.model
        if model.Status == grb.GRB.TIME_LIMIT:
            raise TimeoutError("Exact pricing timed out; node is not certified")
        if not combined:
            if model.Status != grb.GRB.OPTIMAL:
                raise PricingNotCertifiedError(f"Pricing status={model.Status}")
            bound_violation = float(model.ObjBound) + float(self.pricing_problem.dual.get("charger", 0.0))
            if not np.isfinite(bound_violation) or bound_violation > self.epsilon:
                raise PricingNotCertifiedError(
                    "No fresh column, but Exact bound still permits an improving column")
        return combined

    def get_metrics(self):
        return dict(provider=self.qaia_solver.provider,
                    heuristic_calls=self.qaia_calls, hit_calls=self.hit_calls,
                    exact_calls=self.exact_calls, exact_skips=self.exact_skips,
                    heuristic_seconds=self.qaia_solve_time,
                    exact_seconds=self.exact_solve_time,
                    **self.qaia_solver.profile)
    
    def _set_exact_mip_start(
        self, qaia_columns: Sequence[ColumnIndependentSet]
    ) -> None:
        """将最优 QAIA 列用作 Gurobi MIP 启动点。"""
        best_column = max(qaia_columns, key=self._column_violation)
        selected_ids = {vertex.id for vertex in best_column.vertex_list}
        for vertex_id, variable in self.exact_solver.vars.items():
            variable.Start = 1.0 if vertex_id in selected_ids else 0.0
        self.exact_solver.model.update()

    def _column_violation(self, column: ColumnIndependentSet) -> float:
        vertex_part = sum(
            float(self.auxiliary_graph.weight_v.get(vertex.id, 0.0))
            for vertex in column.vertex_list
        )
        charger_dual = float(self.pricing_problem.dual.get("charger", 0.0))
        return vertex_part + charger_dual

    @staticmethod
    def _signature(column: ColumnIndependentSet) -> Tuple[int, ...]:
        return tuple(sorted(vertex.id for vertex in column.vertex_list))

    def _existing_signatures(self) -> Set[Tuple[int, ...]]:
        if self.column_pool is None:
            return set()
        return {self._signature(column) for column in self.column_pool.columns}

    def _deduplicate(
        self,
        columns: Sequence[ColumnIndependentSet],
        *,
        exclude_existing: bool,
    ) -> List[ColumnIndependentSet]:
        seen = self._existing_signatures() if exclude_existing else set()
        unique: List[ColumnIndependentSet] = []
        for column in columns:
            signature = self._signature(column)
            if not signature or signature in seen:
                continue
            # 重新检查 QAIA 和 Exact 输出的真实定价条件。
            if self._column_violation(column) <= self.epsilon:
                continue
            seen.add(signature)
            unique.append(column)
        return unique

    # 这些别名使包装器在任何需要 ExactPricingSolver 公开的分支
    # 钩子的代码中可用。
    def branchPerformed(self, branching_decision) -> None:
        self.exact_solver.branchPerformed(branching_decision)

    def branchReversed(self, branching_decision) -> None:
        self.exact_solver.branchReversed(branching_decision)

    def get_solution(self):
        return self.exact_solver.get_solution()


