import { useState, useEffect, useMemo } from "react";
import { FileText, Users, Layers, CheckSquare, Square } from "lucide-react";
import { Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Brush,
  PieChart,
  Pie,
} from "recharts";
import api from "../services/api";
import type { DashboardSummary } from "../types/models";

export default function DashboardOverview() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // State For Topic
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
  const [topAuthors, setTopAuthors] = useState<any[]>([]);
  const [topicMap, setTopicMap] = useState<Record<string, string>>({});
  const processedTrends = useMemo(() => {
    if (trends.length === 0) return [];

    // Find all topics available in the system.
    const allTopics = new Set<string>();
    trends.forEach((yearData) => {
      Object.keys(yearData).forEach((key) => {
        if (key !== "year") allTopics.add(key);
      });
    });

    // Create a new array and add 0 to it.
    return trends.map((yearData) => {
      const filledData = { ...yearData };
      allTopics.forEach((topic) => {
        if (filledData[topic] === undefined) {
          filledData[topic] = 0; // Add 0 to the years in which this topic was not published.
        }
      });
      return filledData;
    });
  }, [trends]);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [summaryRes, trendsRes, topAuthorsRes, topicsRes] =
          await Promise.all([
            api.get("/analytics/summary/"),
            api.get("/analytics/domain-trends/"),
            api.get("/analytics/top-authors/"),
            api.get("/analytics/topics/"),
          ]);
        setSummary(summaryRes.data);
        setTrends(trendsRes.data);
        setTopAuthors(topAuthorsRes.data);

        const map: Record<string, string> = {};
        if (Array.isArray(topicsRes.data)) {
          topicsRes.data.forEach((topicStr: string) => {
            const match = topicStr.match(/(-?\d+)\s*:\s*(.+)/);
            if (match) {
              const topicId = match[1];
              const topicName = match[2].trim();
              map[topicId] = topicName;
            }
          });
        }
        setTopicMap(map);
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

  const overallTopicDistribution = useMemo(() => {
    if (trends.length === 0 || domainInfo.length === 0) return [];

    const totals: Record<string, number> = {};

    // Loop by adding the numbers from every year together.
    trends.forEach((yearData) => {
      Object.keys(yearData).forEach((key) => {
        if (key !== "year") {
          totals[key] = (totals[key] || 0) + (yearData[key] as number);
        }
      });
    });

    // Convert the object to an array and match the colors to the line chart exactly.
    return Object.entries(totals)
      .map(([key, value]) => {
        const dInfo = domainInfo.find((d) => d.fullKey === key);
        const index = domainInfo.findIndex((d) => d.fullKey === key);
        return {
          name:
            dInfo && dInfo.names ? dInfo.names : dInfo ? dInfo.shortName : key,
          value,
          fill: getDynamicColor(index > -1 ? index : 0), // Use the exact same color as the graph line
        };
      })
      .filter((item) => item.value > 0) // Take only the valuable ones.
      .sort((a, b) => b.value - a.value); // Sorted from highest to lowest.
  }, [trends, domainInfo]);

  useEffect(() => {
    if (domainInfo.length > 0 && selectedDomains.length === 0) {
      setSelectedDomains(domainInfo.slice(0, 5).map((d) => d.fullKey));
    }
  }, [domainInfo]);

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
          <div className="p-4 bg-red-50 text-red-600 rounded-lg">
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
          <div className="p-4 bg-yellow-50 text-yellow-600 rounded-lg">
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

      {/* Graph and Controller */}
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
                  <RechartsTooltip
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
                        ? processedTrends.length - 21
                        : 0
                    } // default Zoom
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
                    ${isSelected ? "bg-yellow-50 border-yellow-200" : "bg-white border-slate-100 hover:border-slate-300 opacity-60 hover:opacity-100"}`}
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
      {/* Doughnut Chart & Top Authors Placeholder */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Doughnut Chart*/}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col">
          <h2 className="text-lg font-bold text-slate-800 mb-1">
            Overall Distribution
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            All-time publications by domain
          </p>

          <div className="flex-1 min-h-[250px] w-full relative">
            {overallTopicDistribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={overallTopicDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={70}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                    stroke="none"
                  />

                  <RechartsTooltip
                    formatter={(value: any, name: any) => [
                      `${value} Papers`,
                      name,
                    ]}
                    contentStyle={{
                      borderRadius: "8px",
                      border: "none",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="absolute inset-0 flex items-center justify-center text-slate-400">
                No data available
              </div>
            )}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-2xl font-bold text-slate-700">
                {overallTopicDistribution.length}
              </span>
              <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Topics
              </span>
            </div>
          </div>
        </div>

        {/* Top Authors Leaderboard */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-lg font-bold text-slate-800">
                Top Researchers
              </h2>
              <p className="text-xs text-slate-500">
                Authors with the highest number of publications
              </p>
            </div>
            <span className="text-sm text-red-600 hover:text-red-800 font-medium cursor-pointer">
              View All
            </span>
          </div>

          <div className="flex-1 flex flex-col gap-3 justify-center">
            {topAuthors.map((author, index) => {
              const cleanId = String(author.primary_cluster).trim();
              const topicName =
                topicMap[cleanId] || `Topic ${author.primary_cluster}`;

              return (
                <Link
                  key={author.id}
                  to={`/authors/${author.id}`}
                  className="flex items-center p-3 rounded-lg border border-slate-100 hover:bg-red-50 hover:border-red-200 transition-all group"
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm mr-4 shrink-0
                    ${
                      index === 0
                        ? "bg-amber-100 text-amber-600"
                        : index === 1
                          ? "bg-slate-200 text-slate-600"
                          : index === 2
                            ? "bg-orange-100 text-orange-600"
                            : "bg-slate-100 text-slate-400"
                    }`}
                  >
                    #{index + 1}
                  </div>

                  <div className="flex-1 min-w-0 pr-4">
                    <h3 className="font-bold text-slate-800 group-hover:text-red-600 transition-colors truncate">
                      {author.name}
                    </h3>
                    <p className="text-xs text-slate-500 truncate">
                      {author.faculty || "External Researcher"}
                    </p>
                  </div>

                  {/* Statistics and Expertise Labels */}
                  <div className="flex items-center gap-3 shrink-0">
                    {/* Make sure the value is not null or undefined before showing the label. */}
                    {author.primary_cluster !== null &&
                      author.primary_cluster !== undefined && (
                        <span
                          className="hidden sm:inline-block bg-yellow-50 text-yellow-700 border border-yellow-100 px-2.5 py-1 rounded text-[11px] font-semibold max-w-[150px] truncate"
                          title={topicName} // Add a title in case the name is too long and gets hidden, so you can hover your mouse over it to see the full name.
                        >
                          {topicName}
                        </span>
                      )}
                    <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg text-sm font-bold text-slate-700">
                      <FileText size={14} className="text-slate-400" />
                      {author.works_count}
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
