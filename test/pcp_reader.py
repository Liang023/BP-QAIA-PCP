"""
PCP算例文件读取器

根据 http://www2.ic.uff.br/~celso/grupo/pcp.htm 的格式规范读取PCP实例文件
文件格式:
|V| |E| |Q|
for each vertex v:
    Q[v]
for each edge (i,j):
    i j

其中 Q[v] 是包含顶点v的分区组件编号
"""

import sys
import os
from typing import List, Tuple
from model.graph import Graph
from model.vertex import Vertex
from model.edge import Edge
from model.partition import Partition
from model.instance import Instance
import random

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


    


class PCPReader:
    """PCP算例文件读取器"""
    
    def __init__(self):
        random.seed(17)
        """初始化读取器"""
        pass
    
    def read_pcp_file(self, file_path: str) -> Graph:
        """
        读取PCP算例文件并创建Graph对象
        
        Args:
            file_path: PCP文件路径
            
        Returns:
            Graph对象，包含顶点、边和分区信息
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        print(f"正在读取PCP文件: {file_path}")
        
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        
        if not lines:
            raise ValueError("文件为空")
        
        # 解析第一行: |V| |E| |Q|
        header = lines[0].split()
        if len(header) != 3:
            raise ValueError(f"文件头格式错误，期望3个数字，得到: {header}")
        
        try:
            num_vertices = int(header[0])
            num_edges = int(header[1])
            num_partitions = int(header[2])
        except ValueError as e:
            raise ValueError(f"文件头数字格式错误: {e}")
        
        print(f"  顶点数: {num_vertices}, 边数: {num_edges}, 分区数: {num_partitions}")
        
        # 检查文件行数是否正确
        expected_lines = 1 + num_vertices + num_edges
        if len(lines) != expected_lines:
            raise ValueError(f"文件行数不匹配，期望{expected_lines}行，实际{len(lines)}行")
        
        # 读取顶点的分区信息
        vertex_partitions = []
        for i in range(1, num_vertices + 1):
            try:
                partition_id = int(lines[i])
                vertex_partitions.append(partition_id)
            except ValueError as e:
                raise ValueError(f"第{i+1}行分区ID格式错误: {e}")
        
        # 读取边信息
        edges_data = []
        for i in range(num_vertices + 1, num_vertices + 1 + num_edges):
            edge_line = lines[i].split()
            if len(edge_line) != 2:
                raise ValueError(f"第{i+1}行边格式错误，期望2个顶点，得到: {edge_line}")
            
            try:
                v1 = int(edge_line[0])
                v2 = int(edge_line[1])
                edges_data.append((v1, v2))
            except ValueError as e:
                raise ValueError(f"第{i+1}行边顶点ID格式错误: {e}")
        
        
        # 创建顶点对象
        vertices = self._create_vertices(num_vertices, vertex_partitions)
        
        # 现在创建正确的分区对象（包含Vertex对象）
        partitions = self._create_partitions_with_vertices(num_partitions, vertex_partitions, vertices)
        
        # 更新顶点的分区引用
        for vertex_index, vertex in enumerate(vertices):
            vertex_partition_id = vertex_partitions[vertex_index]
            vertex.set_associated_partition(partitions[vertex_partition_id])
        
        # 创建边对象
        edges = self._create_edges(edges_data, vertices)
        
        # 验证数据一致性
        self._validate_data(vertices, edges, partitions, num_vertices, num_edges, num_partitions)
        
        print(f"  成功读取: {len(vertices)}个顶点, {len(edges)}条边, {len(partitions)}个分区")
        
        return Graph(edges=edges, vertices=vertices, partitions=partitions)


def read_pcp_instance(file_path: str, charger_num: int) -> Instance:
    """
    读取 PCP 文件并构造一个 Instance（包含 graph 和 charger_num）。

    注意：
    - 这里不再根据分区数“猜测” charger_num；
    - charger_num 必须由算例本身或调用者显式给出（例如来自 EV JSON），
      以保证算例的可行性由数据而不是代码默认值来决定。
    """
    reader = PCPReader()
    graph = reader.read_pcp_file(file_path)
    name = os.path.basename(file_path)
    return Instance(graph=graph, charger_num=charger_num, name=name)

    
    
    
    def _create_partitions_with_vertices(self, num_partitions: int, vertex_partitions: List[int], 
                                       vertices: List[Vertex]) -> List[Partition]:
        """
        创建包含Vertex对象的分区对象
        
        Args:
            num_partitions: 分区数量
            vertex_partitions: 每个顶点所属的分区ID列表
            vertices: 顶点对象列表
            
        Returns:
            分区对象列表（包含正确的Vertex对象集合）
        """
        partitions = []
        
        # 统计每个分区包含的顶点对象
        partition_vertices = {i: [] for i in range(num_partitions)}
        
        # 使用顶点在列表中的索引来匹配分区ID
        for vertex_index, vertex in enumerate(vertices):
            partition_id = vertex_partitions[vertex_index]
            if partition_id < 0 or partition_id >= num_partitions:
                raise ValueError(f"顶点索引{vertex_index}的分区ID {partition_id} 超出范围")
            partition_vertices[partition_id].append(vertex)
        
        # 创建分区对象
        for partition_id in range(num_partitions):
            vertex_list = partition_vertices[partition_id]
            if not vertex_list:
                print(f"  警告: 分区{partition_id}为空")
            
            partition = Partition(
                id=partition_id,
                vertex_list=vertex_list
            )
            partitions.append(partition)
        
        return partitions
    
    def _create_vertices(self, num_vertices: int, vertex_partitions: List[int]
                        ) -> List[Vertex]:
        """
        创建顶点对象
        
        Args:
            num_vertices: 顶点数量
            vertex_partitions: 每个顶点所属的分区ID列表
            partitions: 分区对象列表
            
        Returns:
            顶点对象列表
        """
        vertices = []
        

        for vertex_index in range(num_vertices):
            
            end_time = random.randint(0, 100)
            vertex = Vertex(end_time)  # 自动生成ID# TODO: 需要从文件中读取end_time
            vertices.append(vertex)
     
        
        return vertices
    
    def _create_edges(self, edges_data: List[Tuple[int, int]], vertices: List[Vertex]) -> List[Edge]:
        """
        创建边对象
        
        Args:
            edges_data: 边数据列表，每个元素是(顶点1, 顶点2)的元组
            vertices: 顶点对象列表
            
        Returns:
            边对象列表
        """
        edges = []
        vertex_map = {v.id: v for v in vertices}
        
        for i, (v1_id, v2_id) in enumerate(edges_data):
            # 验证顶点ID有效性
            if v1_id not in vertex_map:
                raise ValueError(f"边{i}: 顶点{v1_id}不存在")
            if v2_id not in vertex_map:
                raise ValueError(f"边{i}: 顶点{v2_id}不存在")
            
            # 避免自环
            if v1_id == v2_id:
                print(f"  警告: 跳过自环边 ({v1_id}, {v2_id})")
                continue
            
            vertex1 = vertex_map[v1_id]
            vertex2 = vertex_map[v2_id]
            
            edge = Edge(
                source=vertex1,
                target=vertex2
            )
            edges.append(edge)
        
        return edges
    
    def _validate_data(self, vertices: List[Vertex], edges: List[Edge], 
                      partitions: List[Partition], expected_vertices: int, 
                      expected_edges: int, expected_partitions: int) -> None:
        """
        验证读取的数据一致性
        
        Args:
            vertices: 顶点列表
            edges: 边列表
            partitions: 分区列表
            expected_vertices: 期望的顶点数
            expected_edges: 期望的边数
            expected_partitions: 期望的分区数
        """
        # 验证数量
        if len(vertices) != expected_vertices:
            raise ValueError(f"顶点数量不匹配: 期望{expected_vertices}, 实际{len(vertices)}")
        
        if len(partitions) != expected_partitions:
            raise ValueError(f"分区数量不匹配: 期望{expected_partitions}, 实际{len(partitions)}")
        
        # 注意：边数可能因为跳过自环而减少
        if len(edges) > expected_edges:
            raise ValueError(f"边数量超出期望: 期望最多{expected_edges}, 实际{len(edges)}")
        
        # 验证顶点ID连续性
        vertex_ids = {v.id for v in vertices}
        expected_vertex_ids = set(range(expected_vertices))
        if vertex_ids != expected_vertex_ids:
            missing = expected_vertex_ids - vertex_ids
            extra = vertex_ids - expected_vertex_ids
            raise ValueError(f"顶点ID不连续: 缺失{missing}, 多余{extra}")
        
        # 验证每个顶点都属于某个分区
        for vertex in vertices:
            if vertex.associated_partition not in partitions:
                raise ValueError(f"顶点{vertex.id}的关联分区不在分区列表中")
        
        print("  数据验证通过")


