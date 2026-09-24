"""Improve a validated incumbent by rescheduling a small subset of vehicles.

This is a primal heuristic on the original graph. Its bound/status must never
be used as a bound or infeasibility certificate for the full BP problem.
"""
import math
import random

from cg import budget_clock
from cg.column_independent_set import ColumnIndependentSet


def improve_incumbent(graph, charger_num, incumbent, upper_bound, deadline,
                      seconds, free_vehicles, seed, on_candidate, statistics=None):
    import gurobipy as gp

    started = budget_clock.now()
    end = min(deadline, started + seconds)
    info = {} if statistics is None else statistics
    info.update(status="skipped", free_vehicles=0, variables=0, candidates=0)
    # Candidate times are integer slots in the EV input schema.
    target = math.ceil(upper_bound - 1e-6) - 1
    rows = [list(c.vertex_list) for c, x in incumbent.items() if x > 0.5]
    rows.extend([] for _ in range(charger_num - len(rows)))
    chosen = {v.associated_partition.id: v for row in rows for v in row}
    critical = {p for p, v in chosen.items() if v.end_time > target}
    count = min(free_vehicles, len(chosen) - 1)
    if count < len(critical) or count < 1:
        return info
    rng = random.Random(seed)
    # Alternate a bottleneck-oriented neighborhood and a randomized one.
    others = [p for p in chosen if p not in critical]
    if seed % 2:
        rng.shuffle(others)
    else:
        windows = [chosen[p] for p in critical]
        others.sort(key=lambda p: (
            -sum(max(0, min(chosen[p].end_time, w.end_time)
                     - max(chosen[p].start_time, w.start_time)) for w in windows),
            -chosen[p].end_time, rng.random()))
    released = critical | set(others[:count-len(critical)])
    fixed = [[v for v in row if v.associated_partition.id not in released] for row in rows]
    info["free_vehicles"] = len(released)
    adjacency = {v.id: set() for v in graph.vertices}
    for edge in graph.edges:
        adjacency[edge.source.id].add(edge.target.id)
        adjacency[edge.target.id].add(edge.source.id)
    options = {p: [] for p in released}
    for partition in graph.partitions:
        if partition.id not in released:
            continue
        for v in partition.vertex_list:
            if v.end_time > target:
                continue
            for k, row in enumerate(fixed):
                if all(u.id not in adjacency[v.id] for u in row):
                    options[partition.id].append((v, k))
    if any(not choices for choices in options.values()) or budget_clock.now() >= end:
        return info
    model = gp.Model("incumbent_neighborhood")
    errors = []
    try:
        model.Params.OutputFlag = 0
        model.Params.Threads = 1
        model.Params.Seed = seed
        model.Params.MIPGap = 0.0
        model.Params.MIPGapAbs = 0.0
        model.Params.MIPFocus = 1
        decisions = [(v, k, model.addVar(vtype=gp.GRB.BINARY))
                     for p in sorted(options) for v, k in options[p]]
        by_vehicle = {p: [] for p in released}
        by_slot = {}
        for v, k, x in decisions:
            by_vehicle[v.associated_partition.id].append((v, x))
            by_slot[v.id, k] = x
        fixed_end = max((v.end_time for row in fixed for v in row), default=0)
        makespan = model.addVar(lb=fixed_end, ub=target)
        for values in by_vehicle.values():
            model.addConstr(gp.quicksum(x for _, x in values) == 1)
            model.addConstr(gp.quicksum(v.end_time*x for v, x in values) <= makespan)
        for edge in graph.edges:
            u, v = edge.source, edge.target
            if u.associated_partition.id == v.associated_partition.id:
                continue  # Enforced by the vehicle assignment equality.
            for k in range(charger_num):
                if (u.id, k) in by_slot and (v.id, k) in by_slot:
                    model.addConstr(by_slot[u.id, k] + by_slot[v.id, k] <= 1)
        model.setObjective(makespan, gp.GRB.MINIMIZE)
        info["variables"] = len(decisions)
        variables = [x for _, _, x in decisions]

        def deliver(values):
            bins = [list(row) for row in fixed]
            for (v, k, _), value in zip(decisions, values):
                if value > 0.5:
                    bins[k].append(v)
            solution = {ColumnIndependentSet(sorted(row, key=lambda v: v.id),
                        "incumbent_neighborhood", False, "primal_neighborhood"): 1.0
                        for row in bins if row}
            objective = max(v.end_time for row in bins for v in row)
            info["candidates"] += 1
            on_candidate(solution, objective)

        def callback(m, where):
            if where == gp.GRB.Callback.MIPSOL:
                if budget_clock.now() >= end:
                    m.terminate()
                    return
                try:
                    deliver(m.cbGetSolution(variables))
                except Exception as exc:
                    errors.append(exc)
                    m.terminate()

        remaining = end - budget_clock.now()
        if remaining <= 0:
            return info
        model.Params.TimeLimit = remaining
        model.optimize(callback)
        if errors:
            raise errors[0]
        info["status"] = str(model.Status)
        if model.SolCount and info["candidates"] == 0 and budget_clock.now() < deadline:
            deliver([x.X for x in variables])
        return info
    finally:
        model.dispose()
