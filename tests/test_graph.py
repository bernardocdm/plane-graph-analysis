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
    """Testa grafo completo."""
    g = graph_class(3)
    g.addEdge(0, 1)
    g.addEdge(0, 2)
    g.addEdge(1, 0)
    g.addEdge(1, 2)
    g.addEdge(2, 0)
    g.addEdge(2, 1)
    
    assert g.isCompleteGraph() == True
    assert g.isConnected() == True


# ==========================================
# TESTES - EDGE CASES
# ==========================================

def test_disconnected_graph(graph_class):
    """Testa isConnected() quando grafo tem componentes desconexos"""
    g = graph_class(4)
    # componentes 
    g.addEdge(0,1)
    g.addEdge(2,3)

    assert g.isConnected() == False

def test_vertex_labels(graph_class):
    """Testa set/get de labels dos vértices."""
    g = graph_class(3)
    g.setVertexLabel(0, "Alice")
    g.setVertexLabel(1, "Bob")
    g.setVertexLabel(2, "Charlie")
    
    assert g.getVertexLabel(0) == "Alice"
    assert g.getVertexLabel(1) == "Bob"
    assert g.getVertexLabel(2) == "Charlie"


def test_remove_nonexistent_edge(graph_class):
    """Testa remoção de aresta que nunca foi adicionada."""
    g = graph_class(3)
    
    # Não lança erro
    g.removeEdge(0, 1)
    assert g.getEdgeCount() == 0


def test_large_complete_graph(graph_class):
    """Testa comportamento com grafo completo maior."""
    g = graph_class(10)
    
    # Adiciona as arestas possíveis
    for i in range(10):
        for j in range(10):
            if i != j:
                g.addEdge(i, j)
    
    # N=10, E = 10*9 = 90
    assert g.getEdgeCount() == 90
    assert g.isCompleteGraph() == True
    assert g.isConnected() == True


def test_edge_weight_default(graph_class):
    """Testa peso padrão de aresta recém adicionada."""
    g = graph_class(2)
    g.addEdge(0, 1)
    
    weight = g.getEdgeWeight(0, 1)
    assert isinstance(weight, (int, float))
    assert weight >= 0


def test_isolated_vertex(graph_class):
    """Testa vértice isolado (sem arestas)."""
    g = graph_class(3)
    g.addEdge(0, 1)
    
    # Vértice 2 está isolado
    assert g.getVertexInDegree(2) == 0
    assert g.getVertexOutDegree(2) == 0
    assert g.isConnected() == False

def test_export_to_gephi(graph_class, tmp_path):
    """Testa a exportação do grafo para o formato GEXF (Gephi)."""
    g = graph_class(2)
    g.setVertexLabel(0, "alice")
    g.setVertexLabel(1, "bob")
    g.setVertexWeight(0, 5.0)
    g.addEdge(0, 1)
    g.setEdgeWeight(0, 1, 3.0)

    path = tmp_path / "out.gexf"
    g.exportToGEPHI(str(path))

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "<gexf" in content
    assert 'label="alice"' in content
    assert 'label="bob"' in content
    assert 'source="0" target="1"' in content