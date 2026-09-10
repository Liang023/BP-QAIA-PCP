import argparse
import json
from pathlib import Path
import random


def build_instance(n, chargers, seed):
    rng = random.Random(seed)
    # 随机车辆顺序与异质时长，先植入一个可行排程，再扩展窗口。
    # 这是保证可行的测试集，不是无偏真实会话分布。
    durations = [rng.choice([1, 2, 3]) for _ in range(n)]
    order = list(range(n))
    rng.shuffle(order)
    available = [0] * chargers
    base = {}
    for i in order:
        k = min(range(chargers), key=lambda k: (available[k], k))
        start = available[k] + rng.randint(0, 1)
        end = start + durations[i]
        available[k] = end
        base[i] = (start, end)
    horizon = max(available) + 3
    vehicles = []
    for i in range(n):
        start, end = base[i]
        arrival = max(0, start-rng.randint(0, 2))
        departure = min(horizon, end+rng.randint(1, 3))
        duration = durations[i]
        candidates = [dict(candidate_id=j, start=s, end=s+duration)
                      for j, s in enumerate(range(arrival, departure-duration+1))]
        vehicles.append(dict(id=i, arrival=arrival, departure=departure,
                             duration=duration, candidates=candidates))
    return dict(schema_version="synthetic-v1", data_seed=seed,
                name=f"v1_N{n}_C{chargers}_s{seed}", num_vehicles=n,
                num_chargers=chargers, time_horizon=horizon,
                time_unit="abstract_slot", vehicles=vehicles)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/ev_instances_v1")
    args = parser.parse_args()
    out = Path(args.out_dir)
    plans = [build_instance(n, 2, seed) for n in (6, 8, 10) for seed in (0, 1, 2)]
    # 写入前检查全部路径，避免部分覆盖旧数据。
    if any((out / (d["name"] + ".json")).exists() for d in plans):
        raise FileExistsError("目标数据已存在，请使用新的目录，不覆盖旧版本")
    out.mkdir(parents=True, exist_ok=True)
    for data in plans:
        path = out / (data["name"] + ".json")
        with path.open("x", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(path, sum(len(v["candidates"]) for v in data["vehicles"]), "vertices")


if __name__ == "__main__":
    main()