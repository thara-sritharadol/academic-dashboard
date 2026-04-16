import { useState, useEffect, useRef } from "react";
import { Search, Filter } from "lucide-react"; //
import api from "../services/api";
import type { Paper } from "../types/models";
import PaginationControls from "../components/PaginationControls";
import PaperTable from "../components/PaperTable";

export default function PaperSearch() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);

  // State For Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedDomain, setSelectedDomain] = useState("");
  const [availableDomains, setAvailableDomains] = useState<string[]>([]);

  // State For Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 20; //

  const isFirstRender = useRef(true);

  // Fetch From API
  const fetchPapers = async (
    overrideDomain?: string,
    pageNumber: number = 1,
    overrideQuery?: string,
  ) => {
    setLoading(true);

    const activeDomain =
      overrideDomain !== undefined ? overrideDomain : selectedDomain;
    const activeQuery =
      overrideQuery !== undefined ? overrideQuery : debouncedQuery;

    try {
      const response = await api.get("/papers/", {
        params: {
          q: activeQuery || undefined,
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

  // Debounce

  useEffect(() => {
    // 500ms
    const timerId = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 500);

    // Timer Clear
    return () => {
      clearTimeout(timerId);
    };
  }, [searchQuery]);

  // Call API for Debounce
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    setCurrentPage(1);
    fetchPapers(selectedDomain, 1, debouncedQuery);
  }, [debouncedQuery]);

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
            placeholder="Search by title or abstract..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
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

      {/* Table & Pagination Component */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex-1 overflow-hidden flex flex-col">
        <PaperTable papers={papers} loading={loading} />
        <PaginationControls
          currentPage={currentPage}
          totalPages={totalPages}
          totalCount={totalCount}
          pageSize={pageSize}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  );
}
