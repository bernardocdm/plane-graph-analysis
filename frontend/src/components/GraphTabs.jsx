import { useState } from 'react';
import { GraphVisualization } from './GraphVisualization';

export function GraphTabs({ graphs }) {
    const [activeTab, setActiveTab] = useState('integrated');

    if (!graphs) return <div className="p-4 text-gray-500">Nenhum grafo carregado</div>;

    const tabs = [
        { id: 'integrated', label: '📊 Grafo Integrado', color: 'blue', gexf: 'graph_integrated.gexf' },
        { id: 'comments', label: '💬 Comentários', color: 'green', gexf: 'graph_comments.gexf' },
        { id: 'closings', label: '🔒 Fechamentos', color: 'purple', gexf: 'graph_closings.gexf' },
        { id: 'reviews', label: '✅ Reviews/Merges', color: 'orange', gexf: 'graph_reviews.gexf' },
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

    const currentTab = tabs.find(t => t.id === activeTab);
    const currentGraph = graphs[activeTab];
    const hasData = currentGraph && currentGraph.nodes && currentGraph.nodes.length > 0;

    return (
        <section>
            {/* Botões de abas para trocar entre grafos */}
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

            {/* Descrição do grafo ativo */}
            <div className="mb-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
                {getDescription()}
            </div>

            {/* Grafo Sigma.js + Button Download */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
                {hasData ? (
                    <>
                        {/* Grafo */}
                        <GraphVisualization graphData={currentGraph} />

                        {/* Button Download GEXF logo abaixo do grafo */}
                        <div className="p-4 bg-blue-50 border-t border-blue-200 flex items-center justify-between">
                            <div>
                                <p className="text-sm text-blue-800 font-semibold">
                                    💡 Visualização completa no Gephi
                                </p>
                                <p className="text-xs text-blue-600 mt-1">
                                    Layout força-dirigido, cores por comunidade e controles avançados
                                </p>
                            </div>

                            {/*
                              Antes: href={`/data/outputs/${currentTab.gexf}`}
                              Esse caminho não existe no Vite (porta 5173), então cai no
                              fallback de SPA e baixa o index.html (<!doctype html>...),
                              quebrando o import no Gephi.

                              Agora: usa o endpoint /api/download/<arquivo>.gexf do
                              api_server.py (porta 8000), que o Vite já proxyia via
                              '/api' -> 'http://localhost:8000' (vite.config.js).
                            */}
                            <a
                                href={`/api/download/${currentTab.gexf}`}
                                download={currentTab.gexf}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition whitespace-nowrap"
                            >
                                📥 Baixar GEXF
                            </a>
                        </div>
                    </>
                ) : (
                    <div className="h-96 flex items-center justify-center text-gray-400">
                        <p>Sem dados para este grafo</p>
                    </div>
                )}
            </div>
        </section>
    );
}