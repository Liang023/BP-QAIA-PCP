"""Root primal repair using existing LP and incumbent columns."""

import random

from cg import budget_clock
from cg.column_independent_set import ColumnIndependentSet


def complete_root_pool(graph, charger_num, lp_solution, pool, pricing_problem,
                       deadline, attempts=20, seed=0, incumbent=None,
                       upper_bound=float("inf")):
    """Destroy part of a schedule and refill missing vehicles.

    Only complete schedules add columns. These columns improve the primal side
    and do not certify a lower bound.
    """
    rng = random.Random(seed)
    adjacency = {v.id: set() for v in graph.vertices}
    for edge in graph.edges:
        adjacency[edge.source.id].add(edge.target.id)
        adjacency[edge.target.id].add(edge.source.id)
    signature = lambda c: tuple(sorted(v.id for v in c.vertex_list))
    known = {signature(c): c for c in pool.columns if not c.is_artificial_column}
    lp_columns = [(c, x) for c, x in lp_solution.items()
                  if not c.is_artificial_column and x > 1e-6]
    incumbent_columns = [(c, 1.0) for c in (incumbent or {})]
    added, schedules = [], []
    completed_attempts = 0
    for attempt in range(attempts):
        if budget_clock.now() >= deadline:
            break
        use_incumbent = bool(incumbent_columns) and attempt % 2 == 0
        candidates = incumbent_columns if use_incumbent else lp_columns
        keep = min(charger_num - 1, max(0, charger_num - 1 - attempt // 4))
        if use_incumbent:
            # Drop the latest-finishing incumbent column first.
            ranked = sorted(candidates, key=lambda cx: (
                max(v.end_time for v in cx[0].vertex_list), rng.random()))
        else:
            ranked = sorted(candidates, key=lambda cx: -(cx[1] + rng.random() * 0.25))
        bins = [[] for _ in range(charger_num)]
        covered = set()
        fixed = 0
        for column, _ in ranked:
            if fixed >= keep:
                break
            partitions = {v.associated_partition.id for v in column.vertex_list}
            if partitions & covered or any(v.end_time >= upper_bound for v in column.vertex_list):
                continue
            bins[fixed] = list(column.vertex_list)
            covered.update(partitions)
            fixed += 1
        remaining = [p for p in graph.partitions if p.id not in covered]
        remaining.sort(key=lambda p: (
            sum(v.end_time < upper_bound for v in p.vertex_list),
            len(p.vertex_list) * (0.75 + rng.random() * 0.5)))
        for partition in remaining:
            if budget_clock.now() >= deadline:
                break
            options = []
            for vertex in partition.vertex_list:
                if vertex.end_time >= upper_bound:
                    continue
                for k, vertices in enumerate(bins):
                    if all(u.id not in adjacency[vertex.id] for u in vertices):
                        options.append((vertex.end_time, len(vertices), rng.random(), k, vertex))
            if not options:
                break
            options.sort(key=lambda option: option[:3])
            _, _, _, k, vertex = options[rng.randrange(min(3, len(options)))]
            bins[k].append(vertex)
            covered.add(partition.id)
        completed_attempts += 1
        if len(covered) != len(graph.partitions):
            continue
        columns = []
        for vertices in bins:
            if not vertices:
                continue
            key = tuple(sorted(v.id for v in vertices))
            if key not in known:
                column = ColumnIndependentSet(sorted(vertices, key=lambda v: v.id),
                    pricing_problem, False, "primal_repair", 0.0)
                known[key] = column
                added.append(column)
            columns.append(known[key])
        schedules.append({c: 1.0 for c in columns})
    return added, schedules, completed_attempts
