import argparse
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ["ev_V10_C2_T12_dur1_vpc5.json", "ev_V10_C2_T12_dur2_vpc5.json",
          "ev_V10_C2_T24_dur1_vpc5.json", "ev_V20_C5_T12_dur1_vpc4.json",
          "ev_V20_C4_T12_dur1_vpc5.json"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", choices=["legacy", "v1"], required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--limit", type=float, default=120)
    args = p.parse_args()
    out = Path(args.out_dir).resolve()
    if out.exists():
        raise FileExistsError("结果目录已存在，请换目录，避免混入旧记录")
    if not math.isfinite(args.limit) or args.limit <= 0:
        raise ValueError("limit必须为有限正数")
    files = ([ROOT / "data/ev_instances" / n for n in LEGACY]
             if args.dataset == "legacy" else
             [ROOT / "data/ev_instances_v1" / f"v1_N{n}_C2_s{s}.json"
              for n in (6, 8, 10) for s in (0, 1, 2)])
    if not all(path.is_file() for path in files):
        raise FileNotFoundError("缺少指定数据，先生成v1或检查旧数据目录")
    out.mkdir(parents=True)
    manifest = dict(dataset=args.dataset, limit=args.limit,
                    instances=[str(x) for x in files], qaia_seeds=[0,1,2,3,4],
                    exact_repeats=3)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary = []
    fingerprints = set()

    def run(path, method, seed, label):
        result_path = out / f"{path.stem}_{label}.json"
        command = [sys.executable, str(ROOT / "test/run_stage1.py"),
                   "--instance", str(path), "--method", method,
                   "--seed", str(seed), "--limit", str(args.limit),
                   "--out", str(result_path)]
        started = time.perf_counter()
        try:
            with result_path.with_suffix(".process.log").open("x", encoding="utf-8") as f:
                proc = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                                      timeout=args.limit + 60)
            if proc.returncode != 0 or not result_path.exists():
                raise RuntimeError("子进程失败或缺少结果，查看process.log")
            record = json.loads(result_path.read_text(encoding="utf-8"))
        except subprocess.TimeoutExpired:
            failure = dict(status="external_timeout", method=method, seed=seed,
                           instance=str(path), process_seconds=time.perf_counter()-started)
            result_path.with_suffix(".failure.json").write_text(
                json.dumps(failure, indent=2), encoding="utf-8")
            raise RuntimeError("外部超时，保留日志并停止，不计算伪gap")
        if record.get("status") != "optimal" or record.get("validation_passed") is not True:
            raise RuntimeError(f"{result_path.name} 未通过认证/校验，停止扩展")
        objective = record.get("objective")
        if objective is None or not math.isfinite(objective):
            raise RuntimeError("缺少有限目标")
        fp = record.get("source_sha256")
        if not fp:
            raise RuntimeError("请先完成run_stage1源码指纹修改")
        fingerprints.add(fp)
        if len(fingerprints) != 1:
            raise RuntimeError("批次内源码发生变化，停止比较")
        return record

    try:
        # 热身单独保存，不参与中位数；也必须通过校验。
        warm_ref = run(files[0], "compact", 0, "warmup_compact")
        for method in ("exact", "qaia_root"):
            warm = run(files[0], method, 0, "warmup_" + method)
            if abs(warm["objective"] - warm_ref["objective"]) > 1e-6:
                raise RuntimeError("热身目标不一致")
        for path in files:
            reference = run(path, "compact", 0, "compact")
            runs = {"exact": [], "qaia_root": []}
            for seed in range(5):
                pair = [("qaia_root", seed, f"qaia_s{seed}")]
                if seed < 3:
                    pair.append(("exact", 0, f"exact_r{seed}"))
                if seed % 2 == 0:
                    pair.reverse()
                for method, algo_seed, label in pair:
                    result = run(path, method, algo_seed, label)
                    if result["instance_sha256"] != reference["instance_sha256"]:
                        raise RuntimeError("运行期间输入数据改变")
                    if abs(result["objective"]-reference["objective"]) > 1e-6:
                        raise RuntimeError(f"{path.name} 与compact目标不一致")
                    runs[method].append(result)
            row = dict(instance=path.name, vertices=reference["vertices"],
                       objective=reference["objective"],
                       compact_workflow_seconds=reference["workflow_seconds"])
            for method, records in runs.items():
                times = [r["wall_seconds"] for r in records]
                row[method] = dict(count=len(times), median_seconds=statistics.median(times),
                    min_seconds=min(times), max_seconds=max(times),
                    median_workflow_seconds=statistics.median(r["workflow_seconds"] for r in records),
                    nodes=[r["statistics"]["nodes_processed"] for r in records])
            row["bp_speedup"] = (row["exact"]["median_seconds"] /
                                  row["qaia_root"]["median_seconds"])
            summary.append(row)
            (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
            print(path.name, "passed; BP speedup", round(row["bp_speedup"], 3), flush=True)
    except Exception as exc:
        (out / "STOP.json").write_text(json.dumps(dict(error=str(exc)), ensure_ascii=False,
                                                   indent=2), encoding="utf-8")
        raise
    (out / "PASS.json").write_text(json.dumps(dict(instances=len(files),
        source_sha256=next(iter(fingerprints))), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()