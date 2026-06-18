import json
from pathlib import Path
from src.config import PROCESSED_DATA_DIR
from src.graph.adjacency_list import AdjacencyListGraph


class CollaborationGraphBuilder:
    """
    Constrói os 4 grafos de colaboração exigidos pelo trabalho prático.

    Grafos gerados:
        graph_comments  (Grafo 1) — comentários em issues e PRs
        graph_closings  (Grafo 2) — fechamento de issue por outro usuário
        graph_reviews   (Grafo 3) — revisões, aprovações e merges de PRs
        graph           (integrado) — combinação ponderada de todas as interações

    Pesos do enunciado:
        Comentário em issue ou PR          → 2
        Abertura de issue comentada        → 3  (extra sobre o comentário)
        Revisão / aprovação de PR          → 4
        Merge de PR                        → 5
    """

    # Bots conhecidos que devem ser ignorados por padrão
    KNOWN_BOTS = {"dependabot", "plane-bot", "github-actions", "github-bot",
                  "codecov", "codecov-io", "stale", "allcontributors"}

    def __init__(self, exclude_bots=True):
        self.exclude_bots = exclude_bots
        self.graph          = None   # Grafo integrado
        self.graph_comments = None   # Grafo 1
        self.graph_closings = None   # Grafo 2
        self.graph_reviews  = None   # Grafo 3
        self.username_to_id = {}     # mapeamento do grafo integrado (para save/load)

    # ── Ponto de entrada principal ────────────────────────────────────────────

    def build_from_mined_data(self, data):
        """
        Constrói os 4 grafos e retorna o integrado.
        Mantém compatibilidade com o main.py existente.
        """
        self.graph_comments = self._build_graph_comments(data)
        self.graph_closings = self._build_graph_closings(data)
        self.graph_reviews  = self._build_graph_reviews(data)
        self.graph          = self._build_integrated_graph(data)

        print(f"[INFO] Grafo 1 (comentários):  {self.graph_comments.getVertexCount()} nós, "
              f"{self.graph_comments.getEdgeCount()} arestas")
        print(f"[INFO] Grafo 2 (fechamentos):  {self.graph_closings.getVertexCount()} nós, "
              f"{self.graph_closings.getEdgeCount()} arestas")
        print(f"[INFO] Grafo 3 (revisões/PRs): {self.graph_reviews.getVertexCount()} nós, "
              f"{self.graph_reviews.getEdgeCount()} arestas")
        print(f"[INFO] Grafo integrado:        {self.graph.getVertexCount()} nós, "
              f"{self.graph.getEdgeCount()} arestas")

        return self.graph

    # ── Helpers internos ──────────────────────────────────────────────────────

    def _is_bot(self, username, user_type):
        """Retorna True se o usuário deve ser filtrado como bot."""
        if not self.exclude_bots:
            return False
        if user_type == "Bot":
            return True
        if "[bot]" in username.lower():
            return True
        if username.lower() in self.KNOWN_BOTS:
            return True
        return False

    def _collect_users(self, data):
        """
        Varre todos os itens e devolve um dict {username: {avatar, type}}
        com todos os usuários válidos (sem bots filtrados).
        """
        users = {}

        def reg(username, avatar, utype):
            if not username or username == "ghost":
                return
            if self._is_bot(username, utype):
                return
            if username not in users:
                users[username] = {"avatar": avatar, "type": utype}

        items = data.get("issues", []) + data.get("prs", [])
        for item in items:
            reg(item.get("author"), item.get("author_avatar", ""), item.get("author_type", "User"))
            for c in item.get("comments", []):
                reg(c.get("author"), c.get("author_avatar", ""), c.get("author_type", "User"))
            for r in item.get("reviews", []):
                reg(r.get("author"), r.get("author_avatar", ""), r.get("author_type", "User"))
            if item.get("closed_by"):
                reg(item["closed_by"], "", "User")
            if item.get("merged_by"):
                reg(item["merged_by"], "", "User")

        return users

    def _build_graph_from_edges(self, users, edge_weights, store_id_map=False):
        """
        Cria um AdjacencyListGraph a partir de dicionários de usuários e pesos de arestas.

        Args:
            users:        {username: {avatar, type}}
            edge_weights: {(source_username, target_username): peso_float}
            store_id_map: Se True, atualiza self.username_to_id (usado no grafo integrado).
        """
        unique_users = list(users.keys())
        g = AdjacencyListGraph(len(unique_users))
        local_map = {}

        for i, username in enumerate(unique_users):
            local_map[username] = i
            g.setVertexLabel(i, username)

        if store_id_map:
            self.username_to_id = local_map

        for (source, target), weight in edge_weights.items():
            if source in local_map and target in local_map:
                u = local_map[source]
                v = local_map[target]
                g.addEdge(u, v)
                g.setEdgeWeight(u, v, weight)

        return g

    # ── Grafo 1 — comentários ─────────────────────────────────────────────────

    def _build_graph_comments(self, data):
        """
        Grafo 1: A comentou em issue ou PR de B → aresta A→B, peso 2 por comentário.
        Cobre tanto issues quanto pull requests.
        """
        users = self._collect_users(data)
        edges = {}  # {(source, target): peso}

        items = data.get("issues", []) + data.get("prs", [])
        for item in items:
            author = item.get("author")
            if not author or author not in users:
                continue
            for comment in item.get("comments", []):
                commenter = comment.get("author")
                if not commenter or commenter not in users:
                    continue
                if commenter == author:
                    continue
                pair = (commenter, author)
                edges[pair] = edges.get(pair, 0.0) + 2.0

        return self._build_graph_from_edges(users, edges)

    # ── Grafo 2 — fechamento de issue ─────────────────────────────────────────

    def _build_graph_closings(self, data):
        """
        Grafo 2: A fechou a issue de B → aresta A→B, peso 3.
        Requer que o miner colete o campo 'closed_by' nas issues.
        """
        users = self._collect_users(data)
        edges = {}

        for issue in data.get("issues", []):
            author    = issue.get("author")
            closed_by = issue.get("closed_by")

            if not closed_by or not author:
                continue
            if closed_by == author:
                continue
            if author not in users or closed_by not in users:
                continue

            pair = (closed_by, author)
            edges[pair] = edges.get(pair, 0.0) + 3.0

        return self._build_graph_from_edges(users, edges)

    # ── Grafo 3 — revisões e merges de PRs ───────────────────────────────────

    def _build_graph_reviews(self, data):
        """
        Grafo 3:
          - A revisou/aprovou PR de B → aresta A→B, peso 4 por revisão.
          - A fez merge do PR de B   → aresta A→B, peso 5 por merge.
        Requer que o miner colete 'reviews', 'merged' e 'merged_by' nos PRs.
        """
        users = self._collect_users(data)
        edges = {}

        for pr in data.get("prs", []):
            author = pr.get("author")
            if not author or author not in users:
                continue

            # Revisões e aprovações — peso 4
            for review in pr.get("reviews", []):
                reviewer = review.get("author")
                if not reviewer or reviewer not in users:
                    continue
                if reviewer == author:
                    continue
                pair = (reviewer, author)
                edges[pair] = edges.get(pair, 0.0) + 4.0

            # Merge — peso 5
            merged_by = pr.get("merged_by")
            if merged_by and pr.get("merged") and merged_by != author:
                if merged_by in users:
                    pair = (merged_by, author)
                    edges[pair] = edges.get(pair, 0.0) + 5.0

        return self._build_graph_from_edges(users, edges)

    # ── Grafo integrado ───────────────────────────────────────────────────────

    def _build_integrated_graph(self, data):
        """
        Grafo integrado: todos os tipos de interação com pesos combinados.

        Regras de peso:
          - Comentário em issue ou PR:                   +2
          - Issue que recebeu comentário externo (autor): +1 extra por comentador
              (totalizando peso 3 = 2 base + 1 extra, conforme "abertura de issue comentada")
          - Revisão / aprovação de PR:                   +4
          - Merge de PR:                                 +5
          - Fechamento de issue por outro:               +3
        """
        users = self._collect_users(data)
        edges = {}
        contributions = {u: 0 for u in users}  # VertexWeight = participações totais

        items = data.get("issues", []) + data.get("prs", [])
        for item in items:
            author  = item.get("author")
            is_pr   = item.get("is_pr", False)

            if not author or author not in users:
                continue

            contributions[author] += 1  # ponto por abrir o item

            # Identificar se a issue recebeu comentário de alguém externo
            external_commenters = set()
            for comment in item.get("comments", []):
                commenter = comment.get("author")
                if commenter and commenter in users and commenter != author:
                    external_commenters.add(commenter)

            # Peso 2: comentários (issues e PRs)
            for comment in item.get("comments", []):
                commenter = comment.get("author")
                if not commenter or commenter not in users or commenter == author:
                    continue
                contributions[commenter] += 1
                pair = (commenter, author)
                edges[pair] = edges.get(pair, 0.0) + 2.0

            # Peso extra +1 (= 3 total) para issues comentadas por outros
            if not is_pr and external_commenters:
                for commenter in external_commenters:
                    pair = (commenter, author)
                    edges[pair] = edges.get(pair, 0.0) + 1.0

            if is_pr:
                # Peso 4: revisões e aprovações
                for review in item.get("reviews", []):
                    reviewer = review.get("author")
                    if not reviewer or reviewer not in users or reviewer == author:
                        continue
                    contributions[reviewer] += 1
                    pair = (reviewer, author)
                    edges[pair] = edges.get(pair, 0.0) + 4.0

                # Peso 5: merge
                merged_by = item.get("merged_by")
                if merged_by and item.get("merged") and merged_by != author and merged_by in users:
                    contributions[merged_by] += 1
                    pair = (merged_by, author)
                    edges[pair] = edges.get(pair, 0.0) + 5.0
            else:
                # Peso 3: fechamento de issue
                closed_by = item.get("closed_by")
                if closed_by and closed_by != author and closed_by in users:
                    contributions[closed_by] += 1
                    pair = (closed_by, author)
                    edges[pair] = edges.get(pair, 0.0) + 3.0

        g = self._build_graph_from_edges(users, edges, store_id_map=True)

        # Aplicar contribuições como VertexWeight
        for username, count in contributions.items():
            uid = self.username_to_id.get(username)
            if uid is not None:
                g.setVertexWeight(uid, float(count))

        return g

    # ── Compatibilidade / acesso ──────────────────────────────────────────────

    def get_custom_graph(self):
        """Retorna o grafo integrado."""
        return self.graph

    def get_all_graphs(self):
        """
        Retorna os 4 grafos como dicionário.
        Útil para exportação separada no main.py.
        """
        return {
            "comments":   self.graph_comments,
            "closings":   self.graph_closings,
            "reviews":    self.graph_reviews,
            "integrated": self.graph,
        }

    # ── Persistência ──────────────────────────────────────────────────────────

    def save_graph_state(self, filepath=None):
        """Salva o grafo integrado em JSON para reconstrução posterior."""
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
        print(f"[INFO] Estado do grafo salvo em: {Path(path).name}")

    def load_graph_state(self, filepath=None):
        """Reconstrói o grafo integrado a partir de um JSON salvo."""
        path = filepath or PROCESSED_DATA_DIR / "graph_state.json"
        if not Path(path).exists():
            raise FileNotFoundError(f"Arquivo de estado não encontrado: {path}")

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
            u, v, w = edge["source"], edge["target"], edge["weight"]
            self.graph.addEdge(u, v)
            self.graph.setEdgeWeight(u, v, float(w))

        print(f"[INFO] Grafo carregado com {self.graph.getVertexCount()} nós.")
        return self.graph
    