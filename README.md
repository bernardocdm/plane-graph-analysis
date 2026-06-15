# FastAPI Graph Analysis - Plane Repository

Análise de colaboração no ecossistema **Plane** (makeplane/plane) usando Grafos Direcionados e Ponderados baseados nas interações em Issues e Pull Requests.

---

## 📊 Sobre o Projeto

Este projeto automatiza a mineração de interações (comentários, fechamentos e revisões de código) entre desenvolvedores no repositório **Plane** (makeplane/plane), constrói uma rede social de colaboração usando uma **Estrutura de Grafo próprio (AdjacencyListGraph/AdjacencyMatrixGraph)** implementada do zero, calcula métricas de centralidade (PageRank, Betweenness de Brandes, Closeness de Wasserman & Faust), detecta comunidades através do algoritmo de **Label Propagation (Propagação de Rótulos)**, e exporta os dados para análise visual interativa no **Gephi** ou na web com **Sigma.js**.

### 🔄 Pipeline de Fluxo de Dados
```
GitHub API / Cache JSON
    ↓
src/mining/miner.py (mineração — outro integrante cuida)
    ↓
src/graph/builder.py (4 grafos)
    ↓
src/analysis/analyzer.py (centralidades + comunidades + métricas)
    ↓
src/export/exporter.py (JSON + CSV + GEXF)
    ↓
api_server.py (FastAPI)
    ↓
frontend/ (React + Sigma.js dashboard)
```

---

## 🚀 Como Executar Tudo

Siga os passos abaixo para preparar o ambiente e executar a pipeline completa do projeto.

### 1. Clonar o Repositório e Navegar até a Pasta
```bash
git clone https://github.com/bernardocdm/fastapi-graph-analysis.git
cd fastapi-graph-analysis
```

### 2. Criar e Ativar o Ambiente Virtual

* **No Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

* **No Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar as Dependências
```bash
pip install -r requirements.txt
```

### 4. Executar o Script Principal (`main.py`)

O pipeline central do projeto é controlado pelo arquivo `main.py`. Ele aceita diversos parâmetros de linha de comando para ajustar o comportamento da execução.

#### 💡 Cenários Comuns de Execução:

* **Modo Offline Rápido (Demonstração / Sem API Token):**
  Excelente para testar a pipeline instantaneamente sem se preocupar com limites de requisição da API do GitHub. Utiliza um gerador robusto de dados realistas e simulados.
  ```bash
  python main.py --use-mock
  ```

* **Modo Online Ativo (Mineração no GitHub):**
  Realiza conexões reais com o GitHub API. Se você tiver um token pessoal de acesso, defina-o na variável de ambiente `GITHUB_TOKEN`.
  
  *No Windows (PowerShell):*
  ```powershell
  $env:GITHUB_TOKEN="seu_token_aqui"
  python main.py --mine --limit 100
  ```
  
  *No Linux / macOS:*
  ```bash
  export GITHUB_TOKEN="seu_token_aqui"
  python main.py --mine --limit 100
  ```

* **Ignorar Cache Local e Forçar Nova Coleta:**
  Por padrão, os dados minerados ficam salvos em cache local. Use `--force-refresh` para atualizar as informações ativamente do GitHub:
  ```bash
  python main.py --mine --limit 200 --force-refresh
  ```

* **Analisar Repositório Plane e Incluir Bots de Automação:**
  Por padrão, robôs como o `dependabot` são filtrados. Você pode desativar essa restrição:
  ```bash
  python main.py --mine --repo "makeplane/plane" --limit 100 --include-bots
  ```

#### 🛠️ Parâmetros Disponíveis da CLI:

| Parâmetro | Tipo | Descrição | Padrão |
| :--- | :--- | :--- | :--- |
| `--mine` | Flag | Ativa a mineração real do repositório no GitHub (via API). | `False` |
| `--use-mock` | Flag | Força o uso imediato de dados simulados (offline). | `False` |
| `--limit` | Inteiro | Limite máximo de Issues/PRs a processar na mineração ativa. | `200` |
| `--include-bots` | Flag | Inclui bots automáticos (ex: `dependabot`) no grafo final. | `False` |
| `--force-refresh` | Flag | Ignora o arquivo de cache JSON local e força uma nova busca online. | `False` |
| `--repo` | String | Nome do repositório no GitHub para processamento. | `"makeplane/plane"` |

---

## 🧪 Como Executar os Testes Automatizados

A suíte de testes unitários garante a estabilidade de toda a lógica do grafo, cálculo de centralidades e exportadores.

Execute os testes com cobertura de código integrada usando o comando:
```bash
pytest tests/ -v --cov=src
```

---

## 🛠️ O Que Já Foi Feito (Implementado)

O projeto conta com uma infraestrutura robusta, testada e pronta para produção:

### Backend

1. **Configuração Unificada (`src/config.py`):**
   * Criação automatizada de diretórios de trabalho.
   * Gerenciamento de credenciais via variáveis de ambiente.

2. **Módulo de Mineração Inteligente (`src/mining/miner.py`):**
   * Conexão ativa com o GitHub API do repositório Plane.
   * Coleta granular de Issues (1219), Pull Requests (4347), Comentários e Revisões.
   * Sistema inteligente de **cache local** em formato JSON.
   * Gerador avançado de **dados realistas simulados (Mock)**.

3. **Modelagem de Grafo de Colaboração (`src/graph/builder.py`):**
   * Construção de **4 grafos direcionados e ponderados**:
     * **Grafo 1 (Comentários):** A comentou em issue/PR de B → aresta A→B, peso 2.0
     * **Grafo 2 (Fechamentos):** A fechou issue de B → aresta A→B, peso 3.0
     * **Grafo 3 (Reviews/Merges):** Revisão (peso 4.0), Merge (peso 5.0)
     * **Grafo 4 (Integrado):** Combina todos, acumula pesos
   * Implementação própria de **Lista de Adjacência** e **Matriz de Adjacência**.
   * Filtro opcional e dinâmico de bots (dependabot, plane-bot, github-actions, etc).
   * Resultado: **1496 nós, 2313 arestas** (dados reais do Plane).

4. **Analisador de Métricas de Rede (`src/analysis/analyzer.py`):**
   * **Centralidades (implementadas do zero):**
     * Degree Centrality (in/out normalizados)
     * PageRank (Power Iteration, d=0.85, 100 iterações)
     * Betweenness Centrality (Algoritmo de Brandes, O(V·E))
     * Closeness Centrality (Wasserman & Faust para grafos desconexos)
   * **Detecção de Comunidades:** Label Propagation (20 iterações, determinístico)
   * **Métricas Globais:** Densidade, reciprocidade, clustering, assortatividade, WCC, SCC (Kosaraju), diâmetro
   * 100% implementado manualmente (sem NetworkX).

5. **Módulo de Exportação e Saídas (`src/export/exporter.py`):**
   * **`.gexf` (Gephi):** Enriquecido com métricas e comunidades embutidas.
   * **`.json` (Node-Link):** Padrão para consumo por Sigma.js e outras bibliotecas web.
   * **`.csv` (Metrics Table):** Estatísticas consolidadas de cada desenvolvedor.

6. **Interface de Linha de Comando (`main.py`):**
   * Orquestração fluida de todo o processo em 4 etapas.
   * Exibição automatizada de estatísticas globais e ranking Top 10 por PageRank.

7. **Suíte Completa de Testes (`tests/`):**
   * `test_graph.py`: 9+ testes parametrizados (AdjacencyList + AdjacencyMatrix)
   * `test_all.py`: 5 testes de integração do pipeline
   * 100% dos testes passando.

### Frontend

8. **API Server FastAPI (`api_server.py`):**
   * Endpoints RESTful para consumo do frontend:
     * `GET /api/graph` - Grafo integrado completo
     * `GET /api/graph/comments` - Grafo de comentários
     * `GET /api/graph/closings` - Grafo de fechamentos
     * `GET /api/graph/reviews` - Grafo de reviews/merges
     * `GET /api/metrics` - Métricas globais
   * CORS configurado para frontend local.

9. **Dashboard React (`frontend/`):**
   * **Componentes:**
     * `App.jsx`: Layout principal com header/footer
     * `DashboardMetrics.jsx`: 4 cards + tabela de ranking
     * `GraphTabs.jsx`: Abas para trocar entre 4 grafos
     * `GraphVisualization.jsx`: Renderização com Sigma.js
   * **Funcionalidades:**
     * 1496 nós renderizados interativamente
     * 2313 arestas visíveis
     * Cores por comunidade (Label Propagation)
     * Tamanho dos nós proporcional a PageRank
     * Zoom, pan, click interativo
     * Botão download GEXF para Gephi
   * **Tecnologias:** React 18, Sigma.js, Tailwind CSS, Vite

---

## 📁 Estrutura de Pastas do Projeto

```text
fastapi-graph-analysis/
│
├── main.py                   # CLI principal — orquestra o pipeline
├── api_server.py             # Servidor FastAPI
├── requirements.txt          # Dependências Python
├── pytest.ini                # Configuração do pytest
│
├── src/                      # Código-fonte do backend
│   ├── config.py             # Caminhos globais
│   ├── mining/
│   │   └── miner.py          # GitHubMiner: coleta + mock data
│   ├── graph/
│   │   ├── api.py            # AbstractGraph (7 métodos abstratos)
│   │   ├── adjacency_list.py # AdjacencyListGraph
│   │   ├── adjacency_matrix.py # AdjacencyMatrixGraph
│   │   └── builder.py        # CollaborationGraphBuilder (4 grafos)
│   ├── analysis/
│   │   └── analyzer.py       # Centralidades + Label Propagation + métricas
│   └── export/
│       └── exporter.py       # GEXF + JSON + CSV
│
├── tests/
│   ├── test_all.py           # 5 testes de integração
│   └── test_graph.py         # 9+ testes da API de grafos
│
├── data/                     # Gerado em runtime
│   ├── raw/                  # Cache JSON bruto (.gitignore)
│   ├── processed/
│   │   └── graph_state.json
│   └── outputs/
│       ├── collaboration_graph.json
│       ├── collaboration_graph_*.json (3 individuais)
│       ├── graph_*.gexf (4 arquivos)
│       └── collaboration_metrics.csv
│
├── frontend/                 # Interface web React
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       ├── hooks/
│       │   └── useGraphData.js
│       └── components/
│           ├── DashboardMetrics.jsx
│           ├── GraphTabs.jsx
│           └── GraphVisualization.jsx
│
├── docs/
│   ├── class-diagram.puml    # Diagrama UML
│   └── flow-diagram.puml     # Diagrama de fluxo
│
└── README.md                 # Este arquivo
```

---

## 🔗 Links e Recursos

* **Plane (Repositório Alvo):** [https://github.com/makeplane/plane](https://github.com/makeplane/plane)
* **Projeto (GitHub):** [https://github.com/bernardocdm/fastapi-graph-analysis](https://github.com/bernardocdm/fastapi-graph-analysis)
* **Gephi (Visualização):** [https://gephi.org/](https://gephi.org/)
* **Sigma.js (Web):** [https://www.sigmajs.org/](https://www.sigmajs.org/)
* **PyGithub (API):** [https://pygithub.readthedocs.io/](https://pygithub.readthedocs.io/)

---

## 👥 Divisão de Tarefas

| Responsabilidade | Responsável |
|-----------------|------------|
| **Frontend (React + Sigma.js)** | Bernardo |
| **API Server (FastAPI)** | Bernardo |
| **Testes unitários** | Bernardo + Matheus |
| **Diagramas UML** | Bernardo + Arthur |
| **Slides da apresentação** | Bernardo |
| **Mineração (GitHub API)** | Arthur |
| **Relatório LaTeX** | Arthur |
| **Lógica dos 4 grafos** | Arthur + Matheus |
| **Implementação das classes de grafo** | Matheus |
| **Análise (Centralidades + Comunidades)** | Matheus |
| **Exportação (GEXF + JSON + CSV)** | Matheus |
| **Testes de integração** | Matheus |

---

## 📊 Dados e Resultados

**Repositório Analisado:** Plane (makeplane/plane)
**Período:** Dados históricos até Janeiro/2024

**Estatísticas:**
- **Issues processadas:** 1219
- **Pull Requests processados:** 4347
- **Usuários únicos:** 1496
- **Interações (arestas):** 2313
- **Densidade do grafo:** 0.0010
- **Reciprocidade:** 0.0510
- **Diâmetro:** 10
- **Componentes fracos:** 159
- **Componentes fortes (Kosaraju):** 1453

**Top 5 Colaboradores (PageRank):**
1. sriramveeraghanta - 0.1207
2. Prince-Shivaram - 0.1191
3. gurusainath - 0.1191
4. pablohashescobar - 0.1241
5. ChandanTeerth - 0.1141

---

## 🎯 Status do Projeto

✅ **Completo e Funcional**

- [x] Mineração de dados (GitHub API + Mock)
- [x] Construção de 4 grafos (implementações próprias)
- [x] Análise completa (centralidades + comunidades)
- [x] Exportação (JSON + GEXF + CSV)
- [x] API Server (FastAPI)
- [x] Frontend (React + Sigma.js)
- [x] Testes (30+ testes passando)
- [x] Documentação (Diagramas UML)

---

Desenvolvido para a disciplina de **Teoria de Grafos e Computabilidade - PUC Minas**
