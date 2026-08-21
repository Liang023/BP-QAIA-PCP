from model.vertex import Vertex
from typing import List

class ColumnIndependentSet:
    """
    Class modeling an independent set in the column generation procedure.
    An independent set is a set of vertices where no two vertices are adjacent.
    Note that the fields in an independent set (except the value assigned to it by the master problem) are all final:
    an independent set should NOT be tempered with.
    """
    
    # 类级别的计数器，用于生成唯一的列ID
    _next_column_id = 1
    
    def __init__(self, vertex_list:List[Vertex], associated_pricing_problem, is_artificial, creator, value=0.0):
        """
        Constructs a new independent set
        
        Args:
            vertex_set (set): Set of vertices in this independent set
            associated_pricing_problem: Pricing problem to which this independent set belongs
            is_artificial (bool): Is this an artificial independent set?
            creator (str): Who/What created this independent set?
        """
        self.vertex_list = vertex_list  # The set of vertices in this independent set
        self.value = value  # The value of the independent set assigned to it by the last master problem solved
        self.is_artificial_column = is_artificial  # Indicates whether this is a real independent set or artificial
        self.creator = creator  # Textual description of the method which created this independent set
        self.associated_pricing_problem = associated_pricing_problem  # The pricing problem to which this independent set belongs
        self.iteration =0 # last iteration when the independent set was added to the master problem,used to manage the column pool
        
        # 生成唯一的列ID
        self.columnid = ColumnIndependentSet._next_column_id
        ColumnIndependentSet._next_column_id += 1
        
        # 生成可读的列名称（用于调试和日志）
        self.readable_name = self._generate_readable_name()
    
    def _generate_readable_name(self):
        """生成可读的列名称"""
        vertex_str = "-".join(sorted([str(v.id) for v in self.vertex_list]))
        prefix = "ART" if self.is_artificial_column else "COL"
        return f"{prefix}_{vertex_str}_{self.columnid}"
    
    @classmethod
    def reset_counter(cls):
        """重置列ID计数器（主要用于测试）"""
        cls._next_column_id = 1
    
    def __eq__(self, other):
        """
        Compares two independent sets mutually.
        
        Args:
            other: Another independent set to compare with
            
        Returns:
            bool: True if the independent sets are equal, False otherwise
        """
        if not isinstance(other, ColumnIndependentSet):
            return False
        return (self.vertex_list == other.vertex_list and
                self.is_artificial_column == other.is_artificial_column and
                self.creator == other.creator and
                self.associated_pricing_problem == other.associated_pricing_problem)
    
    def __hash__(self):
        """
        Creates a hash code for the given independent set
        
        Returns:
            int: Hash code for the independent set
        """
        return hash(self.columnid)
    
    def __str__(self):
        """
        Gives a textual representation of an independent set
        
        Returns:
            str: String representation of the independent set
        """
        vertex_ids = [vertex.id for vertex in self.vertex_list]
        return f"{self.readable_name}(vertices={vertex_ids})"
    
    def __repr__(self):
        """详细的字符串表示"""
        vertex_ids = [vertex.id for vertex in self.vertex_list]
        return f"ColumnIndependentSet(id={self.columnid}, vertices={vertex_ids},is_artificial={self.is_artificial_column})"
