"""Wait for real CIM samples; exclude measured cloud calls from the BP clock."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import numpy as np
from cg import budget_clock
from cg.deadline import remaining_seconds


def cim_options():
    options = dict(device_id=os.getenv("CIM_DEVICE_ID", "WuYue-QPU-Qboson-1000"),
        max_bits=int(os.getenv("CIM_MAX_BITS", "1000")),
        precision=int(os.getenv("CIM_PRECISION", "8")),
        max_calls=int(os.getenv("CIM_MAX_CALLS", "3")),
        cache_dir=os.getenv("CIM_CACHE_DIR", "results/cim_tasks"))
    if (options["max_bits"] <= 1 or options["max_calls"] < 0 or
            not 2 <= options["precision"] <= 8):
        raise ValueError("Invalid CIM size, precision or call count")
    return options


class CIMBackend:
    def __init__(self):
        self.options = cim_options()
        self.metrics = dict(requests=0, completed=0, timeouts=0, size_skips=0,
                            capped_skips=0, seconds=0.0, cloud_excluded_seconds=0.0,
                            local_seconds=0.0, tasks=[])

    def sample(self, ids, weights, adjacency, forbidden, margin, deadline):
        empty = np.empty((len(ids), 0), dtype=np.int8)
        if len(ids)+1 > self.options["max_bits"]:
            self.metrics["size_skips"] += 1
            return empty
        if self.metrics["requests"] >= self.options["max_calls"]:
            self.metrics["capped_skips"] += 1
            return empty
        remaining_seconds(deadline, "Before CIM submission")
        if not os.getenv("ECLOUD_ACCESS_KEY") or not os.getenv("ECLOUD_SECRET_KEY"):
            raise RuntimeError("Set ECLOUD_ACCESS_KEY and ECLOUD_SECRET_KEY for CIM")
        task = "bp" + uuid.uuid4().hex[:20]
        directory = Path(self.options["cache_dir"]).resolve()/task
        directory.mkdir(parents=True)
        request, result = directory/"request.json", directory/"samples.npy"
        request.write_text(json.dumps(dict(ids=ids, weights=[weights[v] for v in ids],
            edges=[(u, v) for u in ids for v in sorted(adjacency[u]) if u < v],
            forbidden=sorted(forbidden), penalty=max(1.0, max(weights.values()))+margin,
            task=task, options=self.options)), encoding="utf-8")
        event = dict(task=task, directory=str(directory), status="requested")
        self.metrics["tasks"].append(event)
        self.metrics["requests"] += 1
        started = time.perf_counter()
        cloud_seconds = 0.0
        try:
            with (directory/"worker.log").open("w", encoding="utf-8") as log:
                proc = subprocess.run([sys.executable, "-m", "cg.pricing.cim_worker",
                    str(request), str(result)], stdout=log, stderr=subprocess.STDOUT)
            timing_path = directory / "cloud_timing.json"
            if timing_path.exists():
                cloud_seconds = json.loads(timing_path.read_text(encoding="utf-8"))["cloud_call_seconds"]
                budget_clock.exclude_cloud_seconds(cloud_seconds)
            if proc.returncode:
                event["status"] = "error"
                raise RuntimeError(f"CIM worker failed; inspect {directory / 'worker.log'}")
            if not timing_path.exists():
                raise RuntimeError("CIM worker did not record cloud-call timing")
            samples = np.load(result, allow_pickle=False)
            if samples.ndim != 2 or samples.shape[0] != len(ids) or samples.shape[1] == 0 or not np.isin(samples, [0, 1]).all():
                raise ValueError("CIM worker returned invalid binary sample dimensions")
            event["status"] = "completed"
            self.metrics["completed"] += 1
            return samples
        except Exception:
            event["status"] = "error"
            raise
        finally:
            elapsed = time.perf_counter()-started
            event["seconds"] = elapsed
            self.metrics["seconds"] += elapsed
            event["cloud_excluded_seconds"] = cloud_seconds
            event["local_seconds"] = max(0.0, elapsed - cloud_seconds)
            self.metrics["cloud_excluded_seconds"] += cloud_seconds
            self.metrics["local_seconds"] += event["local_seconds"]
            (directory/"status.json").write_text(json.dumps(event, indent=2), encoding="utf-8")
