from src.graph.adjacency_matrix import AdjacencyMatrixGraph
from src.graph.adjacency_list import AdjacencyListGraph

def run_demo():
    print("="*60)
    print(" DEMONSTRAÇÃO DA API DE GRAFOS ".center(60, "="))
    print("="*60)

    print("\n1. Inicializando AdjacencyMatrixGraph(4) e AdjacencyListGraph(4)...")
    g_mat = AdjacencyMatrixGraph(4)
    g_lst = AdjacencyListGraph(4)

    # Vamos usar AdjacencyListGraph para a demonstração
    g = g_lst
    
    print(f"-> Vértices criados: {g.getVertexCount()}")
    print(f"-> Arestas iniciais: {g.getEdgeCount()}")
    print(f"-> O grafo está vazio? {g.isEmptyGraph()}")

    print("\n2. Adicionando arestas e pesos...")
    g.addEdge(0, 1)
    g.addEdge(0, 2)
    g.addEdge(1, 3)
    g.addEdge(3, 0)
    
    g.setEdgeWeight(0, 1, 5.0)
    g.setEdgeWeight(0, 2, 2.5)
    
    g.setVertexLabel(0, "Alice")
    g.setVertexLabel(1, "Bob")
    g.setVertexLabel(2, "Charlie")
    g.setVertexLabel(3, "Dave")

    print(f"-> Total de Arestas: {g.getEdgeCount()}")
    print(f"-> O grafo está vazio agora? {g.isEmptyGraph()}")
    print(f"-> Aresta de 0 para 1 existe? {g.hasEdge(0, 1)}")
    print(f"-> Peso da aresta (0->1): {g.getEdgeWeight(0, 1)}")
    
    print("\n3. Verificando graus dos vértices...")
    print(f"-> Grau de Entrada (In-Degree) do vértice 1 (Bob): {g.getVertexInDegree(1)}")
    print(f"-> Grau de Saída (Out-Degree) do vértice 0 (Alice): {g.getVertexOutDegree(0)}")
    
    print("\n4. Verificando Relações e Incidências...")
    print(f"-> Bob(1) é sucessor de Alice(0)? {g.isSucessor(0, 1)}")
    print(f"-> Alice(0) é predecessor de Bob(1)? {g.isPredessor(1, 0)}")
    print(f"-> As arestas (0->1) e (0->2) são divergentes? {g.isDivergent(0, 1, 0, 2)}")
    print(f"-> A aresta (3->0) e a (0->1) são convergentes? {g.isConvergent(3, 0, 0, 1)}")
    print(f"-> A aresta (0->1) é incidente ao vértice 0? {g.isIncident(0, 1, 0)}")
    
    print("\n5. Propriedades Estruturais...")
    print(f"-> O grafo é completo? {g.isCompleteGraph()}")
    print(f"-> O grafo é conexo? {g.isConnected()}")
    
    print("\n6. Exportando para GEPHI...")
    g.exportToGEPHI("data/output/demo_graph.gexf")
    print("-> Grafo exportado para 'data/output/demo_graph.gexf'.")

    print("\n7. Exceções e Tratamento de Erros...")
    try:
        g.addEdge(1, 1) # Laço (self-loop)
    except Exception as e:
        print(f"-> Erro ao adicionar laço tratado: {e}")
        
    try:
        g.getEdgeWeight(2, 3) # Aresta inexistente
    except Exception as e:
        print(f"-> Erro de aresta inexistente tratado: {e}")
        
    try:
        g.addEdge(0, 10) # Índice fora do limite
    except Exception as e:
        print(f"-> Erro de índice inválido tratado: {e}")

    print("\n" + "="*60)
    print(" DEMONSTRAÇÃO CONCLUÍDA ".center(60, "="))
    print("="*60)

if __name__ == "__main__":
    run_demo()
