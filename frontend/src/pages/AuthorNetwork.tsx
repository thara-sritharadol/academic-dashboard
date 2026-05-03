import { useState, useEffect } from "react";
import api from "../services/api";
import { Users } from "lucide-react";
import NetworkTopicFilter from "../components/NetworkTopicFilter";
import NetworkLegend from "../components/NetworkLegend";
import AuthorForceGraph from "../components/AuthorForceGraph";

interface TopicResponse {
  topic_id: number;
  name: string;
  keywords: string[];
}

export default function AuthorNetwork() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);

  const [availableDomains, setAvailableDomains] = useState<TopicResponse[]>([]);
  const [isReady, setIsReady] = useState(false);

  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
  const [pendingDomains, setPendingDomains] = useState<string[]>([]);
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  useEffect(() => {
    api.get("/analytics/topics/").then((res) => {
      const domains = res.data;
      setAvailableDomains(domains);

      if (domains.length > 0) {
        const initialDomains = domains
          .slice(0, 3)
          .map((d: TopicResponse) => d.name);
        setSelectedDomains(initialDomains);
        setPendingDomains(initialDomains);
      }
      setIsReady(true);
    });
  }, []);

  useEffect(() => {
    if (!isReady) return;

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

  const COLOR_TU = "#FFD13F";
  const COLOR_EXTERNAL = "#d1d5db";

  const toggleDomain = (domainName: string) => {
    setPendingDomains((prev) =>
      prev.includes(domainName)
        ? prev.filter((d) => d !== domainName)
        : [...prev, domainName],
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

      <div className="flex-1 m-8 mt-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
        {!loading && graphData.nodes.length > 0 && <NetworkLegend />}
        <AuthorForceGraph graphData={graphData} loading={loading} />
      </div>
    </div>
  );
}
