import csv
import json
from pathlib import Path
from src.config import OUTPUT_DATA_DIR
from src.graph.api import AbstractGraph

def export_to_gexf(graph: AbstractGraph, filepath=None, centralities=None, communities=None):
    """
    Exporta o grafo no formato GEXF utilizando o método embutido na API do Grafo.
    """
    path = filepath or OUTPUT_DATA_DIR / "collaboration_graph.gexf"
    
    # O nosso grafo já possui o método exportToGEPHI que gera o GEXF perfeitamente
    graph.exportToGEPHI(str(path))
    
    print(f"[INFO] Grafo exportado com sucesso no formato Gephi (GEXF) em: {Path(path).name}")
    return path

def export_to_json(graph: AbstractGraph, filepath=None, centralities=None, communities=None):
    """
    Exporta o grafo em formato JSON customizado.
    """
    path = filepath or OUTPUT_DATA_DIR / "collaboration_graph.json"
    
    data = {
        "nodes": [],
        "links": []
    }
    
    num_vertices = graph.getVertexCount()
    
    for i in range(num_vertices):
        label = graph.getVertexLabel(i)
        node_data = {
            "id": label,
            "weight": graph.getVertexWeight(i)
        }
        
        if centralities and label in centralities:
            c = centralities[label]
            node_data.update(c)
            
        if communities and label in communities:
            node_data["group"] = communities[label]
            
        data["nodes"].append(node_data)
        
    for u in range(num_vertices):
        for v in range(num_vertices):
            if graph.hasEdge(u, v):
                data["links"].append({
                    "source": graph.getVertexLabel(u),
                    "target": graph.getVertexLabel(v),
                    "weight": graph.getEdgeWeight(u, v)
                })
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"[INFO] Grafo exportado com sucesso no formato JSON em: {Path(path).name}")
    return path

def export_metrics_to_csv(centralities, communities, graph: AbstractGraph, filepath=None):
    """
    Exporta a tabela comparativa de métricas em formato CSV.
    """
    path = filepath or OUTPUT_DATA_DIR / "collaboration_metrics.csv"
    
    headers = [
        "Username", 
        "Contributions", 
        "InDegreeCentrality", 
        "OutDegreeCentrality", 
        "BetweennessCentrality", 
        "ClosenessCentrality", 
        "PageRank", 
        "CommunityID"
    ]
    
    num_vertices = graph.getVertexCount()
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i in range(num_vertices):
            username = graph.getVertexLabel(i)
            contributions = graph.getVertexWeight(i)
            
            c_data = centralities.get(username, {})
            in_deg = c_data.get("in_degree", 0.0)
            out_deg = c_data.get("out_degree", 0.0)
            between = c_data.get("betweenness", 0.0)
            closeness = c_data.get("closeness", 0.0)
            p_rank = c_data.get("pagerank", 0.0)
            
            comm_id = communities.get(username, 0)
            
            writer.writerow([
                username,
                contributions,
                f"{in_deg:.6f}",
                f"{out_deg:.6f}",
                f"{between:.6f}",
                f"{closeness:.6f}",
                f"{p_rank:.6f}",
                comm_id
            ])
            
    print(f"[INFO] Métricas comparativas exportadas com sucesso em formato CSV em: {Path(path).name}")
    return path
