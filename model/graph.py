from typing import List
from model.edge import Edge
from model.vertex import Vertex
from model.partition import Partition


class Graph:
    def __init__(self,edges:List[Edge],vertices:List[Vertex],partitions:List[Partition]):
        self.edges=edges
        self.vertices=vertices
        self.partitions=partitions
        self.vertex_map={v.id:v for v in vertices}
        
        
        
        
        