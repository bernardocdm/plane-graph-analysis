import { useGraphData } from './hooks/useGraphData';
import { GraphViewer } from './components/GraphViewer';
import { StatsPanel } from './components/StatsPanel';
import './index.css';

function App() {
    const { graphData, metrics, loading, error } = useGraphData();

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-gray-100">
                <div className="text-center">
                    <div className="animate-spin text-4xl mb-4">⏳</div>
                    <p className="text-gray-600">Carregando grafo...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-screen bg-red-50">
                <div className="text-center">
                    <p className="text-red-600 font-bold">❌ Erro</p>
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
        <div className="flex h-screen bg-gray-100">
            <aside className="w-96 bg-white shadow-lg p-6 overflow-y-auto border-r border-gray-200">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-800">FastAPI</h1>
                    <p className="text-sm text-gray-500">Collaboration Graph</p>
                </div>
                
                {metrics && <StatsPanel metrics={metrics} />}
            </aside>

            <main className="flex-1">
                {graphData && <GraphViewer data={graphData} />}
            </main>
        </div>
    );
}

export default App;