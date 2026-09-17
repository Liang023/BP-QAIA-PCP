from types import SimpleNamespace

from model.a_graph import AuxiliaryGraph
from model.edge import Edge
from model.vertex import Vertex


def test_auxiliary_edges_preserve_order_and_existing_reversed_edges():
    vertices = [Vertex(1) for _ in range(5)]
    for v, partition in zip(vertices, [0, 1, 0, 1, 0]):
        v.associated_partition = SimpleNamespace(id=partition)
    edges = [Edge(vertices[2], vertices[0]), Edge(vertices[0], vertices[1])]
    graph = SimpleNamespace(edges=edges)
    auxiliary = AuxiliaryGraph(graph, {v.id: v for v in vertices})
    pairs = [(vertices.index(e.source), vertices.index(e.target)) for e in auxiliary.auxiliary_edges]
    assert pairs == [(2, 0), (0, 1), (0, 4), (1, 3), (2, 4)]
    assert len(graph.edges) == 2  # the original graph must remain unchanged


def test_auxiliary_edges_only_use_active_vertices():
    vertices = [Vertex(1) for _ in range(3)]
    partition = SimpleNamespace(id=0, vertex_list=vertices)
    for v in vertices:
        v.associated_partition = partition
    auxiliary = AuxiliaryGraph(SimpleNamespace(edges=[]), {v.id: v for v in vertices[1:]})
    assert [(e.source, e.target) for e in auxiliary.auxiliary_edges] == [(vertices[1], vertices[2])]
