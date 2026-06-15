import pytest
import json
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
    with open(json_file, "r") as f:
        data = json.load(f)
        assert "nodes" in data
        assert "links" in data


# ==========================================
# TESTES - PERSISTÊNCIA DO GRAFO (save/load)
# ==========================================

def test_save_and_load_graph_state(tmp_path):
    """Testa a persistência (save/load) do estado do grafo integrado."""
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
                    {"author": "dmontagu", "author_avatar": "avatar_d", "author_type": "User"}
                ]
            }
        ],
        "prs": []
    }

    builder = CollaborationGraphBuilder(exclude_bots=True)
    builder.build_from_mined_data(test_data)

    state_file = tmp_path / "graph_state.json"
    builder.save_graph_state(state_file)
    assert state_file.exists()

    # Recarregar em um builder novo
    new_builder = CollaborationGraphBuilder()
    g2 = new_builder.load_graph_state(state_file)

    assert g2.getVertexCount() == builder.graph.getVertexCount()
    assert g2.getEdgeCount() == builder.graph.getEdgeCount()

    labels = [g2.getVertexLabel(i) for i in range(g2.getVertexCount())]
    assert "tiangolo" in labels
    assert "dmontagu" in labels


def test_load_graph_state_missing_file_raises(tmp_path):
    """load_graph_state deve levantar FileNotFoundError se o arquivo não existir."""
    builder = CollaborationGraphBuilder()
    with pytest.raises(FileNotFoundError):
        builder.load_graph_state(tmp_path / "nao_existe.json")


# ==========================================
# TESTES - GRAFO INTEGRADO (fechamento e merge)
# ==========================================

def test_integrated_graph_closing_and_merge_weights():
    """Testa os pesos de fechamento de issue (3) e merge de PR (5) no grafo integrado."""
    test_data = {
        "issues": [
            {
                "number": 1,
                "title": "Bug report",
                "author": "alice",
                "author_avatar": "avatar_a",
                "author_type": "User",
                "is_pr": False,
                "comments": [],
                "closed_by": "bob"
            }
        ],
        "prs": [
            {
                "number": 2,
                "title": "Fix bug",
                "author": "alice",
                "author_avatar": "avatar_a",
                "author_type": "User",
                "is_pr": True,
                "comments": [],
                "reviews": [],
                "merged": True,
                "merged_by": "bob"
            }
        ]
    }

    builder = CollaborationGraphBuilder(exclude_bots=True)
    g = builder.build_from_mined_data(test_data)

    labels = [g.getVertexLabel(i) for i in range(g.getVertexCount())]
    id_a = labels.index("alice")
    id_b = labels.index("bob")

    # bob fechou a issue de alice (peso 3) e fez merge do PR de alice (peso 5)
    # Aresta bob -> alice deve ter peso total 3 + 5 = 8
    assert g.hasEdge(id_b, id_a)
    assert g.getEdgeWeight(id_b, id_a) == 8.0

    # Grafo 2 (fechamentos) deve conter a aresta bob -> alice com peso 3
    labels2 = [builder.graph_closings.getVertexLabel(i) for i in range(builder.graph_closings.getVertexCount())]
    id2_b, id2_a = labels2.index("bob"), labels2.index("alice")
    assert builder.graph_closings.hasEdge(id2_b, id2_a)
    assert builder.graph_closings.getEdgeWeight(id2_b, id2_a) == 3.0

    # Grafo 3 (revisões/merges) deve conter a aresta bob -> alice com peso 5
    labels3 = [builder.graph_reviews.getVertexLabel(i) for i in range(builder.graph_reviews.getVertexCount())]
    id3_b, id3_a = labels3.index("bob"), labels3.index("alice")
    assert builder.graph_reviews.hasEdge(id3_b, id3_a)
    assert builder.graph_reviews.getEdgeWeight(id3_b, id3_a) == 5.0


def test_get_all_graphs_returns_four_graphs():
    """get_all_graphs deve retornar os 4 grafos esperados após a construção."""
    test_data = {
        "issues": [
            {
                "number": 1,
                "title": "Bug report",
                "author": "alice",
                "author_avatar": "avatar_a",
                "author_type": "User",
                "is_pr": False,
                "comments": [
                    {"author": "bob", "author_avatar": "avatar_b", "author_type": "User"}
                ]
            }
        ],
        "prs": []
    }

    builder = CollaborationGraphBuilder(exclude_bots=True)
    builder.build_from_mined_data(test_data)

    graphs = builder.get_all_graphs()
    assert set(graphs.keys()) == {"comments", "closings", "reviews", "integrated"}
    assert graphs["integrated"] is builder.get_custom_graph()


# ==========================================
# TESTES - EXPORTAÇÃO SEM MÉTRICAS
# ==========================================

def test_exporter_with_no_metrics(tmp_path):
    """Testa os exportadores quando centralidades/comunidades não são fornecidas."""
    g = AdjacencyListGraph(2)
    g.setVertexLabel(0, "alice")
    g.setVertexLabel(1, "bob")
    g.addEdge(0, 1)
    g.setEdgeWeight(0, 1, 2.0)

    gexf_file = tmp_path / "no_metrics.gexf"
    json_file = tmp_path / "no_metrics.json"

    exporter.export_to_gexf(g, gexf_file, centralities=None, communities=None)
    exporter.export_to_json(g, json_file, centralities=None, communities=None)

    assert gexf_file.exists()
    assert json_file.exists()

    with open(json_file, "r") as f:
        data = json.load(f)
        assert data["nodes"][0]["id"] == "alice"
        # Sem comunidades informadas, a chave "community" não deve existir
        assert "community" not in data["nodes"][0]


# ==========================================
# TESTES - EXPORTAÇÃO DOS GRAFOS INDIVIDUAIS
# ==========================================

def test_export_individual_graphs_to_json(tmp_path):
    """Testa a exportação dos grafos individuais (comentários, fechamentos, revisões)."""
    g_comments = AdjacencyListGraph(2)
    g_comments.setVertexLabel(0, "alice")
    g_comments.setVertexLabel(1, "bob")
    g_comments.addEdge(0, 1)
    g_comments.setEdgeWeight(0, 1, 2.0)

    g_closings = AdjacencyListGraph(2)
    g_closings.setVertexLabel(0, "alice")
    g_closings.setVertexLabel(1, "bob")

    graphs_dict = {
        "comments": g_comments,
        "closings": g_closings,
        # "reviews" propositalmente ausente, para testar o "continue"
        "integrated": g_comments,
    }

    result = exporter.export_individual_graphs_to_json(graphs_dict, filepath_prefix=tmp_path)

    assert (tmp_path / "collaboration_graph_comments.json").exists()
    assert (tmp_path / "collaboration_graph_closings.json").exists()
    # "reviews" não estava em graphs_dict, então o arquivo não deve ser criado
    assert not (tmp_path / "collaboration_graph_reviews.json").exists()

    with open(tmp_path / "collaboration_graph_comments.json") as f:
        data = json.load(f)
    assert data["nodes"][0]["id"] == "alice"
    assert data["links"][0] == {"source": "alice", "target": "bob", "weight": 2.0}

    # Deve sempre retornar o mapa completo dos 3 nomes possíveis
    assert set(result.keys()) == {"comments", "closings", "reviews"}


def test_export_individual_graphs_to_json_default_path(monkeypatch, tmp_path):
    """Testa o uso do caminho padrão (OUTPUT_DATA_DIR) quando filepath_prefix não é informado."""
    monkeypatch.setattr("src.export.exporter.OUTPUT_DATA_DIR", tmp_path)

    g = AdjacencyListGraph(1)
    g.setVertexLabel(0, "alice")

    graphs_dict = {"comments": g, "closings": g, "reviews": g}
    exporter.export_individual_graphs_to_json(graphs_dict)

    assert (tmp_path / "collaboration_graph_comments.json").exists()
    assert (tmp_path / "collaboration_graph_closings.json").exists()
    assert (tmp_path / "collaboration_graph_reviews.json").exists()