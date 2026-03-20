import { useState, useEffect, useMemo } from "react";
import { FileText, Users, Layers, CheckSquare, Square } from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Brush,
} from "recharts";
import api from "../services/api";
import type { DashboardSummary } from "../types/models";

export default function DashboardOverview() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // State For Topic
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);

  const processedTrends = useMemo(() => {
    if (trends.length === 0) return [];

    // หา Topic ทั้งหมดที่มีในระบบ
    const allTopics = new Set<string>();
    trends.forEach((yearData) => {
      Object.keys(yearData).forEach((key) => {
        if (key !== "year") allTopics.add(key);
      });
    });

    // สร้าง Array ใหม่ที่เติม 0 เข้าไป
    return trends.map((yearData) => {
      const filledData = { ...yearData };
      allTopics.forEach((topic) => {
        if (filledData[topic] === undefined) {
          filledData[topic] = 0; // เติม 0 ให้ปีที่ไม่มีการตีพิมพ์หัวข้อนี้
        }
      });
      return filledData;
    });
  }, [trends]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [summaryRes, trendsRes] = await Promise.all([
          api.get("/analytics/summary/"),
          api.get("/analytics/domain-trends/"),
        ]);
        setSummary(summaryRes.data);
        setTrends(trendsRes.data);
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  // useMemo To prevent it from recalculating every time a filter is selected.
  const domainInfo = useMemo(() => {
    if (trends.length === 0) return [];

    const allKeys = Array.from(
      new Set(trends.flatMap(Object.keys).filter((key) => key !== "year")),
    );

    return allKeys.map((key) => {
      // Separate the Topic name from the name (if there are :) symbols).
      const parts = key.split(":");
      const shortName = parts[0].trim();
      const name = parts.length > 1 ? parts.slice(1).join(":").trim() : "";
      return { fullKey: key, shortName, names: name };
    });
  }, [trends]);

  const getDynamicColor = (index: number) => {
    const hue = (index * 137.508) % 360;
    return `hsl(${hue}, 70%, 50%)`;
  };

  useEffect(() => {
    if (domainInfo.length > 0 && selectedDomains.length === 0) {
      setSelectedDomains(domainInfo.slice(0, 5).map((d) => d.fullKey));
    }
  }, [domainInfo]);

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
    "#06b6d4",
    "#d946ef",
    "#eab308",
    "#22c55e",
    "#a855f7",
    "#fb923c",
    "#0ea5e9",
    "#f43f5e",
    "#64748b",
    "#334155",
  ];

  const toggleDomain = (domainKey: string) => {
    setSelectedDomains((prev) =>
      prev.includes(domainKey)
        ? prev.filter((d) => d !== domainKey)
        : [...prev, domainKey],
    );
  };

  if (loading) {
    return <div className="p-8 text-slate-500">Loading dashboard data...</div>;
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">System Overview</h1>

      {/* Hero Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-4 bg-blue-50 text-blue-600 rounded-lg">
            <FileText size={24} />
          </div>
          <div>
            <p className="text-sm text-slate-500 font-medium">Total Papers</p>
            <p className="text-3xl font-bold">
              {summary?.total_papers.toLocaleString()}
            </p>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-4 bg-emerald-50 text-emerald-600 rounded-lg">
            <Users size={24} />
          </div>
          <div>
            <p className="text-sm text-slate-500 font-medium">Total Authors</p>
            <p className="text-3xl font-bold">
              {summary?.total_authors.toLocaleString()}
            </p>
          </div>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
          <div className="p-4 bg-amber-50 text-amber-600 rounded-lg">
            <Layers size={24} />
          </div>
          <div>
            <p className="text-sm text-slate-500 font-medium">
              Discovered Topics
            </p>
            <p className="text-3xl font-bold">
              {summary?.total_clusters.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Graph and Comtroller */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Line */}
        <div className="lg:col-span-3 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="text-lg font-bold mb-6">
            Domain Publications Over Time
          </h2>
          <div className="h-[450px] w-full">
            {trends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={processedTrends}
                  margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="#e2e8f0"
                  />
                  <XAxis
                    dataKey="year"
                    tick={{ fill: "#64748b" }}
                    tickMargin={10}
                  />
                  <YAxis tick={{ fill: "#64748b" }} tickMargin={10} />
                  <Tooltip
                    contentStyle={{
                      borderRadius: "8px",
                      border: "none",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    }}
                  />
                  <Legend wrapperStyle={{ paddingTop: "20px" }} />

                  {/* Draw lines only on the selected Topics in selectedDomains. */}
                  {domainInfo
                    .filter((d) => selectedDomains.includes(d.fullKey))
                    .map((domain, index) => {
                      // Find the color index that matches the initial color, so that the color doesn't change when switching filters.
                      const colorIndex = domainInfo.findIndex(
                        (d) => d.fullKey === domain.fullKey,
                      );

                      const lineColor = getDynamicColor(colorIndex);

                      return (
                        <Line
                          key={domain.fullKey}
                          name={domain.shortName}
                          dataKey={domain.fullKey}
                          type="monotone"
                          stroke={lineColor}
                          strokeWidth={3}
                          dot={{ r: 4, strokeWidth: 2 }}
                          activeDot={{ r: 6 }}
                        />
                      );
                    })}
                  <Brush
                    dataKey="year"
                    height={30}
                    stroke="#94a3b8"
                    fill="#f8fafc"
                    startIndex={
                      processedTrends.length > 10
                        ? processedTrends.length - 11
                        : 0
                    } // ให้ default ซูมดูแค่ 20 ปีล่าสุด
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400">
                No trend data available
              </div>
            )}
          </div>
        </div>

        {/* Filter & Dictionary */}
        <div className="lg:col-span-1 bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col h-[530px]">
          <h2 className="text-sm font-bold text-slate-700 mb-3 px-2 uppercase tracking-wider">
            Filter Topics ({selectedDomains.length}/{domainInfo.length})
          </h2>
          <div className="flex-1 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
            {domainInfo.map((domain, index) => {
              const isSelected = selectedDomains.includes(domain.fullKey);

              const dotColor = getDynamicColor(index);

              //const dotColor = colors[index % colors.length];

              return (
                <div
                  key={domain.fullKey}
                  onClick={() => toggleDomain(domain.fullKey)}
                  className={`p-3 rounded-lg border cursor-pointer transition-all flex items-start gap-3
                    ${isSelected ? "bg-slate-50 border-blue-200" : "bg-white border-slate-100 hover:border-slate-300 opacity-60 hover:opacity-100"}`}
                >
                  <div
                    className="mt-0.5"
                    style={{ color: isSelected ? dotColor : "#cbd5e1" }}
                  >
                    {isSelected ? (
                      <CheckSquare size={18} />
                    ) : (
                      <Square size={18} />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-sm text-slate-800 flex items-center gap-2">
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: dotColor }}
                      ></span>
                      {domain.shortName}
                    </div>
                    {domain.names && (
                      <div className="text-xs text-slate-500 mt-1 line-clamp-2 leading-tight">
                        {domain.names}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-3 mt-2 border-t border-slate-100 flex gap-2">
            <button
              onClick={() =>
                setSelectedDomains(domainInfo.map((d) => d.fullKey))
              }
              className="flex-1 text-xs py-1.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-700 font-medium transition"
            >
              Select All
            </button>
            <button
              onClick={() => setSelectedDomains([])}
              className="flex-1 text-xs py-1.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-700 font-medium transition"
            >
              Clear All
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
