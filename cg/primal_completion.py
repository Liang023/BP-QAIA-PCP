"""Root-only LP-guided schedule completion; never supplies a lower bound."""
import random
import time

from cg.column_independent_set import ColumnIndependentSet


def complete_root_pool(graph, charger_num, lp_solution, pool, pricing_problem,
                       deadline, attempts=20, seed=0):
    """Keep disjoint LP columns, then fill unused chargers with original vertices.

    Every returned column is feasible. Failed completions may still supply useful
    partial columns; only complete schedules may be offered as incumbents.
    """
    rng = random.Random(seed)
    adjacency = {v.id: set() for v in graph.vertices}
    for edge in graph.edges:
        adjacency[edge.source.id].add(edge.target.id)
        adjacency[edge.target.id].add(edge.source.id)
    signature = lambda c: tuple(sorted(v.id for v in c.vertex_list))
    known = {signature(c): c for c in pool.columns if not c.is_artificial_column}
    candidates = [(c, x) for c, x in lp_solution.items()
                  if not c.is_artificial_column and x > 1e-6]
    added, schedules = [], []
    completed_attempts = 0
    for attempt in range(attempts):
        if time.perf_counter() >= deadline:
            break
        # Cycle through no fixing and progressively larger partial LP solutions.
        keep = attempt % max(1, charger_num)
        ranked = sorted(candidates, key=lambda cx: -(cx[1] + rng.random()*0.25))
        bins, covered = [], set()
        for column, _ in ranked:
            if len(bins) >= keep:
                break
            partitions = {v.associated_partition.id for v in column.vertex_list}
            if not partitions & covered:
                bins.append(list(column.vertex_list))
                covered.update(partitions)
        fixed = len(bins)
        bins.extend([] for _ in range(charger_num-fixed))
        remaining = [p for p in graph.partitions if p.id not in covered]
        # Restrictive vehicles first; random perturbation supplies alternative orders.
        remaining.sort(key=lambda p: len(p.vertex_list)*(0.5+rng.random()))
        for partition in remaining:
            if time.perf_counter() >= deadline:
                break
            options = []
            for vertex in partition.vertex_list:
                for k in range(fixed, charger_num):
                    if all(u.id not in adjacency[vertex.id] for u in bins[k]):
                        options.append((vertex.end_time, rng.random(), k, vertex))
            if not options:
                continue
            options.sort(key=lambda option: option[:2])
            _, _, k, vertex = options[rng.randrange(min(3, len(options)))]
            bins[k].append(vertex)
            covered.add(partition.id)
        columns = []
        for vertices in bins:
            if not vertices:
                continue
            key = tuple(sorted(v.id for v in vertices))
            if key not in known:
                column = ColumnIndependentSet(sorted(vertices, key=lambda v: v.id),
                    pricing_problem, False, "primal_completion", 0.0)
                known[key] = column
                added.append(column)
            columns.append(known[key])
        completed_attempts += 1
        if len(covered) == len(graph.partitions):
            schedules.append({c: 1.0 for c in columns})
    return added, schedules, completed_attempts
