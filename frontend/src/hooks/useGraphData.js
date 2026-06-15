import { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000/api';

export function useGraphData() {
    const [contributors, setContributors] = useState(null);
    const [metrics, setMetrics] = useState(null);
    const [graphData, setGraphData] = useState(null);
    const [graphs, setGraphs] = useState({
        integrated: null,
        comments: null,
        closings: null,
        reviews: null,
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Buscar grafo integrado
                const graphRes = await fetch(`${API_URL}/graph`);
                if (!graphRes.ok) throw new Error('Grafo não encontrado');
                const graph = await graphRes.json();

                // Buscar 3 grafos individuais
                const commentsRes = await fetch(`${API_URL}/graph/comments`);
                const closingsRes = await fetch(`${API_URL}/graph/closings`);
                const reviewsRes = await fetch(`${API_URL}/graph/reviews`);

                console.log('API responses:', {
                    comments: commentsRes.status,
                    closings: closingsRes.status,
                    reviews: reviewsRes.status,
                });

                const commentsData = commentsRes.ok ? await commentsRes.json() : null;
                const closingsData = closingsRes.ok ? await closingsRes.json() : null;
                const reviewsData = reviewsRes.ok ? await reviewsRes.json() : null;

                console.log('Dados carregados:', {
                    integrated: graph.nodes?.length,
                    comments: commentsData?.nodes?.length,
                    closings: closingsData?.nodes?.length,
                    reviews: reviewsData?.nodes?.length,
                });

                // Buscar métricas
                const metricsRes = await fetch(`${API_URL}/metrics`);
                if (!metricsRes.ok) throw new Error('Métricas não encontradas');
                const metricsData = await metricsRes.json();

                // Ordenar por PageRank
                const orderedContributors = (graph.nodes || [])
                    .sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0));

                setGraphData(graph);
                setGraphs({
                    integrated: graph,
                    comments: commentsData,
                    closings: closingsData,
                    reviews: reviewsData,
                });
                setContributors(orderedContributors);
                setMetrics(metricsData);
                setLoading(false);
            } catch (err) {
                console.error('Erro ao buscar:', err);
                setError(err.message);
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return { contributors, metrics, graphData, graphs, loading, error };
}