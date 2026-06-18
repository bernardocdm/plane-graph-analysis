from abc import ABC, abstractmethod
import math
import os

# ==============================================================================
# Classe: AbstractGraph
# Descrição: Esta classe abstrata (baseada em ABC) define a API padrão,
#            os atributos compartilhados e os métodos comuns para manipulação
#            de grafos no sistema. Serve como a base estrutural para as subclasses
#            AdjacencyListGraph e AdjacencyMatrixGraph.
# ==============================================================================
class AbstractGraph(ABC):
    """
    Classe abstrata que define a API comum, atributos compartilhados 
    e métodos auxiliares para a representação de grafos.
    """
    
    def __init__(self, numVertices: int):
        if numVertices <= 0:
            raise ValueError("O número de vértices deve ser maior que zero.")
            
        self.numVertices = numVertices
        self.vertexWeights = [0.0] * numVertices
        self.vertexLabels = [str(i) for i in range(numVertices)]
        self.edgeCount = 0

    # ========================================================
    # Métodos Auxiliares
    # ========================================================
    def _check_vertex(self, v: int):
        if not (0 <= v < self.numVertices):
            raise IndexError(f"Vértice {v} inválido. Deve estar entre 0 e {self.numVertices - 1}.")

    # ========================================================
    # API Obrigatória (Abstrata - para subclasses implementarem)
    # ========================================================
    @abstractmethod
    def hasEdge(self, u: int, v: int) -> bool:
        pass

    @abstractmethod
    def addEdge(self, u: int, v: int) -> None:
        pass

    @abstractmethod
    def removeEdge(self, u: int, v: int) -> None:
        pass

    @abstractmethod
    def setEdgeWeight(self, u: int, v: int, w: float) -> None:
        pass

    @abstractmethod
    def getEdgeWeight(self, u: int, v: int) -> float:
        pass

    @abstractmethod
    def getVertexInDegree(self, u: int) -> int:
        pass

    @abstractmethod
    def getVertexOutDegree(self, u: int) -> int:
        pass

    # ========================================================
    # API Obrigatória (Implementação Comum)
    # ========================================================
    def getVertexCount(self) -> int:
        return self.numVertices

    def getEdgeCount(self) -> int:
        return self.edgeCount

    def setVertexWeight(self, v: int, w: float) -> None:
        self._check_vertex(v)
        self.vertexWeights[v] = w

    def getVertexWeight(self, v: int) -> float:
        self._check_vertex(v)
        return self.vertexWeights[v]
        
    def setVertexLabel(self, v: int, label: str) -> None:
        self._check_vertex(v)
        self.vertexLabels[v] = label
        
    def getVertexLabel(self, v: int) -> str:
        self._check_vertex(v)
        return self.vertexLabels[v]

    def isSucessor(self, u: int, v: int) -> bool:
        """Verifica se v é sucessor de u (existe aresta de u para v)"""
        self._check_vertex(u)
        self._check_vertex(v)
        return self.hasEdge(u, v)

    def isPredessor(self, u: int, v: int) -> bool:
        """Verifica se v é predecessor de u (existe aresta de v para u)"""
        self._check_vertex(u)
        self._check_vertex(v)
        return self.hasEdge(v, u)

    def isDivergent(self, u1: int, v1: int, u2: int, v2: int) -> bool:
        """Duas arestas são divergentes se partem do mesmo vértice (u1 == u2)"""
        if not (self.hasEdge(u1, v1) and self.hasEdge(u2, v2)):
            return False
        return u1 == u2

    def isConvergent(self, u1: int, v1: int, u2: int, v2: int) -> bool:
        """Duas arestas são convergentes se chegam no mesmo vértice (v1 == v2)"""
        if not (self.hasEdge(u1, v1) and self.hasEdge(u2, v2)):
            return False
        return v1 == v2

    def isIncident(self, u: int, v: int, x: int) -> bool:
        """A aresta (u, v) é incidente ao vértice x se x == u ou x == v"""
        self._check_vertex(x)
        if not self.hasEdge(u, v):
            return False
        return x == u or x == v

    def isConnected(self) -> bool:
        """
        Verifica se o grafo é conexo (fracamente conexo, já que é direcionado).
        Uma busca simples a partir de qualquer vértice alcança todos os vértices?
        Faremos uma busca em largura considerando arestas como não-direcionadas.
        """
        if self.numVertices == 0:
            return True
            
        visited = set()
        queue = [0]
        visited.add(0)
        
        while queue:
            current = queue.pop(0)
            
            # Olhar todos os vértices para simular a versão não direcionada
            for neighbor in range(self.numVertices):
                if neighbor not in visited:
                    if self.hasEdge(current, neighbor) or self.hasEdge(neighbor, current):
                        visited.add(neighbor)
                        queue.append(neighbor)
                        
        return len(visited) == self.numVertices

    def isEmptyGraph(self) -> bool:
        """Um grafo é vazio se não possui arestas."""
        return self.edgeCount == 0

    def isCompleteGraph(self) -> bool:
        """
        Em um grafo simples direcionado, um grafo é completo se 
        para todo par de vértices distintos existe uma aresta (u->v) e (v->u).
        Total de arestas = V * (V - 1)
        """
        return self.edgeCount == (self.numVertices * (self.numVertices - 1))

    def exportToGEPHI(self, path: str) -> None:
        """Exporta o grafo no formato GEXF."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">\n')
            f.write('  <graph mode="static" defaultedgetype="directed">\n')
            
            f.write('    <attributes class="node">\n')
            f.write('      <attribute id="0" title="weight" type="double"/>\n')
            f.write('      <attribute id="1" title="label" type="string"/>\n')
            f.write('    </attributes>\n')
            
            # Export nodes
            f.write('    <nodes>\n')
            for i in range(self.numVertices):
                f.write(f'      <node id="{i}" label="{self.vertexLabels[i]}">\n')
                f.write('        <attvalues>\n')
                f.write(f'          <attvalue for="0" value="{self.vertexWeights[i]}"/>\n')
                f.write(f'          <attvalue for="1" value="{self.vertexLabels[i]}"/>\n')
                f.write('        </attvalues>\n')
                f.write('      </node>\n')
            f.write('    </nodes>\n')
            
            # Export edges
            f.write('    <edges>\n')
            edge_id = 0
            for u in range(self.numVertices):
                for v in range(self.numVertices):
                    if self.hasEdge(u, v):
                        weight = self.getEdgeWeight(u, v)
                        f.write(f'      <edge id="{edge_id}" source="{u}" target="{v}" weight="{weight}"/>\n')
                        edge_id += 1
            f.write('    </edges>\n')
            
            f.write('  </graph>\n')
            f.write('</gexf>\n')
