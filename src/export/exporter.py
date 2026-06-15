import csv
import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent
from src.config import OUTPUT_DATA_DIR
from src.graph.api import AbstractGraph


def export_to_gexf(graph: AbstractGraph, filepath=None, centralities=None, communities=None):
    path = filepath or OUTPUT_DATA_DIR / "collaboration_graph.gexf"

    gexf = Element("gexf", {
        "xmlns":         "http://gexf.net/1.3",
        "xmlns:viz":     "http://gexf.net/1.3/viz",
        "xmlns:xsi":     "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://gexf.net/1.3 http://gexf.net/1.3/gexf.xsd",
        "version":       "1.3"
    })

    graph_el = SubElement(gexf, "graph", {
        "defaultedgetype": "directed",
        "mode":            "static"
    })

    # Declaração dos atributos dos nós
    node_attrs = SubElement(graph_el, "attributes", {"class": "node", "mode": "static"})
    SubElement(node_attrs, "attribute", {"id": "0", "title": "weight",      "type": "float"})
    SubElement(node_attrs, "attribute", {"id": "1", "title": "pagerank",    "type": "float"})
    SubElement(node_attrs, "attribute", {"id": "2", "title": "betweenness", "type": "float"})
    SubElement(node_attrs, "attribute", {"id": "3", "title": "closeness",   "type": "float"})
    SubElement(node_attrs, "attribute", {"id": "4", "title": "in_degree",   "type": "float"})
    SubElement(node_attrs, "attribute", {"id": "5", "title": "out_degree",  "type": "float"})
    SubElement(node_attrs, "attribute", {"id": "6", "title": "community",   "type": "integer"})

    # Declaração dos atributos das arestas
    edge_attrs = SubElement(graph_el, "attributes", {"class": "edge", "mode": "static"})
    SubElement(edge_attrs, "attribute", {"id": "0", "title": "weight", "type": "float"})

    # Paleta de cores para comunidades
    PALETTE = [
        (31,  119, 180), (255, 127,  14), (44,  160,  44), (214,  39,  40),
        (148, 103, 189), (140,  86,  75), (227, 119, 194), (127, 127, 127),
        (188, 189,  34), (23,  190, 207), (174, 199, 232), (255, 187, 120),
    ]

    n = graph.getVertexCount()
    nodes_el = SubElement(graph_el, "nodes")

    for i in range(n):
        label    = graph.getVertexLabel(i)
        node_el  = SubElement(nodes_el, "node", {"id": str(i), "label": label})
        attvals  = SubElement(node_el, "attvalues")

        weight = graph.getVertexWeight(i)
        SubElement(attvals, "attvalue", {"for": "0", "value": str(weight)})

        c = (centralities or {}).get(label, {})
        SubElement(attvals, "attvalue", {"for": "1", "value": str(c.get("pagerank",    0.0))})
        SubElement(attvals, "attvalue", {"for": "2", "value": str(c.get("betweenness", 0.0))})
        SubElement(attvals, "attvalue", {"for": "3", "value": str(c.get("closeness",   0.0))})
        SubElement(attvals, "attvalue", {"for": "4", "value": str(c.get("in_degree",   0.0))})
        SubElement(attvals, "attvalue", {"for": "5", "value": str(c.get("out_degree",  0.0))})

        comm = (communities or {}).get(label, 0)
        SubElement(attvals, "attvalue", {"for": "6", "value": str(comm)})

        # Cor por comunidade
        r, g_c, b = PALETTE[comm % len(PALETTE)]
        SubElement(node_el, "viz:color", {"r": str(r), "g": str(g_c), "b": str(b), "a": "1.0"})

        # Tamanho proporcional ao PageRank
        pr   = c.get("pagerank", 0.0)
        size = max(3.0, min(40.0, pr * 500))
        SubElement(node_el, "viz:size", {"value": str(round(size, 2))})

    # Arestas
    edges_el  = SubElement(graph_el, "edges")
    edge_id   = 0
    for u in range(n):
        for v in range(n):
            if graph.hasEdge(u, v):
                w       = graph.getEdgeWeight(u, v)
                edge_el = SubElement(edges_el, "edge", {
                    "id":     str(edge_id),
                    "source": str(u),
                    "target": str(v),
                    "weight": str(w)
                })
                attvals = SubElement(edge_el, "attvalues")
                SubElement(attvals, "attvalue", {"for": "0", "value": str(w)})
                edge_id += 1

    indent(gexf, space="  ")
    tree = ElementTree(gexf)
    with open(path, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    print(f"[INFO] GEXF exportado com métricas embutidas: {Path(path).name}")
    return path


def export_to_json(graph: AbstractGraph, filepath=None, centralities=None, communities=None):
    path = filepath or OUTPUT_DATA_DIR / "collaboration_graph.json"

    data = {"nodes": [], "links": []}
    n    = graph.getVertexCount()

    for i in range(n):
        label     = graph.getVertexLabel(i)
        node_data = {
            "id":     label,
            "weight": graph.getVertexWeight(i)
        }
        if centralities and label in centralities:
            node_data.update(centralities[label])
        if communities and label in communities:
            node_data["community"] = communities[label]
        data["nodes"].append(node_data)

    for u in range(n):
        for v in range(n):
            if graph.hasEdge(u, v):
                data["links"].append({
                    "source": graph.getVertexLabel(u),
                    "target": graph.getVertexLabel(v),
                    "weight": graph.getEdgeWeight(u, v)
                })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[INFO] JSON exportado: {Path(path).name}")
    return path


def export_metrics_to_csv(centralities, communities, graph: AbstractGraph, filepath=None):
    path = filepath or OUTPUT_DATA_DIR / "collaboration_metrics.csv"

    username_to_id = {
        graph.getVertexLabel(i): i
        for i in range(graph.getVertexCount())
    }

    sorted_users = sorted(
        centralities.keys(),
        key=lambda u: centralities[u].get("pagerank", 0),
        reverse=True
    )

    headers = [
        "Username", "Contributions",
        "InDegreeCentrality", "OutDegreeCentrality",
        "BetweennessCentrality", "ClosenessCentrality",
        "PageRank", "CommunityID"
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for username in sorted_users:
            uid          = username_to_id[username]
            contributions = graph.getVertexWeight(uid)
            c            = centralities.get(username, {})
            writer.writerow([
                username,
                contributions,
                f"{c.get('in_degree',   0.0):.6f}",
                f"{c.get('out_degree',  0.0):.6f}",
                f"{c.get('betweenness', 0.0):.6f}",
                f"{c.get('closeness',   0.0):.6f}",
                f"{c.get('pagerank',    0.0):.6f}",
                communities.get(username, 0)
            ])

    print(f"[INFO] CSV exportado: {Path(path).name}")
    return path


def export_individual_graphs_to_json(graphs_dict, filepath_prefix=None):
    """
    Exporta os 3 grafos individuais (comments, closings, reviews) em JSON.
    
    graphs_dict: dicionário retornado por builder.get_all_graphs()
    {
        "comments": graph,
        "closings": graph,
        "reviews": graph,
        "integrated": graph
    }
    """
    filepath_prefix = filepath_prefix or OUTPUT_DATA_DIR
    
    graph_names = {
        "comments": "collaboration_graph_comments.json",
        "closings": "collaboration_graph_closings.json",
        "reviews": "collaboration_graph_reviews.json",
    }
    
    for graph_type, filename in graph_names.items():
        if graph_type not in graphs_dict:
            continue
            
        graph = graphs_dict[graph_type]
        path = filepath_prefix / filename
        
        # Mesma lógica que export_to_json
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
        
        print(f"[INFO] {graph_type.capitalize()} graph exportado em: {filename}")
    
    return graph_names