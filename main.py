import argparse
import sys
from pathlib import Path
from src.config import init_directories, DEFAULT_REPO
from src.mining.miner import GitHubMiner
from src.graph.builder import CollaborationGraphBuilder
from src.analysis import analyzer
from src.export import exporter

def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title:^78} ")
    print("=" * 80)

def print_table(rows, headers):
    # Calcular largura de cada coluna
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))
            
    # Criar string de formato
    row_fmt = " | ".join([f"{{:<{w}}}" for w in widths])
    sep = "-+-".join(["-" * w for w in widths])
    
    print("\n" + row_fmt.format(*headers))
    print(sep)
    for row in rows:
        print(row_fmt.format(*[str(c) for c in row]))
    print()

def main():
    parser = argparse.ArgumentParser(
        description="FastAPI Graph Analysis - Analise a colaboração dos desenvolvedores no ecossistema FastAPI."
    )
    parser.add_argument("--mine", action="store_true", help="Executar mineração ativa no GitHub.")
    parser.add_argument("--use-mock", action="store_true", help="Forçar o uso de simulação offline (dados sintéticos).")
    parser.add_argument("--limit", type=int, default=50, help="Limite de issues/PRs a processar na mineração (padrão: 50).")
    parser.add_argument("--include-bots", action="store_true", help="Incluir bots de automação (como dependabot) na análise.")
    parser.add_argument("--force-refresh", action="store_true", help="Ignorar o cache local e forçar atualização via API.")
    parser.add_argument("--repo", type=str, default=DEFAULT_REPO, help=f"Repositório GitHub (padrão: {DEFAULT_REPO}).")
    
    args = parser.parse_args()
    
    # Inicializar diretórios
    init_directories()
    
    print_header("FASTAPI GRAPH ANALYSIS - INICIALIZANDO PIPELINE")
    
    miner = GitHubMiner(repo_name=args.repo)
    mined_data = None
    
    # Verificar se devemos usar mock ou tentar mineração/cache
    if args.use_mock:
        mined_data = miner.generate_mock_data()
    else:
        # Tentar ler cache ou fazer mineração
        cache_exists = miner.cache_file.exists()
        
        if not cache_exists and not args.mine:
            print("[WARN] Nenhum cache local encontrado e --mine não foi especificado.")
            print("[INFO] Alternando automaticamente para o modo simulação (Mock) para fins demonstrativos.")
            mined_data = miner.generate_mock_data()
        else:
            # Tentar minerar ou carregar cache
            try:
                # Se forçando ou não possuindo cache, realiza a mineração
                if args.force_refresh or not cache_exists:
                    mined_data = miner.mine(limit=args.limit, force_refresh=True)
                else:
                    mined_data = miner.mine(limit=args.limit, force_refresh=False)
            except Exception as e:
                print(f"[ERROR] Não foi possível obter dados ativos: {e}")
                print("[INFO] Realizando fallback automático para dados simulados (Mock).")
                mined_data = miner.generate_mock_data()

    if not mined_data:
        print("[ERROR] Erro crítico: Sem dados para processamento. Encerrando.")
        sys.exit(1)
        
    # 2. Construir Grafo
    print_header("1. CONSTRUÇÃO DO GRAFO DE COLABORAÇÃO")
    exclude_bots = not args.include_bots
    builder = CollaborationGraphBuilder(exclude_bots=exclude_bots)
    graph = builder.build_from_mined_data(mined_data)
    
    if graph.getVertexCount() == 0:
        print("[WARN] Grafo vazio! Nenhum colaborador encontrado com os filtros atuais.")
        sys.exit(0)
        
    # Salvar estado do grafo
    builder.save_graph_state()
    
    # 3. Analisar Grafo
    print_header("2. ANÁLISE E CÁLCULO DE MÉTRICAS DA REDE")
    
    print("[INFO] Calculando centralidades (Degree, Betweenness, Closeness, PageRank)...")
    centralities = analyzer.calculate_centralities(graph)
    
    print("[INFO] Detectando comunidades de colaboradores (Louvain)...")
    communities = analyzer.detect_communities(graph)
    
    print("[INFO] Compilando estatísticas globais da rede...")
    global_metrics = analyzer.get_network_metrics(graph)
    
    # Mostrar estatísticas globais
    print("\n--- Estatísticas Globais da Rede ---")
    print(f"  Número de Contribuintes (Nós): {global_metrics['nodes']}")
    print(f"  Número de Interações (Arestas): {global_metrics['edges']}")
    print(f"  Densidade do Grafo: {global_metrics['density']:.4f}")
    print(f"  Reciprocidade (Mútua): {global_metrics['reciprocity']:.4f}")
    print(f"  Agrupamento Médio (Clustering): {global_metrics['average_clustering']:.4f}")
    print(f"  Diâmetro da Rede: {global_metrics['diameter']}")
    print(f"  Componentes Conectados (Fraco): {global_metrics['weakly_connected_components']}")
    print(f"  Componentes Conectados (Forte): {global_metrics['strongly_connected_components']}")

    # 4. Mostrar os Top 10 Contribuidores mais influentes (PageRank)
    print_header("3. TOP 10 COLABORADORES MAIS INFLUENTES (PAGERANK)")
    
    # Obter todos os usuários
    all_users = [graph.getVertexLabel(i) for i in range(graph.getVertexCount())]
    
    # Ordenar nós por PageRank
    top_contributors = sorted(
        all_users,
        key=lambda user: centralities.get(user, {}).get("pagerank", 0.0),
        reverse=True
    )[:10]
    
    headers = ["Username", "Contrib.", "In-Degree", "Out-Degree", "Betweenness", "PageRank", "Community"]
    rows = []
    
    # Precisamos do id do nó para buscar as contribuições (VertexWeight)
    for user in top_contributors:
        # Encontrar id do user
        node_id = -1
        for i in range(graph.getVertexCount()):
            if graph.getVertexLabel(i) == user:
                node_id = i
                break
                
        contributions = graph.getVertexWeight(node_id) if node_id != -1 else 0
        metrics = centralities.get(user, {})
        comm = communities.get(user, 0)
        
        rows.append([
            user,
            contributions,
            f"{metrics.get('in_degree', 0.0):.4f}",
            f"{metrics.get('out_degree', 0.0):.4f}",
            f"{metrics.get('betweenness', 0.0):.4f}",
            f"{metrics.get('pagerank', 0.0):.4f}",
            comm
        ])
        
    print_table(rows, headers)
    
    # 5. Exportar Resultados
    print_header("4. EXPORTAÇÃO DOS ARQUIVOS DE SAÍDA")
    
    # Exportar GEXF (para Gephi)
    gexf_path = exporter.export_to_gexf(graph, centralities=centralities, communities=communities)
    
    # Exportar JSON (para visualização web)
    json_path = exporter.export_to_json(graph, centralities=centralities, communities=communities)
    
    # Exportar CSV (tabela de métricas)
    csv_path = exporter.export_metrics_to_csv(centralities, communities, graph)
    
    print("\n[SUCCESS] Pipeline concluído com sucesso!")
    print(f"  Arquivo Gephi (GEXF): {gexf_path}")
    print(f"  Arquivo JSON: {json_path}")
    print(f"  Tabela de Métricas (CSV): {csv_path}\n")

if __name__ == "__main__":
    main()
