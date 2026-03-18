import { useState, useEffect } from "react";
import { Search, Filter, BookOpen, ExternalLink } from "lucide-react";
import api from "../services/api";
import type { Paper } from "../types/models";

export default function PaperSearch() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);

  // State For Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDomain, setSelectedDomain] = useState("");

  const [availableDomains, setAvailableDomains] = useState<string[]>([]);

  // Fetch From API
  const fetchPapers = async () => {
    setLoading(true);
    try {
      const response = await api.get("/papers/", {
        params: {
          q: searchQuery || undefined,
          domain: selectedDomain || undefined,
        },
      });
      setPapers(response.data);
    } catch (error) {
      console.error("Error fetching papers:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const fetchInitialData = async () => {
      setLoading(true);
      try {
        // ยิง API ดึงทั้งรายชื่อเปเปอร์และรายชื่อโดเมนพร้อมกัน
        const [papersRes, topicsRes] = await Promise.all([
          api.get("/papers/"),
          api.get("/analytics/topics/"),
        ]);
        setPapers(papersRes.data);
        setAvailableDomains(topicsRes.data); // เก็บรายชื่อ Domain ลง State
      } catch (error) {
        console.error("Error fetching initial data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The data is retrieved for the first time when the webpage is loaded.
  useEffect(() => {
    fetchPapers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // The function is managed when you press Enter in the search box.
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      fetchPapers();
    }
  };

  return (
    <div className="p-8 h-screen flex flex-col">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Paper Repository</h1>
        <p className="text-slate-500">
          Search and explore research papers across all discovered domains.
        </p>
      </div>

      {/* Search Bar & Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 mb-6 shrink-0">
        {/* Search */}
        <div className="flex-1 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search size={18} className="text-slate-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            placeholder="Search by title or abstract... (Press Enter to search)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>

        {/* Filter Domain */}
        <div className="w-full md:w-64 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Filter size={18} className="text-slate-400" />
          </div>
          <select
            className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg appearance-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            value={selectedDomain}
            onChange={(e) => {
              setSelectedDomain(e.target.value);
              // When changing the dropdown menu, immediately make a new API call without waiting for Enter.
              setTimeout(fetchPapers, 100);
            }}
          >
            <option value="">All Domains</option>
            {availableDomains.map((domainStr) => {
              // ดึงแค่ชื่อ Topic สั้นๆ มาโชว์ใน Dropdown เช่น "Topic 0" หรือถ้าอยากโชว์เต็มๆ ก็ใช้ domainStr ได้เลย
              const shortName = domainStr.split(":")[0];
              return (
                <option key={domainStr} value={domainStr}>
                  {shortName}
                </option>
              );
            })}
            {/* Domain Option */}
          </select>
        </div>

        <button
          onClick={fetchPapers}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
        >
          Search
        </button>
      </div>

      {/* Table display area */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex-1 overflow-hidden flex flex-col">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="animate-pulse flex flex-col items-center gap-2">
              <BookOpen size={32} className="text-slate-300" />
              <p>Searching database...</p>
            </div>
          </div>
        ) : papers.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            No papers found matching your criteria.
          </div>
        ) : (
          <div className="overflow-x-auto flex-1 custom-scrollbar">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50 sticky top-0 z-10">
                <tr>
                  <th
                    scope="col"
                    className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider w-2/5"
                  >
                    Paper Title
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider w-1/5"
                  >
                    Authors
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-4 text-center text-xs font-semibold text-slate-600 uppercase tracking-wider"
                  >
                    Year
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider"
                  >
                    Discovered Domains
                  </th>
                  <th
                    scope="col"
                    className="px-6 py-4 text-right text-xs font-semibold text-slate-600 uppercase tracking-wider"
                  >
                    Citations
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-100">
                {papers.map((paper) => (
                  <tr
                    key={paper.id}
                    className="hover:bg-slate-50 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <div className="text-sm font-semibold text-slate-900 line-clamp-2">
                        {paper.title}
                      </div>
                      {/* In the future, create a button that allows you to click to the Details page. */}
                      <div className="text-xs text-blue-600 mt-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer flex items-center gap-1">
                        View details <ExternalLink size={12} />
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-slate-600 line-clamp-2">
                        {paper.authors_list?.join(", ") || "Unknown Author"}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center whitespace-nowrap">
                      <div className="text-sm text-slate-700">
                        {paper.year || "-"}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1.5">
                        {paper.predicted_multi_labels?.map((label, idx) => {
                          // The badge colors are slightly randomized according to the label name.
                          const isCS = label.toLowerCase().includes("computer");
                          const colorClass = isCS
                            ? "bg-blue-100 text-blue-700 border-blue-200"
                            : "bg-emerald-100 text-emerald-700 border-emerald-200";

                          return (
                            <span
                              key={idx}
                              className={`px-2.5 py-1 inline-flex text-[11px] leading-4 font-semibold rounded-full border ${colorClass}`}
                            >
                              {label.split(":")[0]} {/* Topic */}
                            </span>
                          );
                        })}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right whitespace-nowrap">
                      <div className="text-sm font-medium text-slate-700">
                        {paper.citation_count}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
