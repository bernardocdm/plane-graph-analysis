import pytest
from pathlib import Path
from src import config
from src.mining.miner import GitHubMiner
from src.graph.builder import CollaborationGraphBuilder
from src import analysis
from src.analysis import analyzer
from src.export import exporter
from src.graph.adjacency_list import AdjacencyListGraph

def test_directories_creation():
    """Testa se as pastas padrão de dados são criadas corretamente."""
    config.init_directories()
    assert config.DATA_DIR.exists()
    assert config.RAW_DATA_DIR.exists()
    assert config.PROCESSED_DATA_DIR.exists()
    assert config.OUTPUT_DATA_DIR.exists()

def test_mock_data_generation():
    """Testa se a geração de dados mock possui todas as chaves e estrutura necessárias."""
    data = GitHubMiner.generate_mock_data()
    assert "repository" in data
    assert "issues" in data
    assert "prs" in data
    assert len(data["issues"]) > 0 or len(data["prs"]) > 0
    
    # Testar formato de uma issue
    first_issue = data["issues"][0]
    assert "number" in first_issue
    assert "author" in first_issue
    assert "comments" in first_issue
    assert "is_pr" in first_issue

def test_graph_builder_and_bot_filtering():
    """Testa se o construtor do grafo monta nós/arestas com pesos certos e filtra bots."""
    # Massa de dados de teste controlada
    test_data = {
        "issues": [
            {
                "number": 1,
                "title": "Bug in API",
                "author": "tiangolo",
                "author_avatar": "avatar_t",
                "author_type": "User",
                "is_pr": False,
                "comments": [
                    {"author": "dmontagu", "author_avatar": "avatar_d", "author_type": "User"},
                    {"author": "dependabot", "author_avatar": "avatar_dep", "author_type": "Bot"}
                ]
            }
        ],
        "prs": [
            {
                "number": 2,
                "title": "Improve docs",
                "author": "dmontagu",
                "author_avatar": "avatar_d",
                "author_type": "User",
                "is_pr": True,
                "comments": [
                    {"author": "tiangolo", "author_avatar": "avatar_t", "author_type": "User"}
                ],
                "reviews": [
                    {"author": "tiangolo", "author_avatar": "avatar_t", "author_type": "User", "state": "APPROVED"}
                ]
            }
        ]
    }
    
    # Caso 1: Excluindo bots
    builder = CollaborationGraphBuilder(exclude_bots=True)
    g = builder.build_from_mined_data(test_data)
    
    # dependabot (Bot) deve ser excluído
    labels = [g.getVertexLabel(i) for i in range(g.getVertexCount())]
    assert "dependabot" not in labels
    assert "tiangolo" in labels
    assert "dmontagu" in labels
    
    id_t = labels.index("tiangolo")
    id_d = labels.index("dmontagu")
    
    # Contribuições
    # tiangolo abriu 1 issue + comentou 1 pr + revisou 1 pr = 3 contribuições
    assert g.getVertexWeight(id_t) == 3.0
    # dmontagu abriu 1 pr + comentou 1 issue = 2 contribuições
    assert g.getVertexWeight(id_d) == 2.0
    
    # Arestas
    # dmontagu comentou no post de tiangolo -> Aresta dmontagu -> tiangolo
    # O documento diz: comentário vale 2.
    assert g.hasEdge(id_d, id_t)
    assert g.getEdgeWeight(id_d, id_t) == 2.0
    
    # tiangolo comentou e revisou no post de dmontagu -> Aresta tiangolo -> dmontagu
    # Comentário (2) + Revisão (4) = 6
    assert g.hasEdge(id_t, id_d)
    assert g.getEdgeWeight(id_t, id_d) == 6.0

def test_analyzer_metrics():
    """Testa se as funções do analisador de rede calculam as centralidades e comunidades sem erros."""
    # Grafo de teste direcionado usando API custom
    g = AdjacencyListGraph(3)
    g.setVertexLabel(0, "A")
    g.setVertexLabel(1, "B")
    g.setVertexLabel(2, "C")
    
    # Arestas direcionadas com pesos
    g.addEdge(0, 1)
    g.setEdgeWeight(0, 1, 3.0)
    g.addEdge(1, 2)
    g.setEdgeWeight(1, 2, 1.0)
    g.addEdge(2, 0)
    g.setEdgeWeight(2, 0, 2.0)
    
    # Testar cálculo de centralidades
    centralities = analyzer.calculate_centralities(g)
    assert "A" in centralities
    assert "in_degree" in centralities["A"]
    assert "pagerank" in centralities["A"]
    
    # Testar detecção de comunidades
    communities = analyzer.detect_communities(g)
    assert "A" in communities
    assert "B" in communities
    
    # Testar estatísticas de rede
    metrics = analyzer.get_network_metrics(g)
    assert metrics["nodes"] == 3
    assert metrics["edges"] == 3
    # Densidade para N=3 é 3 / (3*2) = 0.5
    assert metrics["density"] == 0.5  
    assert metrics["reciprocity"] == 0.0

def test_exporter_runs(tmp_path):
    """Testa se os exportadores salvam arquivos fisicamente sem levantar exceções."""
    g = AdjacencyListGraph(2)
    g.setVertexLabel(0, "tiangolo")
    g.setVertexLabel(1, "dmontagu")
    g.setVertexWeight(0, 15)
    g.setVertexWeight(1, 10)
    
    g.addEdge(1, 0)
    g.setEdgeWeight(1, 0, 4.0)
    
    centralities = analyzer.calculate_centralities(g)
    communities = analyzer.detect_communities(g)
    
    # Arquivos temporários
    gexf_file = tmp_path / "test.gexf"
    json_file = tmp_path / "test.json"
    csv_file = tmp_path / "test.csv"
    
    # Executar exportadores
    exporter.export_to_gexf(g, gexf_file, centralities, communities)
    exporter.export_to_json(g, json_file, centralities, communities)
    exporter.export_metrics_to_csv(centralities, communities, g, csv_file)
    
    # Verificar se foram gerados
    assert gexf_file.exists()
    assert json_file.exists()
    assert csv_file.exists()
    
    # Garantir que o JSON é parseável
    import json
    with open(json_file, "r") as f:
        data = json.load(f)
        assert "nodes" in data
        assert "links" in data
