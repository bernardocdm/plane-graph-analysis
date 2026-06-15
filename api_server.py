# Roda em: http://localhost:8000
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Path absoluto relativo ao arquivo
DATA_DIR = Path(__file__).parent / "data/outputs"
HOST = "127.0.0.1"
PORT = 8000

app = FastAPI(title="FastAPI Graph Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/api/graph")
def get_graph():
    """Retorna o grafo completo (nós com métricas + arestas)."""
    file_path = DATA_DIR / "collaboration_graph.json"
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Execute primeiro: python main.py --use-mock"
        )
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/graph/comments")
def get_graph_comments():
    """Retorna o grafo de comentários."""
    file_path = DATA_DIR / "collaboration_graph_comments.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Grafo de comentários não encontrado")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/graph/closings")
def get_graph_closings():
    """Retorna o grafo de fechamentos de issue."""
    file_path = DATA_DIR / "collaboration_graph_closings.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Grafo de fechamentos não encontrado")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/graph/reviews")
def get_graph_reviews():
    """Retorna o grafo de reviews/merges de PRs."""
    file_path = DATA_DIR / "collaboration_graph_reviews.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Grafo de reviews não encontrado")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.get("/api/metrics")
def get_metrics():
    """Retorna métricas globais da rede calculadas do grafo."""
    file_path = DATA_DIR / "collaboration_graph.json"
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Execute primeiro: python main.py --use-mock"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    nodes = [n["id"] for n in graph_data["nodes"]]
    links = graph_data["links"]
    num_nodes = len(nodes)
    num_edges = len(links)

    adj_out = {n: set() for n in nodes}
    adj_in  = {n: set() for n in nodes}
    for link in links:
        s, t = link["source"], link["target"]
        if s in adj_out and t in adj_out:
            adj_out[s].add(t)
            adj_in[t].add(s)

    max_edges = num_nodes * (num_nodes - 1)
    density = round(num_edges / max_edges, 4) if max_edges > 0 else 0.0

    reciprocal = sum(1 for s in adj_out for t in adj_out[s] if s in adj_out.get(t, set()))
    reciprocity = round(reciprocal / num_edges, 4) if num_edges > 0 else 0.0

    def weakly_connected_components(nodes, adj_out, adj_in):
        visited = set()
        count = 0
        for start in nodes:
            if start not in visited:
                count += 1
                queue = [start]
                while queue:
                    node = queue.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    queue.extend(adj_out[node] - visited)
                    queue.extend(adj_in[node] - visited)
        return count

    def strongly_connected_components(nodes, adj_out, adj_in):
        visited = set()
        finish_order = []

        def dfs_forward(v):
            stack = [(v, False)]
            while stack:
                node, returning = stack.pop()
                if returning:
                    finish_order.append(node)
                    continue
                if node in visited:
                    continue
                visited.add(node)
                stack.append((node, True))
                for neighbor in adj_out[node]:
                    if neighbor not in visited:
                        stack.append((neighbor, False))

        for n in nodes:
            if n not in visited:
                dfs_forward(n)

        visited2 = set()
        count = 0
        for v in reversed(finish_order):
            if v not in visited2:
                count += 1
                stack = [v]
                while stack:
                    node = stack.pop()
                    if node in visited2:
                        continue
                    visited2.add(node)
                    stack.extend(adj_in[node] - visited2)
        return count

    def bfs_max_distance(start, adj_out, adj_in):
        dist = {start: 0}
        queue = [start]
        while queue:
            node = queue.pop(0)
            for neighbor in adj_out[node] | adj_in[node]:
                if neighbor not in dist:
                    dist[neighbor] = dist[node] + 1
                    queue.append(neighbor)
        return max(dist.values()) if len(dist) > 1 else 0

    weak_components   = weakly_connected_components(nodes, adj_out, adj_in)
    strong_components = strongly_connected_components(nodes, adj_out, adj_in)

    diameter = None
    if weak_components == 1:
        diameter = max(bfs_max_distance(n, adj_out, adj_in) for n in nodes)

    return {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "density": density,
        "reciprocity": reciprocity,
        "diameter": diameter,
        "weakly_connected_components": weak_components,
        "strongly_connected_components": strong_components,
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print(f"  API Server rodando em http://{HOST}:{PORT}")
    print("="*60)
    print("\nEndpoints:")
    print(f"   GET http://{HOST}:{PORT}/api/graph")
    print(f"   GET http://{HOST}:{PORT}/api/graph/comments")
    print(f"   GET http://{HOST}:{PORT}/api/graph/closings")
    print(f"   GET http://{HOST}:{PORT}/api/graph/reviews")
    print(f"   GET http://{HOST}:{PORT}/api/metrics")
    print(f"   GET http://{HOST}:{PORT}/health")
    print(f"\nDocs: http://{HOST}:{PORT}/docs\n")
    uvicorn.run(app, host=HOST, port=PORT)