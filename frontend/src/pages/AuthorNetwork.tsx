import { useState, useEffect, useRef } from "react";
import api from "../services/api";
import { Users } from "lucide-react";
import NetworkTopicFilter from "../components/NetworkTopicFilter";
import NetworkLegend from "../components/NetworkLegend";
import AuthorForceGraph from "../components/AuthorForceGraph";

export default function AuthorNetwork() {
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
        <NetworkTopicFilter
          availableDomains={availableDomains}
          selectedDomains={selectedDomains}
          pendingDomains={pendingDomains}
          isFilterOpen={isFilterOpen}
          setIsFilterOpen={setIsFilterOpen}
          toggleDomain={toggleDomain}
          applyFilter={applyFilter}
          clearFilter={clearFilter}
        />
      </div>

      {/* GRAPH SECTION */}
      <div className="flex-1 m-8 mt-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
        {/* COMPONENT: Legend */}
        {!loading && graphData.nodes.length > 0 && <NetworkLegend />}

        {/* COMPONENT: Force Graph */}
        <AuthorForceGraph graphData={graphData} loading={loading} />
      </div>
    </div>
  );
}
