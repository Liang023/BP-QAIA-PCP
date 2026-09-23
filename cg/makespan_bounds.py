"""Lower bounds for homogeneous chargers and fixed candidate intervals.

Only LP infeasibility raises the horizon bound. LP feasible solutions are not
treated as integer schedules and no compact-MILP reference value is used.
"""
from bisect import bisect_left
from cg import budget_clock

import gurobipy as gp


def capacity_bound(graph, chargers, deadline, lp_seconds=2.0):
    started = budget_clock.now()
    groups = [list(p.vertex_list) for p in graph.partitions]
    vertices = [v for group in groups for v in group]
    endings = sorted({v.end_time for v in vertices})
    earliest = max(min(v.end_time for v in group) for group in groups)
    # All work released at/after r must fit in [r, makespan] on C chargers.
    jobs = [(min(v.start_time for v in group),
             min(v.end_time-v.start_time for v in group)) for group in groups]
    workload = max(r + sum(p for a, p in jobs if a >= r)/chargers for r, _ in jobs)
    lo = bisect_left(endings, max(earliest, workload)-1e-7)
    if lo == len(endings):
        return dict(earliest_completion=earliest, workload_lower_bound=workload,
                    lower_bound=workload, lp_calls=0, lp_seconds=0.0,
                    lp_status="capacity_infeasible", infeasible_horizons=[],
                    seconds=budget_clock.now()-started)
    report = dict(earliest_completion=earliest, workload_lower_bound=endings[lo],
                  lower_bound=endings[lo], lp_calls=0, lp_seconds=0.0,
                  lp_status="disabled", infeasible_horizons=[], seconds=0.0)
    if lp_seconds <= 0 or budget_clock.now() >= deadline:
        report["seconds"] = budget_clock.now()-started
        return report
    lp_start = budget_clock.now()
    lp_end = min(deadline, lp_start+lp_seconds)
    model = gp.Model("capacity_horizon_relaxation")
    try:
        model.Params.OutputFlag = 0
        model.Params.Threads = 1
        model.Params.Seed = 0
        model.Params.DualReductions = 0
        model.Params.FeasibilityTol = 1e-9
        x = model.addVars(len(vertices), lb=0.0, ub=1.0)
        offset = 0
        for group in groups:
            model.addConstr(gp.quicksum(x[j] for j in range(offset, offset+len(group))) == 1)
            offset += len(group)
        # Occupancy only increases at candidate starts; these rows cover all times.
        for slot in sorted({v.start_time for v in vertices}):
            if budget_clock.now() >= lp_end:
                report["lp_status"] = "time_limit"
                return report
            model.addConstr(gp.quicksum(x[j] for j, v in enumerate(vertices)
                if v.start_time <= slot < v.end_time) <= chargers)
        hi = len(endings)-1
        report["lp_status"] = "complete"
        while lo < hi:
            remaining = lp_end-budget_clock.now()
            if remaining <= 0:
                report["lp_status"] = "time_limit"
                break
            mid = (lo+hi)//2
            horizon = endings[mid]
            for j, v in enumerate(vertices):
                x[j].UB = float(v.end_time <= horizon)
            remaining = lp_end-budget_clock.now()
            if remaining <= 0:
                report["lp_status"] = "time_limit"
                break
            model.Params.TimeLimit = remaining
            model.optimize()
            report["lp_calls"] += 1
            # Do not use a certificate obtained beyond the global BP deadline.
            if budget_clock.now() > deadline:
                report["lp_status"] = "time_limit"
                break
            if model.Status == gp.GRB.INFEASIBLE:
                report["infeasible_horizons"].append(horizon)
                lo = mid+1
                report["lower_bound"] = endings[lo]
            elif model.Status == gp.GRB.OPTIMAL:
                hi = mid
            else:
                report["lp_status"] = ("time_limit" if model.Status == gp.GRB.TIME_LIMIT
                                       else f"gurobi_status_{model.Status}")
                break
        # The report is a lower bound, not a claim that the final horizon is feasible.
        return report
    finally:
        model.dispose()
        report["lp_seconds"] = budget_clock.now()-lp_start
        report["seconds"] = budget_clock.now()-started
