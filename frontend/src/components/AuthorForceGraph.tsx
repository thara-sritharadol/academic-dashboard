import React, { useEffect, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { useNavigate } from "react-router-dom";
import { ZoomIn, ZoomOut, Maximize, Filter } from "lucide-react";

interface AuthorForceGraphProps {
  graphData: { nodes: any[]; links: any[] };
  loading: boolean;
}

const COLOR_TU = "#FFD13F";
const COLOR_EXTERNAL = "#d1d5db";
const COLOR_TEXT = "#1f2937";

const AuthorForceGraph: React.FC<AuthorForceGraphProps> = ({
  graphData,
  loading,
}) => {
  const navigate = useNavigate();
  const fgRef = useRef<any>(null);

  // Physics for Graph
  useEffect(() => {
    if (!loading && fgRef.current && graphData.nodes.length > 0) {
      fgRef.current.d3Force("charge")?.strength(-100);
      fgRef.current.d3Force("link")?.distance(80);
    }
  }, [graphData, loading]);

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-400 bg-slate-50/50 min-h-[600px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
          Generating network physics...
        </div>
      </div>
    );
  }

  if (graphData.nodes.length === 0) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-slate-50/50 min-h-[600px]">
        <Filter size={48} className="text-slate-300 mb-4" />
        <p className="text-lg font-medium text-slate-600">
          No network data available
        </p>
        <p className="text-sm mt-1 text-slate-400">
          Try selecting different topics from the filter above.
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Zoom Contoller */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-2 bg-white/80 p-2 rounded-lg border border-slate-200 backdrop-blur-sm shadow-sm">
        <button
          onClick={() => fgRef.current?.zoom(fgRef.current.zoom() * 1.2, 400)}
          className="p-1.5 hover:bg-slate-100 rounded text-slate-700"
          title="Zoom In"
        >
          <ZoomIn size={20} />
        </button>
        <button
          onClick={() => fgRef.current?.zoom(fgRef.current.zoom() / 1.2, 400)}
          className="p-1.5 hover:bg-slate-100 rounded text-slate-700"
          title="Zoom Out"
        >
          <ZoomOut size={20} />
        </button>
        <button
          onClick={() => fgRef.current?.zoomToFit(400, 50)}
          className="p-1.5 hover:bg-slate-100 rounded text-slate-700"
          title="Fit to Screen"
        >
          <Maximize size={20} />
        </button>
      </div>

      {/* Graph */}
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        width={typeof window !== "undefined" ? window.innerWidth - 300 : 800}
        height={typeof window !== "undefined" ? window.innerHeight - 150 : 600}
        nodeLabel="name"
        onNodeClick={(node: any) => navigate(`/authors/${node.id}`)}
        onNodeHover={(node: any) => {
          const canvas = fgRef.current?.canvas;
          if (canvas) canvas.style.cursor = node ? "pointer" : "default";
        }}
        nodeCanvasObject={(node: any, ctx, globalScale) => {
          const label = node.name;
          const isTu = node.faculty && node.faculty.trim() !== "";
          const nodeRadius = Math.max(3, (node.val || 1) * 0.8 + 2);

          ctx.beginPath();
          ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI, false);
          ctx.fillStyle = isTu ? COLOR_TU : COLOR_EXTERNAL;
          ctx.fill();

          ctx.lineWidth = 1 / globalScale;
          ctx.strokeStyle = isTu ? "#C3002F" : "#9ca3af";
          ctx.stroke();

          if (globalScale > 2 || (globalScale > 1.2 && node.val > 3)) {
            const fontSize = 11 / globalScale;
            ctx.font = `${fontSize}px Inter, Sans-Serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillStyle = COLOR_TEXT;
            ctx.fillText(label, node.x, node.y + nodeRadius + 3 / globalScale);
          }
        }}
        linkColor={(link: any) => {
          const source = typeof link.source === "object" ? link.source : null;
          const target = typeof link.target === "object" ? link.target : null;
          if (!source || !target) return "rgba(148, 163, 184, 0.3)";

          const sourceIsTu = source.faculty && source.faculty.trim() !== "";
          const targetIsTu = target.faculty && target.faculty.trim() !== "";

          if (sourceIsTu && targetIsTu) return "rgba(195, 0, 47, 1)";
          return "rgba(148, 163, 184, 0.5)";
        }}
        linkWidth={(link: any) => Math.sqrt(link.weight) * 1.2}
        d3VelocityDecay={0.25}
        cooldownTicks={120}
        onEngineStop={() => fgRef.current?.zoomToFit(400, 70)}
      />
    </>
  );
};

export default AuthorForceGraph;
