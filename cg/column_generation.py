from cg.master.master_problem import MasterProblem
from cg.pricing.pricing_problem import PricingProblem
from cg.pricing.exact_pricing_solver import ExactPricingSolver
from cg.column_pool import ColumnPool
from config.Config import Config

import time
import math
from typing import List, Dict
from cg.column_independent_set import ColumnIndependentSet


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
    def solve(self, time_end: int):
        """执行列生成迭代直至终止，返回解与主问题目标值。"""
        foundNewColumn = True
        self.new_columns = self.column_pool.columns
        while foundNewColumn:
            self.iteration += 1
            self.invokeMaster(self.new_columns,time_end)
            if self.check_termination():
                break
            
            new_columns = self.invokePricing(time_end, self.dual)
            self.new_columns = new_columns
            for column in new_columns:
                self.column_pool.addColumn(column)
            foundNewColumn = len(new_columns) > 0
        self.solution = self.master.solution
        # print(f"Column Generation Iteration {self.iteration} completed")
        return self.solution,self.masterObjective
    
    def check_termination(self):
        """终止判定：上界已达到或上下界在容差内收敛。"""
        if (
                math.ceil(self.masterObjective - self.config.epsilon)
                >= self.upper_bound
            ):
                return True
            
        if (
                abs(self.masterObjective - self.lower_bound)
                < self.config.epsilon
            ):
                return True
            
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