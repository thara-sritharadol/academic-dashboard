// src/pages/AuthorNetwork.tsx
import { useState, useEffect, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import api from "../services/api";
import { Users, ZoomIn, ZoomOut, Maximize, Filter } from "lucide-react";

export default function AuthorNetwork() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);

  const [availableDomains, setAvailableDomains] = useState<string[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string>("");

  const [uniqueGroups, setUniqueGroups] = useState<string[]>([]);

  const fgRef = useRef<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [networkRes, topicsRes] = await Promise.all([
          api.get("/network/authors/", {
            params: {
              limit: 200,
              domain: selectedDomain || undefined,
            },
          }),
          api.get("/analytics/topics/"),
        ]);

        setGraphData(networkRes.data);
        setAvailableDomains(topicsRes.data);

        // ดึงชื่อกลุ่มทั้งหมดที่มีในกราฟตอนนี้ออกมาใส่ State
        const groups = Array.from(
          new Set(networkRes.data.nodes.map((n: any) => n.group)),
        ) as string[];
        setUniqueGroups(groups.sort());
      } catch (error) {
        console.error("Error fetching network data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedDomain]);

  const colors = [
    "#3b82f6",
    "#10b981",
    "#f59e0b",
    "#8b5cf6",
    "#ef4444",
    "#ec4899",
    "#14b8a6",
    "#f97316",
    "#6366f1",
    "#84cc16",
  ];

  // ฟังก์ชันให้สี โดยล็อคสีตาม Index ของ availableDomains เพื่อให้สีคงที่เหมือนหน้า Dashboard
  const getColor = (group: string) => {
    if (group === "Unknown") return "#cbd5e1";
    const idx = availableDomains.indexOf(group);
    return idx !== -1 ? colors[idx % colors.length] : "#cbd5e1";
  };

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <div className="p-8 pb-4 shrink-0 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
            <Users className="text-blue-600" /> Author Collaboration Network
          </h1>
          <p className="text-slate-500">
            Node size represents the number of published papers. Line thickness
            represents the frequency of collaboration.
          </p>
        </div>

        <div className="w-72 relative z-20">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Filter size={18} className="text-slate-400" />
          </div>
          <select
            className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white shadow-sm"
            value={selectedDomain}
            onChange={(e) => setSelectedDomain(e.target.value)}
          >
            <option value="">All Domains (Global Network)</option>
            {availableDomains.map((domainStr) => {
              const shortName = domainStr.split(":")[0];
              return (
                <option key={domainStr} value={domainStr}>
                  {shortName}
                </option>
              );
            })}
          </select>
        </div>
      </div>

      <div className="flex-1 m-8 mt-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
        {/* ปุ่มควบคุม Zoom */}
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

        {/* กล่อง Legend อธิบายสี (โชว์มุมขวาล่าง) */}
        {uniqueGroups.length > 0 && !loading && (
          <div className="absolute bottom-4 right-4 z-10 bg-white/95 p-4 rounded-xl border border-slate-200 shadow-lg max-h-[40%] overflow-y-auto custom-scrollbar w-64">
            <h3 className="text-sm font-bold text-slate-700 mb-3 uppercase tracking-wider">
              Topic Legend
            </h3>
            <div className="space-y-2">
              {uniqueGroups.map((group) => {
                const shortName = group.split(":")[0]; // โชว์แค่ Topic 0, Topic 1
                return (
                  <div
                    key={group}
                    className="flex items-start gap-2 text-sm"
                    title={group}
                  >
                    <span
                      className="w-3 h-3 rounded-full mt-1 shrink-0 shadow-sm"
                      style={{ backgroundColor: getColor(group) }}
                    ></span>
                    <span className="text-slate-600 leading-tight">
                      <span className="font-semibold text-slate-800">
                        {shortName}
                      </span>
                      <span className="block text-xs text-slate-400 truncate">
                        {group.split(":").slice(1).join(":")}
                      </span>
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {loading ? (
          <div className="w-full h-full flex items-center justify-center text-slate-400">
            Applying filters and generating physics...
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div className="w-full h-full flex items-center justify-center text-slate-500 bg-slate-50/50">
            No collaboration data found for this domain.
          </div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            width={
              typeof window !== "undefined" ? window.innerWidth - 300 : 800
            }
            height={
              typeof window !== "undefined" ? window.innerHeight - 150 : 600
            }
            // ยังคงให้มี Tooltip ตอนเอาเมาส์ชี้เหมือนเดิม
            nodeLabel="name"
            nodeCanvasObject={(node: any, ctx, globalScale) => {
              // 1. คำนวณขนาด Node (ให้ล้อกับค่า val หรือจำนวนเปเปอร์)
              const nodeRadius = Math.sqrt(node.val) * 2.5;

              // 2. วาดวงกลมสีๆ (ตัว Node)
              ctx.beginPath();
              ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI, false);
              ctx.fillStyle = getColor(node.group);
              ctx.fill();

              // 3. วาดตัวหนังสือ "เฉพาะตอนที่ซูมเข้าใกล้ๆ เท่านั้น" (เช่น Scale > 1.8)
              if (globalScale > 1.8) {
                // ปรับขนาดฟอนต์ให้สัมพันธ์กับการซูม จะได้ไม่ใหญ่ทะลุจอ
                const fontSize = 12 / globalScale;
                ctx.font = `${fontSize}px Inter, Sans-Serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                ctx.fillStyle = "#475569"; // สีเทาเข้มให้อ่านง่าย

                // วาดชื่อนักวิจัยให้อยู่ "ใต้" วงกลมพอดี
                ctx.fillText(
                  node.name,
                  node.x,
                  node.y + nodeRadius + 2 / globalScale,
                );
              }
            }}
            // ตั้งค่าเส้นเหมือนเดิม
            linkWidth={(link: any) => Math.sqrt(link.weight) * 1.5}
            linkColor={() => "rgba(148, 163, 184, 0.4)"}
            d3VelocityDecay={0.3}
            onEngineStop={() => fgRef.current?.zoomToFit(400, 50)}
            cooldownTicks={100}
          />
        )}
      </div>
    </div>
  );
}
