import { useState, useEffect } from "react";
import {
  Search,
  Filter,
  BookOpen,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"; //
import api from "../services/api";
import type { Paper } from "../types/models";
import { Link } from "react-router-dom";

export default function PaperSearch() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);

  // State For Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDomain, setSelectedDomain] = useState("");
  const [availableDomains, setAvailableDomains] = useState<string[]>([]);

  // State For Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 20; //

  // Fetch From API
  const fetchPapers = async (
    overrideDomain?: string,
    pageNumber: number = 1,
  ) => {
    setLoading(true);

    const activeDomain =
      overrideDomain !== undefined ? overrideDomain : selectedDomain;

    try {
      const response = await api.get("/papers/", {
        params: {
          q: searchQuery || undefined,
          domain: activeDomain || undefined,
          page: pageNumber,
        },
      });

      if (response.data && response.data.results) {
        setPapers(response.data.results);
        setTotalCount(response.data.count);
        setTotalPages(Math.ceil(response.data.count / pageSize));
      } else {
        setPapers(response.data);
        setTotalCount(response.data.length);
        setTotalPages(1);
      }
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
        const topicsRes = await api.get("/analytics/topics/");
        setAvailableDomains(topicsRes.data);
        await fetchPapers();
      } catch (error) {
        console.error("Error fetching initial data:", error);
        setLoading(false);
      }
    };

    fetchInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setCurrentPage(1); //
      fetchPapers(selectedDomain, 1);
    }
  };

  // ฟังก์ชันสำหรับเปลี่ยนหน้า
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      fetchPapers(selectedDomain, newPage);
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

        <div className="w-full md:w-64 relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Filter size={18} className="text-slate-400" />
          </div>
          <select
            className="block w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg appearance-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
            value={selectedDomain}
            onChange={(e) => {
              const newValue = e.target.value;
              setSelectedDomain(newValue);
              setCurrentPage(1);
              fetchPapers(newValue, 1);
            }}
          >
            <option value="">All Domains</option>
            {availableDomains.map((domainStr) => {
              const shortName = domainStr.split(":")[1];
              return (
                <option key={domainStr} value={domainStr}>
                  {shortName}
                </option>
              );
            })}
          </select>
        </div>
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
          <>
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
                        <Link
                          to={`/papers/${paper.id}`}
                          className="text-xs text-blue-600 mt-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer flex items-center gap-1"
                        >
                          View details <ExternalLink size={12} />
                        </Link>
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
                            const isCS = label
                              .toLowerCase()
                              .includes("computer");
                            const colorClass = isCS
                              ? "bg-blue-100 text-blue-700 border-blue-200"
                              : "bg-emerald-100 text-emerald-700 border-emerald-200";
                            return (
                              <span
                                key={idx}
                                className={`px-2.5 py-1 inline-flex text-[11px] leading-4 font-semibold rounded-full border ${colorClass}`}
                              >
                                {label.split(":")[1]}
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

            {/* Pagination Controls */}
            <div className="bg-white px-6 py-4 border-t border-slate-200 flex items-center justify-between shrink-0">
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-slate-700">
                    Showing{" "}
                    <span className="font-semibold">
                      {(currentPage - 1) * pageSize + 1}
                    </span>{" "}
                    to{" "}
                    <span className="font-semibold">
                      {Math.min(currentPage * pageSize, totalCount)}
                    </span>{" "}
                    of <span className="font-semibold">{totalCount}</span>{" "}
                    results
                  </p>
                </div>
                <div>
                  <nav
                    className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
                    aria-label="Pagination"
                  >
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-slate-300 bg-white text-sm font-medium ${currentPage === 1 ? "text-slate-300 cursor-not-allowed" : "text-slate-500 hover:bg-slate-50"}`}
                    >
                      <span className="sr-only">Previous</span>
                      <ChevronLeft size={18} aria-hidden="true" />
                    </button>

                    <span className="relative inline-flex items-center px-4 py-2 border border-slate-300 bg-white text-sm font-medium text-slate-700">
                      Page {currentPage} of {totalPages}
                    </span>

                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-slate-300 bg-white text-sm font-medium ${currentPage === totalPages ? "text-slate-300 cursor-not-allowed" : "text-slate-500 hover:bg-slate-50"}`}
                    >
                      <span className="sr-only">Next</span>
                      <ChevronRight size={18} aria-hidden="true" />
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
