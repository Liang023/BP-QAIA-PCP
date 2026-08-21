from typing import Optional, Dict
from model.a_graph import AuxiliaryGraph
from cg.column_pool import ColumnPool

class BPCNode:
    """
    分支定价树节点类
    
    表示分支定价算法中的一个节点，包含节点状态、目标值、解等信息。
    该类实现了比较运算符以便于在优先队列中按目标值排序。
    """
    _next_node_id = 1
    
    def __init__(self, parent: Optional['BPCNode'] = None, 
                 a_graph: Optional[AuxiliaryGraph] = None,
                 column_pool: Optional[ColumnPool] = None,
                 objective_value: float = float('-inf'),
                 solution: Optional[Dict[int, float]] = None):
        """
        初始化分支定价节点
        
        Args:
            parent: 父节点
            a_graph: 辅助图对象
            column_pool: 列池对象
            objective_value: 目标值（下界）
            solution: 解字典
        """
        self.a_graph = a_graph
        self.column_pool = column_pool
        self.objective_value = objective_value
        self.solution = solution if solution is not None else {}
        
        # 生成唯一节点ID
        self.nodeid = BPCNode._next_node_id
        BPCNode._next_node_id += 1
        self.parent = parent
    
    
    def __lt__(self, other: 'BPCNode') -> bool:
        """小于比较，用于优先队列按目标值排序。"""
        return self.objective_value < other.objective_value
        
    def __eq__(self, other: 'BPCNode') -> bool:
        """等于比较。"""
        return self.objective_value == other.objective_value
        
    def __gt__(self, other: 'BPCNode') -> bool:
        """大于比较。"""
        return self.objective_value > other.objective_value
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"BPCNode(id={self.nodeid})"
        
        