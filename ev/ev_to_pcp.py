"""
将 EV 算例 JSON 转换为 PCP 图 / Instance。

约定的 EV JSON 结构（与 generate_ev_instances.py 一致）：
{
  "time_horizon": 24,
  "duration": 2,
  "num_vehicles": 20,
  "num_chargers": 5,
  "vehicles": [
    {
      "id": 0,
      "duration": 2,
      "candidates": [
        {"candidate_id": 0, "start": 1, "end": 3},
        ...
      ]
    },
    ...
  ]
}

映射规则（只编码“物理冲突”，不在算例中硬编码 independent set 概念）：
- 每个候选充电时段 = PCP 中的一个顶点；
- 每辆车的所有候选 = 一个分区；
- 若两个候选在**同一充电桩**且时间重叠 ⇒ 两顶点之间有一条边；
- 不同桩之间不连边（它们物理上可以同时充电），
  是否放在同一个 independent set 由后续算法自己决定。
"""

from __future__ import annotations

import json
import os
from typing import Dict, Any, List

from model.edge import Edge
from model.graph import Graph
from model.instance import Instance
from model.partition import Partition
from model.vertex import Vertex


def ev_json_to_instance(ev_data: Dict[str, Any]) -> Instance:
    """从内存中的 EV JSON dict 构造 PCP Graph 和 Instance。"""
    vehicles = ev_data["vehicles"]
    num_chargers = ev_data["num_chargers"]

    vertices: List[Vertex] = []
    partitions: List[Partition] = []

    # 记录 (vehicle_id, candidate_id) -> 顶点对象
    vtx_by_pair: Dict[tuple[int, int], Vertex] = {}

    # 1) 为每辆车创建顶点和分区
    for veh in vehicles:
        v_id = veh["id"]
        cand_vertices: List[Vertex] = []
        for cand in veh["candidates"]:
            end_time = cand["end"]
            vertex = Vertex(end_time=end_time)
            vertices.append(vertex)
            cand_vertices.append(vertex)
            vtx_by_pair[(v_id, cand["candidate_id"])] = vertex
        part = Partition(id=v_id, vertex_list=cand_vertices)
        partitions.append(part)
        # 更新每个顶点的分区引用
        for vertex in cand_vertices:
            vertex.set_associated_partition(part)

    # 2) 仅根据“时间重叠”创建边（与充电桩无关）
    #    即：任何两个时间段只要在时间轴上有交集，就在它们之间连一条边。
    items: List[dict] = []
    for veh in vehicles:
        v_id = veh["id"]
        for cand in veh["candidates"]:
            cid = cand["candidate_id"]
            items.append(
                {
                    "vehicle_id": v_id,
                    "candidate_id": cid,
                    "start": cand["start"],
                    "end": cand["end"],
                }
            )

    edges: List[Edge] = []
    n = len(items)
    for i in range(n):
        a = items[i]
        s_a, e_a = a["start"], a["end"]
        vtx_a = vtx_by_pair[(a["vehicle_id"], a["candidate_id"])]
        for j in range(i + 1, n):
            b = items[j]
            s_b, e_b = b["start"], b["end"]
            # 时间重叠条件（半开区间 [start, end)）
            if s_a < e_b and s_b < e_a:
                vtx_b = vtx_by_pair[(b["vehicle_id"], b["candidate_id"])]
                edges.append(Edge(source=vtx_a, target=vtx_b))

    graph = Graph(edges=edges, vertices=vertices, partitions=partitions)
    name = ev_data.get("name", None)
    instance = Instance(graph=graph, charger_num=num_chargers, name=name)
    return instance


def load_ev_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_ev_instance(path: str) -> Instance:
    """从 EV JSON 文件直接构造 Instance。"""
    data = load_ev_json(path)
    # 若没有显式 name，则用文件名
    if "name" not in data:
        data["name"] = os.path.basename(path)
    return ev_json_to_instance(data)


def save_pcp_from_instance(instance: Instance, path: str) -> None:
    """
    将 Instance 中的 Graph 导出为 .pcp 文件，便于和原始 PCP 算例对比。

    格式：
    |V| |E| |Q|
    Q[v] (v 从 0..|V|-1)
    i j  (边的顶点索引)
    """
    graph = instance.graph
    vertices = graph.vertices
    edges = graph.edges
    partitions = graph.partitions

    # 建立顶点到索引的映射（0..|V|-1）
    index_by_vertex: Dict[Vertex, int] = {v: idx for idx, v in enumerate(vertices)}

    # 分区 id 本身我们已经按 0..|P|-1 建好了，这里直接使用

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{len(vertices)} {len(edges)} {len(partitions)}\n")

        # 每个顶点的分区号
        for v in vertices:
            part_id = v.associated_partition.id
            f.write(f"{part_id}\n")

        # 边列表
        for e in edges:
            i = index_by_vertex[e.source]
            j = index_by_vertex[e.target]
            f.write(f"{i} {j}\n")

    print(f"PCP 文件已导出到: {path}")


if __name__ == "__main__":
    # 批量示例：将 data/ev_instances/ 下所有 .json 转成 .pcp，便于观察图结构
    ev_dir = os.path.join("data", "ev_instances")
    if not os.path.isdir(ev_dir):
        print(f"目录不存在: {ev_dir}")
    else:
        for fname in os.listdir(ev_dir):
            if not fname.endswith(".json"):
                continue
            json_path = os.path.join(ev_dir, fname)
            inst = load_ev_instance(json_path)
            pcp_name = os.path.splitext(fname)[0] + ".pcp"
            pcp_path = os.path.join(ev_dir, pcp_name)
            save_pcp_from_instance(inst, pcp_path)


