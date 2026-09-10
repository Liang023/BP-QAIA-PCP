import math
from collections import Counter


def validate_schedule(solution, a_graph, graph, chargers, objective, tol=1e-6):
    """展开合并顶点；验证原列；去掉跨列重复车辆后验证物理排程。

    只服务当前同质桩、非抢占、候选区间makespan模型。
    不在这里修改B&P上界或宣称最优性。
    """
    if not solution or not math.isfinite(float(objective)):
        raise ValueError("没有可校验的整数解")
    rows = []
    for col, value in solution.items():
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("非有限列权重")
        if abs(value) <= tol:
            continue
        if abs(value - 1.0) > tol or col.is_artificial_column:
            raise ValueError("解含分数列、非0/1列或人工列")
        originals = []
        for vertex in col.vertex_list:
            originals.extend(a_graph.get_original_vertices(vertex))
        ids = [v.id for v in originals]
        if len(ids) != len(set(ids)):
            raise ValueError("一列展开后重复原始顶点")
        if any(v.id not in graph.vertex_map for v in originals):
            raise ValueError("无法展开为原图顶点")
        part_ids = [v.associated_partition.id for v in originals]
        if len(part_ids) != len(set(part_ids)):
            raise ValueError("同一桩列含同一车辆的多个候选")
        selected = set(ids)
        if any(e.source.id in selected and e.target.id in selected
               for e in graph.edges):
            raise ValueError("原列含图冲突")
        row = sorted(originals, key=lambda v: (v.start_time, v.end_time, v.id))
        for v in row:
            if not 0 <= v.start_time < v.end_time:
                raise ValueError("候选区间非法")
        if any(a.end_time > b.start_time for a, b in zip(row, row[1:])):
            raise ValueError("同桩时间重叠")
        rows.append(row)
    if len(rows) > chargers:
        raise ValueError("桩数超限")
    counts = Counter(v.vehicle_id for row in rows for v in row)
    required = {p.id for p in graph.partitions}
    if set(counts) != required:
        raise ValueError("车辆覆盖缺失或存在未知车辆")
    seen, schedule = set(), []
    for row in rows:
        cleaned = []
        for v in row:
            if v.vehicle_id in seen:
                continue
            seen.add(v.vehicle_id)
            cleaned.append(dict(vehicle_id=v.vehicle_id,
                                candidate_id=v.candidate_id,
                                vertex_id=v.id,
                                start=v.start_time, end=v.end_time))
        if cleaned:
            schedule.append(cleaned)
    makespan = max(v["end"] for row in schedule for v in row)
    if makespan > objective + tol:
        raise ValueError("物理排程makespan大于B&P报告目标")
    return dict(schedule=schedule, makespan=makespan,
                duplicate_vehicles={str(k): n for k, n in counts.items() if n > 1})