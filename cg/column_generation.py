from cg.master.master_problem import MasterProblem
from cg.pricing.pricing_problem import PricingProblem
from cg.pricing.exact_pricing_solver import ExactPricingSolver
from cg.column_pool import ColumnPool
from config.Config import Config

import time
import math
from typing import List, Dict
from cg.column_independent_set import ColumnIndependentSet
import gurobipy as grb

class ColumnGeneration:
    """
    列生成主流程控制器：在主问题与子问题之间迭代，持续引入具有负 reduced cost 的列，
    直到满足终止条件（收敛或界限达到）。

    - invokeMaster: 将新列加入 RMP，求解主问题并获取对偶与目标值；
    - invokePricing: 用对偶更新定价问题，求解并返回新列；
    - check_termination: 依据上下界与容差判断是否停止迭代。
    """
    def __init__(
        self,
        master: MasterProblem,
        pricing_problem: PricingProblem,
        pricing_solver: ExactPricingSolver,
        column_pool: ColumnPool,
        upper_bound: float,
        lower_bound: float
    ):
        self.master = master
        self.pricing_problem = pricing_problem
        self.pricing_solver = pricing_solver
        self.column_pool = column_pool
        self.upper_bound = upper_bound
        self.lower_bound = lower_bound
        self.lower_bound = 0.0
        self.masterSolveTime = 0
        self.dual: Dict = {}  # {'partition': {...}, 'makespan': {...}}
        self.pricingSolveTime = 0
        self.masterObjective = 0.0
        self.iteration = 0
        self.solution = None
        self.new_columns = []
        self.config = Config()

    def solve(self, time_end: float):
        """
        执行列生成。

        只有在精确定价达到最优，并且确认不存在改进列时，
        才能结束当前节点的列生成。
        """
        self.new_columns = list(self.column_pool.columns)

        while True:
            if time.time() >= time_end:
                raise TimeoutError(
                    "列生成在精确定价完成之前达到时间限制"
                )

            self.iteration += 1

            # 第一步：把新列加入RMP并求解
            self.invokeMaster(self.new_columns, time_end)

            # 第二步：必须运行定价，不能在定价之前提前终止
            new_columns = self.invokePricing(time_end, self.dual)

            print(
                f"[CG {self.iteration}] "
                f"RMP={self.masterObjective:.6f}, "
                f"pricing={type(self.pricing_solver).__name__}, "
                f"new_columns={len(new_columns)}"
            )

            # 第三步：没有新列时检查Exact Pricing是否真正达到最优
            if len(new_columns) == 0:
                exact_solver = getattr(
                    self.pricing_solver,
                    "exact_solver",
                    self.pricing_solver
                )

                exact_status = exact_solver.model.Status

                if exact_status != grb.GRB.OPTIMAL:
                    raise RuntimeError(
                        "定价问题没有返回新列，但也没有取得最优性证明。"
                        f"Gurobi status={exact_status}"
                    )

                break

            # 第四步：加入新列
            self.new_columns = []

            for column in new_columns:
                self.column_pool.addColumn(column)
                self.new_columns.append(column)

        self.solution = self.master.solution

        return self.solution, self.masterObjective
        
    # def check_termination(self):
    #     """终止判定：上界已达到或上下界在容差内收敛。"""
    #     if (
    #             math.ceil(self.masterObjective - self.config.epsilon)
    #             >= self.upper_bound
    #         ):
    #             return True
            
    #     if (
    #             abs(self.masterObjective - self.lower_bound)
    #             < self.config.epsilon
    #         ):
    #             return True
            
    def invokeMaster(self,new_columns:List[ColumnIndependentSet], time_end: int):
        """将新列加入 RMP 并求解主问题，更新对偶与目标值。"""
        c_time = time.time()
        for column in new_columns:
            self.master.add_column_to_rmp(column)
            
        solution, duals, obj_val = self.master.solveMaster(time_end)
        self.masterSolveTime += time.time() - c_time
        self.masterObjective = obj_val
        self.dual = duals
    
    def invokePricing(self, time_end: int, dual: Dict):
        """用对偶更新定价问题并求解，返回新生成的列集合。"""
        c_time = time.time()
        self.pricing_problem.update_pricing_problem(dual)
        new_columns = self.pricing_solver.generate_columns(time_end)
        self.pricingSolveTime += time.time() - c_time
        return new_columns