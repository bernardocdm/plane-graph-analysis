# Planejamento da Solução - Análise de Colaboração (Plane)

## 1. Descrição do Problema e Justificativa
A análise da rede de interação em repositórios de código aberto permite identificar os principais contribuidores, as comunidades formadas ao redor do projeto e a fluidez com a qual as revisões de código e discussões ocorrem.

Para este trabalho, o repositório selecionado foi o **`makeplane/plane`**.

**Justificativa:** O Plane é uma plataforma open source de gerenciamento de projetos (alternativa a ferramentas como Jira, Linear, Monday e ClickUp), atualmente com mais de 46.000 estrelas e mais de 100 colaboradores ativos. Trata-se de um dos projetos de gerenciamento de projetos open source que mais cresceram em popularidade no GitHub nos últimos anos. Devido a esse crescimento acelerado e ao alto volume de *issues* e *pull requests* abertos diariamente por uma comunidade ativa e diversificada, o repositório oferece uma base riquíssima de interações (issues abertas, PRs revisados e aprovados, discussões e *merges* frequentes), ideal para uma modelagem de rede complexa e atendendo ao critério mínimo de 5.000 estrelas exigido pelo enunciado.

## 2. Estratégia de Coleta de Dados
A mineração foi realizada através da API oficial do GitHub (REST, via biblioteca `PyGithub`), priorizando a extração de *Pull Requests* e *Issues*.
As interações foram mapeadas da seguinte forma:
- O **autor original** da Issue/PR é considerado o destino (alvo) da interação.
- Os **comentaristas e revisores** são a origem da interação.
- Robôs (como `dependabot` e `github-actions`) foram previamente filtrados por padrão para não poluir a análise com comportamentos automatizados que distorcem as métricas reais de colaboração humana (filtro que pode ser desativado via `--include-bots`).
- Em caso de limites de requisição (rate limit) da API do GitHub, o módulo de mineração realiza a rotação de tokens e salva *checkpoints* periódicos em cache local, permitindo retomar a coleta sem perda de progresso.

## 3. Modelagem do Grafo
O grafo desenhado é um **Grafo Simples e Direcionado**, ou seja, sem laços e sem arestas múltiplas, onde cada nó é um desenvolvedor (username).

Seguindo o escopo do trabalho, as relações são primeiramente modeladas em três grafos individuais (comentários, fechamentos de issues e revisões/aprovações/merges de PRs) e, em seguida, agregadas em um **único Grafo Integrado**. Para lidar com múltiplas interações entre os mesmos usuários, os pesos das arestas são somados de acordo com a "intensidade" técnica da colaboração:

| Tipo de Interação | Peso | Justificativa |
| :--- | :---: | :--- |
| Comentário em Issue ou Pull Request | **2** | Interação leve, tira-dúvidas ou sugestão. |
| Abertura de issue comentada por outro usuário | **3** | Criação de pauta ou bug report qualificado. |
| Revisão / Aprovação de Pull Request | **4** | Análise técnica profunda do código de outro desenvolvedor. |
| Merge de Pull Request | **5** | Validação final de integração no projeto (decisão do mantenedor). |

*Observação:* No grafo consolidado, se o Usuário A revisou um PR do Usuário B (Peso 4) e também comentou numa Issue do Usuário B (Peso 2), a aresta direcionada de `A -> B` terá peso total **6**.

## 4. Plano de Desenvolvimento
A ferramenta foi projetada baseada nos pilares de Orientação a Objetos. Foi concebida uma interface comum abstrata `AbstractGraph` que estipula os métodos (como `addEdge(u, v)`, `getVertexCount()`).

Para instanciar o grafo da colaboração extraída, utilizamos a estrutura concreta de **Lista de Adjacência (`AdjacencyListGraph`)**, visto que as redes sociais/colaborativas são tipicamente muito **esparsas**. O uso de Matriz de Adjacência para milhares de nós (a rede do Plane chegou a ~1.500 colaboradores na mineração realizada) resultaria em um desperdício enorme de memória computacional, visto que a grande maioria dos desenvolvedores só interage com uma minoria.

As análises incluem o uso de *PageRank*, *Betweenness* (Brandes) e *Closeness* (Wasserman & Faust) para medir influência e centralidade, além de *Label Propagation* para detecção de comunidades, tudo implementado do zero para respeitar a ausência de bibliotecas de grafos (NetworkX). Os dados extraídos podem ser consumidos independentemente pelo script de demonstração da API ou pelo pipeline central (`main.py`).