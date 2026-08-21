from model.partition import Partition

class Vertex:
     # 类级别的计数器，用于生成唯一的列ID
    _next_vertex_id = 0
    def __init__(self,end_time:int):
        self.id = Vertex._next_vertex_id
        Vertex._next_vertex_id += 1
        self.end_time = end_time
    
    def set_associated_partition(self, partition:Partition):
        self.associated_partition = partition
    
    def __eq__(self, other):
        if not isinstance(other, Vertex):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
    def __str__(self):
        return f"Vertex(id={self.id})"
    def __repr__(self):
        return f"Vertex(id={self.id})"
    
    