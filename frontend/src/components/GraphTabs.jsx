import { useState } from 'react';
import { GraphVisualization } from './GraphVisualization';

export function GraphTabs({ graphs }) {
    const [activeTab, setActiveTab] = useState('integrated');

    if (!graphs) return <div className="p-4 text-gray-500">Nenhum grafo carregado</div>;

    const tabs = [
        { id: 'integrated', label: '📊 Grafo Integrado', color: 'blue' },
        { id: 'comments', label: '💬 Comentários', color: 'green' },
        { id: 'closings', label: '🔒 Fechamentos', color: 'purple' },
        { id: 'reviews', label: '✅ Reviews/Merges', color: 'orange' },
    ];

    const getButtonColor = (color) => {
        const colors = {
            blue: 'bg-blue-600 hover:bg-blue-700',
            green: 'bg-green-600 hover:bg-green-700',
            purple: 'bg-purple-600 hover:bg-purple-700',
            orange: 'bg-orange-600 hover:bg-orange-700',
        };
        return colors[color] || colors.blue;
    };

    const getDescription = () => {
        switch (activeTab) {
            case 'integrated':
                return '📊 Grafo Integrado: Combina todos os tipos de interação (comentários + fechamentos + reviews/merges)';
            case 'comments':
                return '💬 Grafo de Comentários: Mostra quem comentou em issues e PRs de quem (peso: 2)';
            case 'closings':
                return '🔒 Grafo de Fechamentos: Mostra quem fechou issues de quem (peso: 3)';
            case 'reviews':
                return '✅ Grafo de Reviews/Merges: Mostra quem revisou e fez merge de PRs (peso: 4 e 5)';
            default:
                return '';
        }
    };

    const currentGraph = graphs[activeTab];
    const hasData = currentGraph && currentGraph.nodes && currentGraph.nodes.length > 0;

    return (
        <section>
            {/* Botões de abas */}
            <div className="flex gap-2 mb-6 flex-wrap">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-4 py-2 rounded-lg font-semibold transition text-white ${
                            activeTab === tab.id
                                ? getButtonColor(tab.color)
                                : 'bg-gray-400 hover:bg-gray-500'
                        }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Botão Gephi */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800 mb-3">
                    💡 <strong>Visualização completa:</strong> Importe o arquivo GEXF no Gephi para layout força-dirigido e controles avançados
                </p>
                
                    href="http://localhost:8000/api/graph"
                    download="collaboration_graph.gexf"
                    className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition"
                >
                    📥 Baixar GEXF para Gephi
                </a>
                <p className="text-xs text-gray-500 mt-2">
                    Abra com: Gephi → File → Open → collaboration_graph.gexf
                </p>
            </div>

            {/* Descrição do grafo */}
            <div className="mb-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
                {getDescription()}
            </div>

            {/* Grafo */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                {hasData ? (
                    <GraphVisualization graphData={currentGraph} />
                ) : (
                    <div className="h-96 flex items-center justify-center text-gray-400">
                        <p>Sem dados para este grafo</p>
                    </div>
                )}
            </div>
        </section>
    );
}