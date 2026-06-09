import pytest
from src.graph.adjacency_matrix import AdjacencyMatrixGraph
from src.graph.adjacency_list import AdjacencyListGraph

@pytest.fixture(params=[AdjacencyMatrixGraph, AdjacencyListGraph])
def graph_class(request):
    return request.param

def test_graph_initialization(graph_class):
    g = graph_class(5)
    assert g.getVertexCount() == 5
    assert g.getEdgeCount() == 0
    assert g.isEmptyGraph() == True
    assert g.isCompleteGraph() == False

def test_add_edge_and_counts(graph_class):
    g = graph_class(3)
    g.addEdge(0, 1)
    
    assert g.hasEdge(0, 1) == True
    assert g.hasEdge(1, 0) == False
    assert g.getEdgeCount() == 1
    assert g.isEmptyGraph() == False
    
    # Test idempotency
    g.addEdge(0, 1)
    assert g.getEdgeCount() == 1

def test_remove_edge(graph_class):
    g = graph_class(3)
    g.addEdge(0, 1)
    g.removeEdge(0, 1)
    
    assert g.hasEdge(0, 1) == False
    assert g.getEdgeCount() == 0

def test_self_loop_raises_error(graph_class):
    g = graph_class(3)
    with pytest.raises(ValueError):
        g.addEdge(1, 1)

def test_invalid_vertex_raises_error(graph_class):
    g = graph_class(2)
    with pytest.raises(IndexError):
        g.addEdge(0, 2)
        
    with pytest.raises(IndexError):
        g.hasEdge(-1, 0)

def test_weights(graph_class):
    g = graph_class(3)
    g.addEdge(0, 1)
    g.setEdgeWeight(0, 1, 3.5)
    
    assert g.getEdgeWeight(0, 1) == 3.5
    
    g.setVertexWeight(0, 10.0)
    assert g.getVertexWeight(0) == 10.0

def test_degree(graph_class):
    g = graph_class(4)
    g.addEdge(0, 1)
    g.addEdge(0, 2)
    g.addEdge(3, 1)
    
    assert g.getVertexOutDegree(0) == 2
    assert g.getVertexInDegree(1) == 2
    assert g.getVertexOutDegree(3) == 1
    assert g.getVertexInDegree(2) == 1
    assert g.getVertexInDegree(0) == 0

def test_relations(graph_class):
    g = graph_class(4)
    g.addEdge(0, 1)
    g.addEdge(0, 2)
    g.addEdge(3, 1)
    
    assert g.isSucessor(0, 1) == True
    assert g.isPredessor(1, 0) == True
    assert g.isDivergent(0, 1, 0, 2) == True
    assert g.isDivergent(0, 1, 3, 1) == False
    assert g.isConvergent(0, 1, 3, 1) == True
    assert g.isIncident(0, 1, 0) == True
    assert g.isIncident(0, 1, 1) == True
    assert g.isIncident(0, 1, 2) == False

def test_complete_graph(graph_class):
    g = graph_class(3)
    g.addEdge(0, 1)
    g.addEdge(0, 2)
    g.addEdge(1, 0)
    g.addEdge(1, 2)
    g.addEdge(2, 0)
    g.addEdge(2, 1)
    
    assert g.isCompleteGraph() == True
    assert g.isConnected() == True
