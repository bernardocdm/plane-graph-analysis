from src.graph.api import AbstractGraph

# ==============================================================================
# Classe: AdjacencyListGraph
# Descrição: Implementação concreta de Grafo (AbstractGraph) que utiliza listas
#            de adjacência para representar as conexões e pesos entre vértices.
#            É especialmente indicada para grafos esparsos por conta da economia
#            de memória.
# ==============================================================================
class AdjacencyListGraph(AbstractGraph):
    """
    Implementação do grafo utilizando listas de adjacência.
    """
    
    def __init__(self, numVertices: int):
        super().__init__(numVertices)
        # Lista de dicionários, onde o índice é o nó origem
        # e o dicionário mapeia vizinho (destino) -> peso
        self.adjList = [{} for _ in range(numVertices)]
        
    def hasEdge(self, u: int, v: int) -> bool:
        self._check_vertex(u)
        self._check_vertex(v)
        return v in self.adjList[u]
        
    def addEdge(self, u: int, v: int) -> None:
        """
        Adiciona aresta de u para v. 
        Se a aresta já existir, não faz nada (idempotente).
        Se for u == v, lança erro (grafo simples, sem laços).
        """
        self._check_vertex(u)
        self._check_vertex(v)
        
        if u == v:
            raise ValueError("Não são permitidos laços (self-loops) em um grafo simples.")
            
        if v not in self.adjList[u]:
            self.adjList[u][v] = 1.0 # Peso padrão 1.0
            self.edgeCount += 1
            
    def removeEdge(self, u: int, v: int) -> None:
        self._check_vertex(u)
        self._check_vertex(v)
        if v in self.adjList[u]:
            del self.adjList[u][v]
            self.edgeCount -= 1
            
    def setEdgeWeight(self, u: int, v: int, w: float) -> None:
        self._check_vertex(u)
        self._check_vertex(v)
        if v not in self.adjList[u]:
            raise ValueError(f"A aresta ({u}, {v}) não existe.")
        self.adjList[u][v] = w
        
    def getEdgeWeight(self, u: int, v: int) -> float:
        self._check_vertex(u)
        self._check_vertex(v)
        if v not in self.adjList[u]:
            raise ValueError(f"A aresta ({u}, {v}) não existe.")
        return self.adjList[u][v]
        
    def getVertexInDegree(self, u: int) -> int:
        self._check_vertex(u)
        in_degree = 0
        for i in range(self.numVertices):
            if u in self.adjList[i]:
                in_degree += 1
        return in_degree
        
    def getVertexOutDegree(self, u: int) -> int:
        self._check_vertex(u)
        return len(self.adjList[u])
