import { useEffect, useRef } from 'react';
import Sigma from 'sigma';
import Graph from 'graphology';

export function GraphVisualization({ graphData }) {
    const containerRef = useRef(null);

    useEffect(() => {
        if (!graphData || !containerRef.current) return;

        console.log('Renderizando grafo com', graphData.nodes?.length, 'nós');

        const g = new Graph();

        // Adicionar nós
        graphData.nodes.forEach(node => {
            g.addNode(node.id, {
                label: node.id,
                size: Math.max(5, (node.pagerank || 0.01) * 100),
                color: getColorByCommunity(node.community || 0),
                x: Math.random() * 100,
                y: Math.random() * 100,
            });
        });

        // Adicionar arestas
        graphData.links.forEach((link, idx) => {
            try {
                g.addEdge(`edge-${idx}`, link.source, link.target, {
                    weight: link.weight || 1,
                });
            } catch (e) {
                console.warn(`Aresta ignorada: ${link.source} -> ${link.target}`);
            }
        });

        console.log('Grafo pronto:', g.order, 'nós,', g.size, 'arestas');

        // Inicializar Sigma
        const sigma = new Sigma(g, containerRef.current, {
            renderEdgeLabels: false,
            defaultEdgeColor: '#ccc',
            defaultNodeColor: '#fff',
            defaultEdgeType: 'directed',
        });

        console.log('Sigma renderizado com sucesso');

        return () => {
            sigma.kill();
        };
    }, [graphData]);

    return (
        <div
            ref={containerRef}
            style={{
                width: '100%',
                height: '600px',
                backgroundColor: '#f3f4f6',
                borderRadius: '8px',
            }}
        />
    );
}

function getColorByCommunity(communityId) {
    const colors = [
        '#FF6B6B',  // vermelho
        '#4ECDC4',  // turquesa
        '#45B7D1',  // azul
        '#FFA07A',  // salmão
        '#98D8C8',  // menta
        '#F7DC6F',  // amarelo
    ];
    return colors[communityId % colors.length];
}