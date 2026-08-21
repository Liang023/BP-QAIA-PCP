from typing import List


class Partition:
    def __init__(self, id: int, vertex_list: List):
        """Initialize a Partition object

        Args:
            vertex_list: List of vertices in the partition
        """
        self.id = id
        self.vertex_list = vertex_list
        
    def __str__(self):
        vertex_ids = [vertex.id for vertex in self.vertex_list]
        return f"Partition(id={self.id}, vertex_list={vertex_ids})"
    def __repr__(self):
        vertex_ids = [vertex.id for vertex in self.vertex_list]
        return f"Partition(id={self.id}, vertex_list={vertex_ids})"
