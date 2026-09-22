import time
from types import SimpleNamespace

from cg.column_pool import ColumnPool
from cg.primal_completion import complete_root_pool
from model.edge import Edge
from model.vertex import Vertex


def test_completion_feasible_unique_and_reproducible():
    vertices = [Vertex(i+1) for i in range(4)]
    partitions = [SimpleNamespace(id=i, vertex_list=[v]) for i, v in enumerate(vertices)]
    for p in partitions:
        p.vertex_list[0].associated_partition = p
    graph = SimpleNamespace(vertices=vertices, partitions=partitions,
                            edges=[Edge(vertices[0], vertices[1])])
    pool = ColumnPool()
    added, solutions, attempts = complete_root_pool(graph, 2, {}, pool, None,
                                                   time.perf_counter()+5, 10, 3)
    assert attempts == 10 and solutions
    keys = [tuple(v.id for v in c.vertex_list) for c in added]
    assert len(keys) == len(set(keys))
    for solution in solutions:
        assert len(solution) <= 2
        assert sorted(v.id for c in solution for v in c.vertex_list) == sorted(v.id for v in vertices)
        for c in solution:
            assert not {vertices[0], vertices[1]} <= set(c.vertex_list)
    again, _, _ = complete_root_pool(graph, 2, {}, pool, None, time.perf_counter()+5, 10, 3)
    assert keys == [tuple(v.id for v in c.vertex_list) for c in again]
    expired = complete_root_pool(graph, 2, {}, pool, None, time.perf_counter()-1)
    assert expired == ([], [], 0)
