import { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000/api';

export function useGraphData() {
    const [graphData, setGraphData] = useState(null);
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const graphRes = await fetch(`${API_URL}/graph`);
                if (!graphRes.ok) throw new Error('Grafo não encontrado');
                const graph = await graphRes.json();

                const metricsRes = await fetch(`${API_URL}/metrics`);
                if (!metricsRes.ok) throw new Error('Métricas não encontradas');
                const metricsData = await metricsRes.json();

                setGraphData(graph);
                setMetrics(metricsData);
                setLoading(false);
            } catch (err) {
                setError(err.message);
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return { graphData, metrics, loading, error };
}