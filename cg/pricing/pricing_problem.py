from typing import Dict
from model.a_graph import AuxiliaryGraph


"""
This module contains the PricingProblem class which represents a pricing problem in column generation.
The pricing problem is responsible for generating new columns (independent sets) with negative reduced cost.
It maintains the dual costs from the master problem and handles branching decisions.
"""

class PricingProblem:
    def __init__(self, auxiliary_graph: AuxiliaryGraph, name : str,dual:Dict):
        self.auxiliary_graph = auxiliary_graph
        self.name = name
        self.dual = dual
    
    def update_pricing_problem(self,dual:Dict):
        self.dual = dual
        self.auxiliary_graph.update_weightf(self.dual)

    def __str__(self):
        return f"PricingProblem(name={self.name})"

    __repr__ = __str__
