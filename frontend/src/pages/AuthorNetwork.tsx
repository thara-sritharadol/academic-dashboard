import { useState, useEffect, useRef } from "react";
import ForceGraph2D from "react-force-graph-2d";
import api from "../services/api";
import { useNavigate } from "react-router-dom"; // <-- เพิ่ม import นี้
import {
  Users,
  ZoomIn,
  ZoomOut,
  Maximize,
  Filter,
  Check,
  X,
} from "lucide-react";

export default function AuthorNetwork() {
  const navigate = useNavigate(); // <-- สร้าง instance สำหรับใช้เปลี่ยนหน้า
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [availableDomains, setAvailableDomains] = useState<string[]>([]);
  const [isReady, setIsReady] = useState(false); // <-- เพิ่ม State เพื่อเช็คว่าโหลด Topic เสร็จหรือยัง

  // Multi-select Checkbox
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
  const [pendingDomains, setPendingDomains] = useState<string[]>([]);
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  const fgRef = useRef<any>(null);

  // โหลด Topic ทั้งหมด และตั้งค่า 3 อันดับแรกเป็นค่าเริ่มต้น
  useEffect(() => {
    api.get("/analytics/topics/").then((res) => {
      const domains = res.data;
      setAvailableDomains(domains);

      if (domains.length > 0) {
        // เลือก 3 Topic แรกเป็นค่าเริ่มต้น (ปรับตัวเลขได้ตามต้องการ)
        const initialDomains = domains.slice(0, 3);
        setSelectedDomains(initialDomains);
        setPendingDomains(initialDomains);
      }
      setIsReady(true); // อนุญาตให้ดึงกราฟได้
    });
  }, []);

  // ดึงข้อมูลกราฟ (จะทำงานก็ต่อเมื่อ isReady = true แล้วเท่านั้น)
  useEffect(() => {
    if (!isReady) return; // กั้นไม่ให้โหลดกราฟจนกว่า Topic จะเซ็ตค่าเริ่มต้นเสร็จ

    const fetchNetwork = async () => {
      setLoading(true);
      try {
        const res = await api.get("/network/authors/", {
          params: {
            limit: 200,
            domains:
              selectedDomains.length > 0
                ? selectedDomains.join(",")
                : undefined,
          },
        });
        setGraphData(res.data);
      } catch (error) {
        console.error("Error fetching network data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchNetwork();
  }, [selectedDomains, isReady]);

  useEffect(() => {
    if (!loading && fgRef.current && graphData.nodes.length > 0) {
      fgRef.current.d3Force("charge")?.strength(-100);
      fgRef.current.d3Force("link")?.distance(80);
    }
  }, [graphData, loading]);

  const COLOR_TU = "#FFD13F";
  const COLOR_EXTERNAL = "#d1d5db";
  const COLOR_TEXT = "#1f2937";

  const toggleDomain = (domain: string) => {
    setPendingDomains((prev) =>
      prev.includes(domain)
        ? prev.filter((d) => d !== domain)
        : [...prev, domain],
    );
  };

  const applyFilter = () => {
    setSelectedDomains(pendingDomains);
    setIsFilterOpen(false);
  };

  const clearFilter = () => {
    setPendingDomains([]);
    setSelectedDomains([]);
    setIsFilterOpen(false);
  };

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <div className="p-8 pb-4 shrink-0 flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
            <Users className="text-red-600" /> TU Collaboration Network
          </h1>
          <p className="text-slate-500">
            Node size: paper count. Line thickness: collaboration frequency.
            <span className="ml-2 inline-flex items-center gap-1.5 font-medium">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: COLOR_TU }}
              ></span>{" "}
              TU Author
              <span
                className="w-3 h-3 rounded-full ml-1"
                style={{ backgroundColor: COLOR_EXTERNAL }}
              ></span>{" "}
              External Co-author
            </span>
          </p>
        </div>

        {/* Multi-select Filter */}
        <div className="relative z-20">
          <button
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg shadow-sm hover:bg-slate-50 text-slate-700 font-medium transition-colors"
          >
            <Filter
              size={18}
              className={
                selectedDomains.length > 0 ? "text-red-600" : "text-red-400"
              }
            />
            Filter Topics{" "}
            {selectedDomains.length > 0 && (
              <span className="bg-red-100 text-red-700 py-0.5 px-2 rounded-full text-xs">
                {selectedDomains.length}
              </span>
            )}
          </button>

          {isFilterOpen && (
            <div className="absolute right-0 mt-2 w-96 bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden flex flex-col">
              <div className="p-3 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <span className="font-semibold text-slate-700 text-sm">
                  Select Topics
                </span>
                <button
                  onClick={() => setIsFilterOpen(false)}
                  className="text-slate-400 hover:text-slate-600"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="max-h-64 overflow-y-auto p-2">
                {availableDomains.length === 0 ? (
                  <p className="p-2 text-sm text-slate-500 text-center">
                    No topics available.
                  </p>
                ) : (
                  availableDomains.map((domainStr) => {
                    // ป้องกัน Error กรณี format string ไม่ตรง
                    const parts = domainStr.split(":");
                    const shortName = parts[0] ? parts[0].trim() : domainStr;
                    const fullName =
                      parts.length > 1
                        ? parts.slice(1).join(":").trim()
                        : domainStr;
                    const isChecked = pendingDomains.includes(domainStr);

                    return (
                      <div
                        key={domainStr}
                        onClick={() => toggleDomain(domainStr)}
                        className="flex items-start gap-3 p-2 hover:bg-slate-50 rounded-lg cursor-pointer transition-colors group"
                      >
                        <div
                          className={`mt-0.5 w-4 h-4 rounded flex items-center justify-center border ${isChecked ? "bg-yellow-600 border-yellow-600" : "border-slate-300 group-hover:border-blue-400"}`}
                        >
                          {isChecked && (
                            <Check size={12} className="text-white" />
                          )}
                        </div>
                        <div className="flex-1 text-sm pointer-events-none">
                          <span className="font-medium text-slate-700 block">
                            {shortName}
                          </span>
                          <span
                            className="text-xs text-slate-400 line-clamp-1"
                            title={fullName}
                          >
                            {fullName}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              <div className="p-3 border-t border-slate-100 bg-slate-50 flex gap-2">
                <button
                  onClick={clearFilter}
                  className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded-md transition-colors"
                >
                  Clear All
                </button>
                <button
                  onClick={applyFilter}
                  className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md shadow-sm transition-colors"
                >
                  Apply Filter
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 m-8 mt-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
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

        {!loading && graphData.nodes.length > 0 && (
          <div className="absolute bottom-4 right-4 z-10 bg-white/95 p-4 rounded-xl border border-slate-200 shadow-lg w-56">
            <h3 className="text-sm font-bold text-slate-700 mb-3 uppercase tracking-wider">
              Institution
            </h3>
            <div className="space-y-2.5">
              <div className="flex items-center gap-2.5 text-sm">
                <span
                  className="w-4 h-4 rounded-full shrink-0 shadow-sm"
                  style={{ backgroundColor: COLOR_TU }}
                ></span>
                <span className="font-semibold text-slate-800">
                  Thammasat Univ.
                </span>
              </div>
              <div className="flex items-center gap-2.5 text-sm">
                <span
                  className="w-4 h-4 rounded-full shrink-0 shadow-sm"
                  style={{ backgroundColor: COLOR_EXTERNAL }}
                ></span>
                <span className="text-slate-600">External Network</span>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="w-full h-full flex items-center justify-center text-slate-400 bg-slate-50/50">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-3"></div>
              Generating network physics...
            </div>
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 bg-slate-50/50">
            <Filter size={48} className="text-slate-300 mb-4" />
            <p className="text-lg font-medium text-slate-600">
              No network data available
            </p>
            <p className="text-sm mt-1 text-slate-400">
              Try selecting different topics from the filter above.
            </p>
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
            nodeLabel="name"
            // 🔥 เพิ่มการตั้งค่าคลิกแล้วให้ไปยังหน้า AuthorDetail.tsx
            onNodeClick={(node: any) => {
              navigate(`/authors/${node.id}`);
            }}
            // 🔥 เมื่อนำเมาส์ไปชี้ที่ Node ให้เปลี่ยน Cursor เป็นแบบ Pointer ให้ดูน่ากด
            onNodeHover={(node: any) => {
              const canvas = fgRef.current?.canvas;
              if (canvas) {
                canvas.style.cursor = node ? "pointer" : "default";
              }
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
                ctx.fillText(
                  label,
                  node.x,
                  node.y + nodeRadius + 3 / globalScale,
                );
              }
            }}
            linkColor={(link: any) => {
              const source =
                typeof link.source === "object" ? link.source : null;
              const target =
                typeof link.target === "object" ? link.target : null;
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
        )}
      </div>
    </div>
  );
}
