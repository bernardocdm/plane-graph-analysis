from src.graph.api import AbstractGraph

class AdjacencyMatrixGraph(AbstractGraph):
    """
    Implementação do grafo utilizando matriz de adjacência.
    """
    
    def __init__(self, numVertices: int):
        super().__init__(numVertices)
        # Matriz V x V inicializada com float('inf') para ausência de aresta
        # ou None (vamos usar None para representar ausência para simplificar os cálculos)
        self.matrix = [[None for _ in range(numVertices)] for _ in range(numVertices)]
        
    def hasEdge(self, u: int, v: int) -> bool:
        self._check_vertex(u)
        self._check_vertex(v)
        return self.matrix[u][v] is not None
        
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
            
        if self.matrix[u][v] is None:
            self.matrix[u][v] = 1.0 # Peso padrão 1.0
            self.edgeCount += 1
            
    def removeEdge(self, u: int, v: int) -> None:
        self._check_vertex(u)
        self._check_vertex(v)
        if self.matrix[u][v] is not None:
            self.matrix[u][v] = None
            self.edgeCount -= 1
            
    def setEdgeWeight(self, u: int, v: int, w: float) -> None:
        self._check_vertex(u)
        self._check_vertex(v)
        if self.matrix[u][v] is None:
            raise ValueError(f"A aresta ({u}, {v}) não existe.")
        self.matrix[u][v] = w
        
    def getEdgeWeight(self, u: int, v: int) -> float:
        self._check_vertex(u)
        self._check_vertex(v)
        if self.matrix[u][v] is None:
            raise ValueError(f"A aresta ({u}, {v}) não existe.")
        return self.matrix[u][v]
        
    def getVertexInDegree(self, u: int) -> int:
        self._check_vertex(u)
        in_degree = 0
        for i in range(self.numVertices):
            if self.matrix[i][u] is not None:
                in_degree += 1
        return in_degree
        
    def getVertexOutDegree(self, u: int) -> int:
        self._check_vertex(u)
        out_degree = 0
        for j in range(self.numVertices):
            if self.matrix[u][j] is not None:
                out_degree += 1
        return out_degree
