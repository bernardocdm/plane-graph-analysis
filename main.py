import argparse
import sys
from src.config import init_directories, DEFAULT_REPO, GITHUB_TOKENS, OUTPUT_DATA_DIR
from src.mining.miner import GitHubMiner
from src.graph.builder import CollaborationGraphBuilder
from src.analysis import analyzer
from src.export import exporter


def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title:^78} ")
    print("=" * 80)


def print_table(rows, headers):
    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(str(cell)))

    row_fmt = " | ".join([f"{{:<{w}}}" for w in widths])
    sep     = "-+-".join(["-" * w for w in widths])

    print("\n" + row_fmt.format(*headers))
    print(sep)
    for row in rows:
        print(row_fmt.format(*[str(c) for c in row]))
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Graph Analysis — Análise de colaboração em repositórios GitHub via Teoria de Grafos."
    )
    parser.add_argument("--mine",          action="store_true",
                        help="Executar mineração ativa no GitHub.")
    parser.add_argument("--use-mock",      action="store_true",
                        help="Usar dados sintéticos (offline).")
    parser.add_argument("--limit",         type=int, default=200,
                        help="Limite de issues/PRs a processar (padrão: 200). Use 0 para sem limite.")
    parser.add_argument("--include-bots",  action="store_true",
                        help="Incluir bots na análise.")
    parser.add_argument("--force-refresh", action="store_true",
                        help="Ignorar cache e reminerar do zero.")
    parser.add_argument("--repo",          type=str, default=DEFAULT_REPO,
                        help=f"Repositório GitHub (padrão: {DEFAULT_REPO}).")

    args = parser.parse_args()
    init_directories()

    print_header("GRAPH ANALYSIS — INICIALIZANDO PIPELINE")

    # ── 1. Mineração ──────────────────────────────────────────────────────────
    miner      = GitHubMiner(tokens=GITHUB_TOKENS, repo_name=args.repo)
    mined_data = None

    if args.use_mock:
        mined_data = miner.generate_mock_data()

    else:
        cache_exists = miner.cache_file.exists()

        if not cache_exists and not args.mine:
            print("[WARN] Nenhum cache local encontrado e --mine não foi especificado.")
            print("[INFO] Alternando para modo mock para demonstração.")
            mined_data = miner.generate_mock_data()

        else:
            try:
                force      = args.force_refresh or not cache_exists
                mined_data = miner.mine(limit=args.limit, force_refresh=force)

            except Exception as e:
                print(f"[ERROR] Mineração interrompida: {e}")

                # Tentar usar checkpoint parcial salvo durante a mineração
                if miner.cache_file.exists():
                    print("[INFO] Usando checkpoint parcial salvo durante a mineração.")
                    mined_data = miner.load_cache()
                    issues_count = len(mined_data.get("issues", []))
                    prs_count    = len(mined_data.get("prs",    []))
                    print(f"[INFO] Checkpoint contém {issues_count} issues e {prs_count} PRs reais.")
                else:
                    print("[INFO] Nenhum checkpoint disponível. Usando dados mock.")
                    mined_data = miner.generate_mock_data()

    if not mined_data:
        print("[ERROR] Sem dados para processamento. Encerrando.")
        sys.exit(1)

    is_mock       = mined_data.get("is_mock",       False)
    is_checkpoint = mined_data.get("is_checkpoint", False)

    print(f"\n[INFO] Issues: {len(mined_data.get('issues', []))}")
    print(f"[INFO] PRs:    {len(mined_data.get('prs',    []))}")
    if is_mock:
        print("[INFO] Fonte: dados sintéticos (mock)")
    elif is_checkpoint:
        print("[INFO] Fonte: checkpoint parcial (mineração incompleta)")
    else:
        print("[INFO] Fonte: mineração completa")

    # ── 2. Construção dos 4 grafos ────────────────────────────────────────────
    print_header("1. CONSTRUÇÃO DOS GRAFOS DE COLABORAÇÃO")

    builder = CollaborationGraphBuilder(exclude_bots=not args.include_bots)
    graph   = builder.build_from_mined_data(mined_data)

    if graph.getVertexCount() == 0:
        print("[WARN] Grafo vazio. Verifique os dados minerados.")
        sys.exit(0)

    builder.save_graph_state()

    # ── 3. Análise ────────────────────────────────────────────────────────────
    print_header("2. ANÁLISE E CÁLCULO DE MÉTRICAS")

    print("[INFO] Calculando centralidades (Degree, Betweenness, Closeness, PageRank)...")
    centralities = analyzer.calculate_centralities(graph)

    print("[INFO] Detectando comunidades (Label Propagation)...")
    communities  = analyzer.detect_communities(graph)

    print("[INFO] Calculando métricas globais da rede...")
    global_metrics = analyzer.get_network_metrics(graph)

    print("\n--- Métricas Globais da Rede ---")
    print(f"  Contribuidores (nós):              {global_metrics['nodes']}")
    print(f"  Interações (arestas):              {global_metrics['edges']}")
    print(f"  Densidade:                         {global_metrics['density']:.4f}")
    print(f"  Reciprocidade:                     {global_metrics['reciprocity']:.4f}")
    print(f"  Clustering médio:                  {global_metrics['average_clustering']:.4f}")
    print(f"  Assortatividade:                   {global_metrics['assortativity']:.4f}")
    print(f"  Diâmetro:                          {global_metrics['diameter']:.0f}")
    print(f"  Componentes fracos:                {global_metrics['weakly_connected_components']}")
    print(f"  Componentes fortes (Kosaraju):     {global_metrics['strongly_connected_components']}")

    # ── 4. Top 10 por PageRank ────────────────────────────────────────────────
    print_header("3. TOP 10 COLABORADORES MAIS INFLUENTES (PAGERANK)")

    all_users = [graph.getVertexLabel(i) for i in range(graph.getVertexCount())]
    top_contributors = sorted(
        all_users,
        key=lambda u: centralities.get(u, {}).get("pagerank", 0.0),
        reverse=True
    )[:10]

    headers = ["Username", "Contrib.", "In-Deg", "Out-Deg",
               "Betweenness", "Closeness", "PageRank", "Comunidade"]
    rows = []
    for user in top_contributors:
        node_id = next(
            (i for i in range(graph.getVertexCount()) if graph.getVertexLabel(i) == user), -1
        )
        contribs = graph.getVertexWeight(node_id) if node_id != -1 else 0
        m = centralities.get(user, {})
        rows.append([
            user,
            int(contribs),
            f"{m.get('in_degree',   0.0):.4f}",
            f"{m.get('out_degree',  0.0):.4f}",
            f"{m.get('betweenness', 0.0):.4f}",
            f"{m.get('closeness',   0.0):.4f}",
            f"{m.get('pagerank',    0.0):.4f}",
            communities.get(user, 0)
        ])
    print_table(rows, headers)

    # ── 5. Exportação ─────────────────────────────────────────────────────────
    print_header("4. EXPORTAÇÃO DOS ARQUIVOS DE SAÍDA")

    all_graphs = builder.get_all_graphs()

    # Exportar os 4 grafos em GEXF separados (para Gephi)
    for name, g in all_graphs.items():
        if g and g.getVertexCount() > 0:
            filepath = OUTPUT_DATA_DIR / f"graph_{name}.gexf"
            path = exporter.export_to_gexf(
                g,
                filepath=filepath,
                centralities=(centralities if name == "integrated" else None),
                communities=(communities  if name == "integrated" else None)
            )
            print(f"  [GEXF] {name}: {path}")

    # JSON e CSV do grafo integrado
    json_path = exporter.export_to_json(
        graph, centralities=centralities, communities=communities
    )
    csv_path = exporter.export_metrics_to_csv(centralities, communities, graph)

    print(f"\n  [JSON] {json_path}")
    print(f"  [CSV]  {csv_path}")

    # Exportar os 3 grafos individuais em JSON
    graphs_dict = builder.get_all_graphs()
    exporter.export_individual_graphs_to_json(graphs_dict)

    print("\n[SUCCESS] Pipeline concluído com sucesso!")


if __name__ == "__main__":
    main()