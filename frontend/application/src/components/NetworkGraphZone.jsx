import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const COLORS = [
    '#1f77b4', // น้ำเงิน
    '#ff7f0e', // ส้ม
    '#2ca02c', // เขียว
    '#d62728', // แดง
    '#9467bd', // ม่วง
    '#8c564b', // น้ำตาล
    '#e377c2', // ชมพู
    '#7f7f7f', // เทา
    '#bcbd22', // เหลืองขี้ม้า
    '#17becf'  // ฟ้า
];

const NetworkGraphZone = () => {
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const fgRef = useRef();

    useEffect(() => {
        fetch('http://127.0.0.1:8000/api/graph/')
            .then(res => res.json())
            .then(data => {
                setGraphData(data);
                setLoading(false);
            })
            .catch(err => console.error(err));
    }, []);

    useEffect(() => {
        if (fgRef.current) {
            fgRef.current.d3Force('charge').strength(-200);
            fgRef.current.d3Force('link').distance(70);
            fgRef.current.d3ReheatSimulation();
        }
    }, [graphData]);

    // 2. คำนวณ Map ระหว่างชื่อกลุ่มกับสี
    //ใช้ useMemo เพื่อไม่ให้คำนวณใหม่ทุกครั้งที่ render
    const clusterColorMap = useMemo(() => {
        const groups = [...new Set(graphData.nodes.map(node => node.group))];
        const map = {};
        
        groups.forEach((group, index) => {
            //ถ้าเป็นกลุ่ม Uncategorized ให้เป็นสีเทาอ่อน
            if (group === "Uncategorized" || group === "Unknown") {
                map[group] = "#e0e0e0"; 
            } else {
                //วนใช้สีใน COLORS
                map[group] = COLORS[index % COLORS.length];
            }
        });
        return map;
    }, [graphData]);

    const paintNode = useCallback((node, ctx, globalScale) => {
        const label = node.name;
        const subLabel = [node.faculty, node.dept].filter(Boolean).join(', ');

        const fontSize = 12 / globalScale;
        const subFontSize = 10 / globalScale;
        
        const radius = Math.sqrt(node.val) * 2 + 2;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
        
        //3. ใช้สีจาก Map ที่เราสร้างแทนให้ Library สุ่ม
        ctx.fillStyle = clusterColorMap[node.group] || '#333';
        
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();

        if (globalScale > 1.5 || node.val > 10) { 
            ctx.font = `bold ${fontSize}px Sans-Serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#000';
            ctx.fillText(label, node.x, node.y + radius + 6);

            if (subLabel) {
                ctx.font = `${subFontSize}px Sans-Serif`;
                ctx.fillStyle = '#666';
                ctx.fillText(subLabel, node.x, node.y + radius + 6 + fontSize);
            }
        }
    }, [clusterColorMap]);

    if (loading) return <div style={{textAlign: 'center', padding: '50px'}}>Building Network Graph...</div>;

    return (
        <div style={styles.container}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
                <div>
                    <h2 style={styles.header}>Researcher Collaboration Network</h2>
                    <p style={styles.subHeader}>
                        Size represents the number of papers. Colors represent research clusters.
                    </p>
                </div>
            </div>

            {/* 4. Legend (อธิบายสี) */}
            <div style={styles.legendContainer}>
                {Object.keys(clusterColorMap).map((group) => (
                    <div key={group} style={styles.legendItem}>
                        <span style={{...styles.colorBox, backgroundColor: clusterColorMap[group]}}></span>
                        <span style={styles.legendText}>{group}</span>
                    </div>
                ))}
            </div>

            <div style={styles.graphWrapper}>
                <ForceGraph2D
                    ref={fgRef}
                    graphData={graphData}
                    nodeColor={node => clusterColorMap[node.group]}
                    nodeLabel="name"
                    nodeVal="val"
                    backgroundColor="#f9f9f9"
                    nodeCanvasObject={paintNode}
                    linkColor={() => '#cccccc'}
                    linkWidth={1}
                    onNodeClick={node => {
                        fgRef.current.centerAt(node.x, node.y, 1000);
                        fgRef.current.zoom(3, 2000);
                    }}
                    width={1200} 
                    height={600}
                />
            </div>
            
            <div style={styles.legendHint}>
                * Scroll to Zoom, Drag to Pan, Click Node to Focus
            </div>
        </div>
    );
};

const styles = {
    container: {
        padding: '20px',
        backgroundColor: '#fff',
        borderRadius: '8px',
        boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
        marginBottom: '20px'
    },
    header: { margin: '0 0 10px 0', color: '#333' },
    subHeader: { margin: '0 0 20px 0', color: '#666', fontSize: '14px' },
    //Styles for Legend
    legendContainer: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '15px',
        marginBottom: '15px',
        padding: '10px',
        backgroundColor: '#f8f9fa',
        borderRadius: '6px',
        border: '1px solid #eee'
    },
    legendItem: {
        display: 'flex',
        alignItems: 'center',
        gap: '6px'
    },
    colorBox: {
        width: '12px',
        height: '12px',
        borderRadius: '50%',
        display: 'inline-block',
        border: '1px solid rgba(0,0,0,0.1)'
    },
    legendText: {
        fontSize: '12px',
        color: '#555',
        fontWeight: '500',
        textTransform: 'capitalize'
    },
    graphWrapper: {
        border: '1px solid #eee',
        borderRadius: '4px',
        overflow: 'hidden',
        display: 'flex',
        justifyContent: 'center'
    },
    legendHint: {
        marginTop: '10px',
        fontSize: '12px',
        color: '#999',
        textAlign: 'right'
    }
};

export default NetworkGraphZone;