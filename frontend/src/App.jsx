import { useState } from 'react';
import { useGraphData } from './hooks/useGraphData';
import { DashboardMetrics } from './components/DashboardMetrics';
import { GraphVisualization } from './components/GraphVisualization';
import './index.css';
import { GraphTabs } from './components/GraphTabs';

function App() {
    const { contributors, metrics, graphData, graphs, loading, error } = useGraphData();
    const [showGraph, setShowGraph] = useState(false);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-gray-100">
                <div className="text-center">
                    <div className="animate-spin text-4xl mb-4">⏳</div>
                    <p className="text-gray-600">Carregando análise...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-screen bg-red-50">
                <div className="text-center">
                    <p className="text-red-600 font-bold">❌ Erro ao carregar</p>
                    <p className="text-red-500 mb-4">{error}</p>
                    <div className="text-sm text-gray-600 bg-white p-4 rounded">
                        <p className="font-bold mb-2">Checklist:</p>
                        <ul className="space-y-1">
                            <li>✓ python api_server.py rodando em localhost:8000?</li>
                            <li>✓ python main.py --use-mock foi executado?</li>
                            <li>✓ http://localhost:8000/docs abre?</li>
                        </ul>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
            <header className="bg-white shadow">
                <div className="max-w-7xl mx-auto px-6 py-8 flex justify-between items-center">
                    <div>
                        <h1 className="text-4xl font-bold text-gray-900">FastAPI Graph Analysis</h1>
                        <p className="text-gray-600 mt-2">Dashboard de análise de colaboração no FastAPI</p>
                    </div>
                    
                    {/* Botão Sigma */}
                    <button
                        onClick={() => setShowGraph(!showGraph)}
                        className={`px-6 py-2 rounded-lg font-semibold transition ${
                            showGraph
                                ? 'bg-blue-600 text-white hover:bg-blue-700'
                                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                    >
                        {showGraph ? '🔒 Ocultar Grafo' : '📊 Mostrar Grafo'}
                    </button>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-12 space-y-8">
                {/* Seção do Grafo Sigma */}
                {showGraph && graphs && (
                <section>
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">Visualização dos Grafos</h2>
                    <GraphTabs graphs={graphs} />

                    <p className="text-xs text-gray-500 mt-2">
                                        💡 Dica: Use scroll para zoom, arraste para mover, clique em nós para mais detalhes
                                    </p>
                </section>
            )}

                {/* Dashboard Metrics */}
                {metrics && contributors && (
                    <DashboardMetrics 
                        metrics={metrics} 
                        contributors={contributors} 
                    />
                )}
            </main>

            <footer className="bg-white border-t border-gray-200 mt-12">
                <div className="max-w-7xl mx-auto px-6 py-6 text-center text-gray-600 text-sm">
                    <p>Visualize também em <strong>Gephi</strong> usando os arquivos em <code className="bg-gray-100 px-2 py-1 rounded">data/outputs/collaboration_graph.gexf</code></p>
                </div>
            </footer>
        </div>
    );
}

export default App;
