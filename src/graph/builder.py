import json
from pathlib import Path
from src.config import PROCESSED_DATA_DIR
from src.graph.adjacency_list import AdjacencyListGraph

class CollaborationGraphBuilder:
    """Construtor de grafos de colaboração direcionados e ponderados utilizando a API customizada."""

    def __init__(self, exclude_bots=True):
        self.exclude_bots = exclude_bots
        self.graph = None
        self.username_to_id = {}

    def build_from_mined_data(self, data):
        """
        Gera um grafo direcionado com base nos dados obtidos da mineração.
        - Nó: Contribuidor (usuário).
        - Aresta A -> B: Usuário A comentou/revisou um PR/Issue criado por B.
        - Peso: Quantidade de interações de A no conteúdo de B.
        """
        # Juntar issues e PRs para iteração unificada
        items = data.get("issues", []) + data.get("prs", [])
        
        # Dicionários auxiliares de metadados para nós
        user_avatars = {}
        user_types = {}
        user_contributions = {} # Contagem de participações ativas

        # Dicionário temporário para contar interações A -> B
        # Estrutura: {(A, B): {"comments": 0, "reviews": 0}}
        edge_interactions = {}

        def register_user(username, avatar_url, user_type):
            if not username:
                return False
            # Filtro opcional de bots
            if self.exclude_bots and (user_type == "Bot" or "[bot]" in username.lower() or username == "dependabot"):
                return False
            if username not in user_avatars:
                user_avatars[username] = avatar_url
                user_types[username] = user_type
                user_contributions[username] = 0
            return True

        for item in items:
            author = item.get("author")
            author_avatar = item.get("author_avatar", "")
            author_type = item.get("author_type", "User")
            
            # Registrar autor
            if not register_user(author, author_avatar, author_type):
                continue
                
            # Autor ganha 1 ponto por abrir a Issue/PR
            user_contributions[author] += 1
            
            # 1. Processar comentários da Issue/PR
            for comment in item.get("comments", []):
                commenter = comment.get("author")
                commenter_avatar = comment.get("author_avatar", "")
                commenter_type = comment.get("author_type", "User")
                
                if not register_user(commenter, commenter_avatar, commenter_type):
                    continue
                
                # O comentador ganha 1 ponto por interagir
                user_contributions[commenter] += 1
                
                # Ignorar auto-interação (comentando no próprio post)
                if commenter != author:
                    pair = (commenter, author)
                    if pair not in edge_interactions:
                        edge_interactions[pair] = {"comments": 0, "reviews": 0}
                    edge_interactions[pair]["comments"] += 1

            # 2. Processar revisões de PRs
            for review in item.get("reviews", []):
                reviewer = review.get("author")
                reviewer_avatar = review.get("author_avatar", "")
                reviewer_type = review.get("author_type", "User")
                
                if not register_user(reviewer, reviewer_avatar, reviewer_type):
                    continue
                
                # O revisor ganha 1 ponto
                user_contributions[reviewer] += 1
                
                # Ignorar auto-revisão
                if reviewer != author:
                    pair = (reviewer, author)
                    if pair not in edge_interactions:
                        edge_interactions[pair] = {"comments": 0, "reviews": 0}
                    edge_interactions[pair]["reviews"] += 1

        # Agora que temos todos os usuários únicos, inicializamos o grafo
        unique_users = list(user_avatars.keys())
        num_vertices = len(unique_users)
        
        self.graph = AdjacencyListGraph(num_vertices)
        
        # Mapeamento e Atributos de Vértices
        for i, username in enumerate(unique_users):
            self.username_to_id[username] = i
            self.graph.setVertexLabel(i, username)
            self.graph.setVertexWeight(i, float(user_contributions[username]))

        # Adicionar arestas direcionadas com pesos
        for (source, target), metrics in edge_interactions.items():
            if source in self.username_to_id and target in self.username_to_id:
                u = self.username_to_id[source]
                v = self.username_to_id[target]
                
                # Peso consolidado (Comentário: peso 2, Revisão: peso 4) como exigido no documento
                # Vamos simplificar para a soma ou aplicar os pesos se desejado
                # O documento diz: "Comentário em issue ou pull request: peso 2; Revisão/aprovação de pull request: peso 4"
                total_weight = float(metrics["comments"] * 2 + metrics["reviews"] * 4)
                
                self.graph.addEdge(u, v)
                self.graph.setEdgeWeight(u, v, total_weight)

        print(f"[INFO] Grafo construído com {self.graph.getVertexCount()} nós e {self.graph.getEdgeCount()} arestas.")
        return self.graph

    def get_custom_graph(self):
        """Retorna o objeto AbstractGraph gerado."""
        return self.graph

    def save_graph_state(self, filepath=None):
        """Salva a estrutura e atributos do grafo atual em um arquivo JSON compatível."""
        path = filepath or PROCESSED_DATA_DIR / "graph_state.json"
        
        if not self.graph:
            return
            
        data = {
            "num_vertices": self.graph.getVertexCount(),
            "nodes": [],
            "edges": []
        }
        
        for i in range(self.graph.getVertexCount()):
            data["nodes"].append({
                "id": i,
                "label": self.graph.getVertexLabel(i),
                "weight": self.graph.getVertexWeight(i)
            })
            
        for u in range(self.graph.getVertexCount()):
            for v in range(self.graph.getVertexCount()):
                if self.graph.hasEdge(u, v):
                    data["edges"].append({
                        "source": u,
                        "target": v,
                        "weight": self.graph.getEdgeWeight(u, v)
                    })
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Estado do grafo salvo com sucesso em: {Path(path).name}")

    def load_graph_state(self, filepath=None):
        """Carrega e reconstrói o grafo a partir de um arquivo JSON anteriormente salvo."""
        path = filepath or PROCESSED_DATA_DIR / "graph_state.json"
        
        if not Path(path).exists():
            raise FileNotFoundError(f"Arquivo de estado do grafo não encontrado: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        num_vertices = data.get("num_vertices", 0)
        self.graph = AdjacencyListGraph(num_vertices)
        self.username_to_id = {}
        
        for node in data.get("nodes", []):
            i = node["id"]
            username = node["label"]
            self.graph.setVertexLabel(i, username)
            self.graph.setVertexWeight(i, float(node["weight"]))
            self.username_to_id[username] = i
            
        for edge in data.get("edges", []):
            u = edge["source"]
            v = edge["target"]
            w = edge["weight"]
            self.graph.addEdge(u, v)
            self.graph.setEdgeWeight(u, v, float(w))
            
        print(f"[INFO] Grafo carregado com sucesso contendo {self.graph.getVertexCount()} nós.")
        return self.graph
