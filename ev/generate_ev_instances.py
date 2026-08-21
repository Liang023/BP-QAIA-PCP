"""
生成 EV 充电调度算例（JSON），后续可通过 ev_to_pcp.py 转成 PCP 图。

参数设计（可根据需要调整）：
- 时间窗 time_horizon ∈ {12, 24} 小时；
- 固定充电时长 duration ∈ {1, 2} 小时；
- 车辆数 num_vehicles ∈ {20, 40, 60}（可扩展）；
- 车辆数 / 桩数 ∈ {3, 4, 5}，即每个充电桩大约服务 3/4/5 辆车；
- 每辆车候选充电时段数 ∈ {2, 3, 4}。

生成逻辑：
1. 先为每辆车构造一个“基准方案”（不冲突、满足桩容量），保证整体可行；
2. 再为每辆车额外生成若干候选方案，允许相互之间产生冲突，从而得到有代表性的 PCP 图；
3. 将结果写成 JSON：data/ev_instances/ev_V{v}_C{c}_T{T}_dur{d}_cand{k}.json
"""

from __future__ import annotations

import json
import os
import random
from typing import List, Dict, Any, Tuple


def _build_base_schedule(
    num_vehicles: int,
    num_chargers: int,
    time_horizon: int,
    duration: int,
    rng: random.Random,
) -> List[Dict[str, int]]:
    """
    构造一个不冲突的基准排程：每辆车恰好一个候选方案，满足桩容量和时间不重叠。
    """
    # 占用矩阵：charger -> [time_horizon] -> bool
    occupied = [[False] * time_horizon for _ in range(num_chargers)]
    candidates: List[Dict[str, int]] = []

    max_slots_per_charger = time_horizon // duration
    total_capacity = max_slots_per_charger * num_chargers
    if num_vehicles > total_capacity:
        raise ValueError(
            f"车辆数 {num_vehicles} 超过在 time_horizon={time_horizon}, "
            f"duration={duration}, charger_num={num_chargers} 下的理论容量 {total_capacity}"
        )

    for v in range(num_vehicles):
        placed = False
        # 简化为确定性的“先桩后时间”遍历：只要总容量足够，就一定能找到位置
        for p in range(num_chargers):
            for s in range(0, time_horizon - duration + 1):
                # 检查该桩在 [s, s+duration) 是否空闲
                if all(not occupied[p][t] for t in range(s, s + duration)):
                    for t in range(s, s + duration):
                        occupied[p][t] = True
                    candidates.append(
                        {
                            "vehicle_id": v,
                            "candidate_id": 0,
                            "start": s,
                            "end": s + duration,
                        }
                    )
                    placed = True
                    break
            if placed:
                break
        if not placed:
            raise RuntimeError(
                f"无法为车辆 {v} 在给定参数下找到无冲突的基准充电时段，请调整参数。"
            )

    return candidates


def generate_ev_instance(
    num_vehicles: int,
    vehicles_per_charger: int,
    time_horizon: int,
    duration: int,
    min_candidates: int,
    max_candidates: int,
    seed: int = 0,
) -> Dict[str, Any]:
    """
    生成一个 EV 算例，返回 Python dict 可直接写成 JSON。
    """
    if num_vehicles % vehicles_per_charger != 0:
        raise ValueError(
            f"num_vehicles={num_vehicles} 不能被 vehicles_per_charger={vehicles_per_charger} 整除"
        )
    num_chargers = num_vehicles // vehicles_per_charger
    rng = random.Random(seed)

    # 1) 基准无冲突方案
    base_candidates = _build_base_schedule(
        num_vehicles=num_vehicles,
        num_chargers=num_chargers,
        time_horizon=time_horizon,
        duration=duration,
        rng=rng,
    )

    # 2) 对每辆车增加若干候选方案（允许产生冲突）
    vehicles: List[Dict[str, Any]] = []
    # 根据 vehicle_id 将基准候选分组
    base_by_vehicle: Dict[int, Dict[str, int]] = {c["vehicle_id"]: c for c in base_candidates}

    for v in range(num_vehicles):
        # 当前车辆候选个数
        k = rng.randint(min_candidates, max_candidates)
        cand_list: List[Dict[str, Any]] = []
        base = base_by_vehicle[v]
        cand_list.append(
            {
                "candidate_id": 0,
                "start": base["start"],
                "end": base["end"],
            }
        )

        # 额外候选
        for cid in range(1, k):
            s = rng.randrange(0, time_horizon - duration + 1)
            cand_list.append(
                {
                    "candidate_id": cid,
                    "start": s,
                    "end": s + duration,
                }
            )

        vehicles.append(
            {
                "id": v,
                "duration": duration,
                "candidates": cand_list,
            }
        )

    instance = {
        "time_horizon": time_horizon,
        "duration": duration,
        "num_vehicles": num_vehicles,
        "num_chargers": num_chargers,
        "vehicles": vehicles,
    }
    return instance


def save_ev_instance(instance: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(instance, f, ensure_ascii=False, indent=2)


def main():
    # 默认参数范围
    time_horizons = [12, 24]
    durations = [1, 2]
    # 想要生成的车辆规模：10, 20, 30, 40, 50, 60, 70, 80
    num_vehicles_list = [10, 20, 30, 40, 50, 60, 70, 80]
    vehicles_per_charger_list = [3, 4, 5]
    cand_range: Tuple[int, int] = (2, 4)  # 每辆车候选方案数 2~4

    output_dir = os.path.join("data", "ev_instances")

    seed = 42
    for T in time_horizons:
        for dur in durations:
            for nv in num_vehicles_list:
                for vpc in vehicles_per_charger_list:
                    # 容量检查：每个桩的时间槽数要 >= 每桩的车辆数
                    num_chargers = nv // vpc
                    if nv % vpc != 0:
                        continue
                    max_slots_per_charger = T // dur
                    if vpc > max_slots_per_charger:
                        # 参数不合理，跳过
                        continue

                    inst = generate_ev_instance(
                        num_vehicles=nv,
                        vehicles_per_charger=vpc,
                        time_horizon=T,
                        duration=dur,
                        min_candidates=cand_range[0],
                        max_candidates=cand_range[1],
                        seed=seed,
                    )
                    fname = f"ev_V{nv}_C{num_chargers}_T{T}_dur{dur}_vpc{vpc}.json"
                    path = os.path.join(output_dir, fname)
                    save_ev_instance(inst, path)
                    print(f"生成 EV 算例: {path}")
                    seed += 1  # 每个实例用不同种子


if __name__ == "__main__":
    main()


