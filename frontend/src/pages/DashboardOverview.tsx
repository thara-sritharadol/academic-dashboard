import { useState, useEffect, useMemo } from "react";
import { FileText, Users, Layers } from "lucide-react";
import api from "../services/api";
import type { DashboardSummary } from "../types/models";
import StatCard from "../components/StatCard";
import TrendChart from "../components/TrendChart";
import TopicFilter from "../components/TopicFilter";
import DistributionChart from "../components/DistributionChart";
import TopResearchersList from "../components/TopResearchersList";

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

      {/* Hero Stats - Refactored Version */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Total Papers"
          value={summary?.total_papers}
          icon={<FileText size={24} />}
          variant="red"
        />
        <StatCard
          title="Total Authors"
          value={summary?.total_authors}
          icon={<Users size={24} />}
          variant="emerald"
        />
        <StatCard
          title="Discovered Topics"
          value={summary?.total_clusters}
          icon={<Layers size={24} />}
          variant="yellow"
        />
      </div>

      {/* Graph and Controller */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <TrendChart
          data={processedTrends}
          domainInfo={domainInfo}
          selectedDomains={selectedDomains}
        />

        <TopicFilter
          domainInfo={domainInfo}
          selectedDomains={selectedDomains}
          onToggle={toggleDomain}
          onSelectAll={() =>
            setSelectedDomains(domainInfo.map((d) => d.fullKey))
          }
          onClearAll={() => setSelectedDomains([])}
        />
      </div>

      {/* Bottom Section: Bar Chart & Top Authors */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <DistributionChart data={overallTopicDistribution} />
        <TopResearchersList authors={topAuthors} topicMap={topicMap} />
      </div>
    </div>
  );
}
