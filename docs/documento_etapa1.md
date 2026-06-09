# Planejamento da Solução - Análise de Colaboração (FastAPI)

## 1. Descrição do Problema e Justificativa
A análise da rede de interação em repositórios de código aberto permite identificar os principais contribuidores, as comunidades formadas ao redor do projeto e a fluidez com a qual as revisões de código e discussões ocorrem. 

Para este trabalho, o repositório selecionado foi o **`tiangolo/fastapi`**.
**Justificativa:** O FastAPI é um dos frameworks web que mais cresce no ecossistema Python, possuindo mais de 70.000 estrelas. Devido à sua adoção massiva e uma comunidade ativa que discute novas features diariamente, o repositório oferece uma base riquíssima de interações (issues abertas, PRs exaustivamente revisados e muito engajamento) ideais para uma modelagem de rede complexa.

## 2. Estratégia de Coleta de Dados
A mineração foi realizada através da API oficial do GitHub (via GraphQL/REST) priorizando a extração de *Pull Requests* e *Issues*.
As interações foram mapeadas da seguinte forma:
- O **autor original** da Issue/PR é considerado o destino (alvo) do suporte.
- Os **comentaristas e revisores** são a origem da interação.
- Robôs (como `dependabot` e `github-actions`) foram previamente filtrados para não poluir a análise com comportamentos automatizados que distorcem as métricas reais de colaboração humana.

## 3. Modelagem do Grafo
O grafo desenhado é um **Grafo Simples e Direcionado**, ou seja, sem laços e sem arestas múltiplas, onde cada nó é um desenvolvedor (username).

Seguindo o escopo do trabalho, as relações isoladas são interpretadas e agregadas em um **único Grafo Integrado**. Para lidar com múltiplas interações entre os mesmos usuários, os pesos das arestas são somados de acordo com a "intensidade" técnica da colaboração:

| Tipo de Interação | Peso | Justificativa |
| :--- | :---: | :--- |
| Comentário em Issue ou Pull Request | **2** | Interação leve, tira-dúvidas ou sugestão. |
| Abertura de issue por outro usuário | **3** | Criação de pauta ou bug report qualificado. |
| Revisão / Aprovação de Pull Request | **4** | Análise técnica profunda do código de outro desenvolvedor. |
| Merge de Pull Request | **5** | Validação final de integração no projeto (decisão do mantenedor). |

*Observação:* No grafo consolidado, se o Usuário A revisou um PR do Usuário B (Peso 4) e também comentou numa Issue do Usuário B (Peso 2), a aresta direcionada de `A -> B` terá peso total **6**.

## 4. Plano de Desenvolvimento
A ferramenta foi projetada baseada nos pilares de Orientação a Objetos. Foi concebida uma interface comum abstrata `AbstractGraph` que estipula os métodos (como `addEdge(u, v)`, `getVertexCount()`).

Para instanciar o grafo da colaboração extraída, utilizamos a estrutura concreta de **Lista de Adjacência (`AdjacencyListGraph`)**, visto que as redes sociais/colaborativas são tipicamente muito **esparsas**. O uso de Matriz de Adjacência para milhares de nós resultaria em um desperdício enorme de memória computacional (visto que a grande maioria dos desenvolvedores só interage com uma minoria).

As análises incluem o uso de *PageRank* para medir influência global e *Label Propagation* para detecção de comunidades, tudo implementado do zero para respeitar a ausência de bibliotecas de grafos (NetworkX). Os dados extraídos podem ser consumidos independentemente pelo script de demonstração da API ou pelo pipeline central.
