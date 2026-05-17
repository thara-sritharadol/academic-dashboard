import { useState, useEffect, useMemo } from "react";
import { FileText, Users, Layers } from "lucide-react";
import api from "../services/api";
import type { DashboardSummary, DomainInfo } from "../types/models";
import StatCard from "../components/StatCard";
import TrendChart from "../components/TrendChart";
import TopicFilter from "../components/TopicFilter";
import TopResearchersList from "../components/TopResearchersList";

interface TopicDetail {
  name: string;
  keywords: string[];
}

interface TopicResponse {
  topic_id: number;
  name: string;
  keywords: string[];
}

export default function DashboardOverview() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // State For Topic
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
  const [topAuthors, setTopAuthors] = useState<any[]>([]);
  const [topicMap, setTopicMap] = useState<Record<number, TopicDetail>>({});
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

        const map: Record<number, TopicDetail> = {};
        if (Array.isArray(topicsRes.data)) {
          topicsRes.data.forEach((topic: TopicResponse) => {
            if (topic && topic.topic_id !== undefined) {
              map[topic.topic_id] = {
                name: topic.name,
                keywords: topic.keywords || [],
              };
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
  const domainInfo = useMemo<DomainInfo[]>(() => {
    if (trends.length === 0) return [];

    const allKeys = Array.from(
      new Set(trends.flatMap(Object.keys).filter((key) => key !== "year")),
    );

    const topicNameMap = new Map<string, string[]>();
    Object.values(topicMap).forEach((topic) => {
      topicNameMap.set(topic.name.trim(), topic.keywords);
    });

    return allKeys.map((key) => {
      const keywords = topicNameMap.get(key.trim()) || [];

      return {
        fullKey: key,
        name: key,
        keywords: keywords,
      };
    });
  }, [trends, topicMap]);

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
      <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

      {/* Hero Stats - Refactored Version */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard
          title="Total Articles"
          value={summary?.total_papers}
          icon={<FileText size={24} />}
          variant="red"
        />
        <StatCard
          title="Total Researcher"
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
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-6">
        <TopResearchersList authors={topAuthors} topicMap={topicMap} />
      </div>
    </div>
  );
}
