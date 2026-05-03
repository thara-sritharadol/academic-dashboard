import { useState, useEffect, useRef } from "react";
import { Search, Filter, ChevronDown } from "lucide-react";
import api from "../services/api";
import type { Paper } from "../types/models";
import PaginationControls from "../components/PaginationControls";
import PaperTable from "../components/PaperTable";

interface TopicResponse {
  topic_id: number;
  name: string;
  keywords: string[];
}

export default function PaperSearch() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [availableDomains, setAvailableDomains] = useState<TopicResponse[]>([]);

  // State For Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 20;

  const isFirstRender = useRef(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchPapers = async (
    overrideDomains?: string[],
    pageNumber: number = 1,
    overrideQuery?: string,
  ) => {
    setLoading(true);

    const activeDomains =
      overrideDomains !== undefined ? overrideDomains : selectedDomains;
    const activeQuery =
      overrideQuery !== undefined ? overrideQuery : debouncedQuery;

    try {
      const response = await api.get("/papers/", {
        params: {
          q: activeQuery || undefined,
          domains:
            activeDomains.length > 0 ? activeDomains.join(",") : undefined,
          page: pageNumber,
          search: searchQuery,
        },
      });

      const payload = response.data;

      if (payload && payload.data && payload.pagination) {
        setPapers(payload.data);
        setTotalCount(payload.pagination.total_items);
        setTotalPages(payload.pagination.total_pages);
      } else if (Array.isArray(payload)) {
        setPapers(payload);
        setTotalCount(payload.length);
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
  }, []);

  useEffect(() => {
    const timerId = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 500);
    return () => clearTimeout(timerId);
  }, [searchQuery]);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    setCurrentPage(1);
    fetchPapers(selectedDomains, 1, debouncedQuery);
  }, [debouncedQuery]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      fetchPapers(selectedDomains, newPage);
    }
  };

  const handleToggleDomain = (domainName: string) => {
    const newSelected = selectedDomains.includes(domainName)
      ? selectedDomains.filter((d) => d !== domainName)
      : [...selectedDomains, domainName];

    setSelectedDomains(newSelected);
    setCurrentPage(1);
    fetchPapers(newSelected, 1);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="p-8 h-screen flex flex-col">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Paper Repository</h1>
        <p className="text-slate-500">
          Search and explore research papers across all discovered domains.
        </p>
      </div>

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

        <div className="w-full md:w-64 relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-full flex items-center justify-between pl-10 pr-3 py-2 border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 text-left transition-colors"
          >
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Filter size={18} className="text-slate-400" />
            </div>
            <span className="truncate text-slate-700">
              {selectedDomains.length === 0
                ? "All Domains"
                : `${selectedDomains.length} Domain(s) Selected`}
            </span>
            <ChevronDown
              size={16}
              className={`text-slate-400 transition-transform ${isDropdownOpen ? "rotate-180" : ""}`}
            />
          </button>

          {/* Dropdown */}
          {isDropdownOpen && (
            <div className="absolute z-20 mt-2 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-y-auto custom-scrollbar">
              <div className="p-2 space-y-1">
                {/* Dropdown Item */}
                {availableDomains.map((topic) => (
                  <div
                    key={topic.topic_id}
                    onClick={() => handleToggleDomain(topic.name)}
                    className="flex items-start gap-3 p-2.5 hover:bg-slate-50 rounded-md cursor-pointer transition-colors select-none"
                  >
                    {/* Checkbox */}
                    <div className="flex-shrink-0 pt-0.5">
                      <input
                        type="checkbox"
                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4 pointer-events-none"
                        checked={selectedDomains.includes(topic.name)}
                        readOnly
                      />
                    </div>

                    <div className="flex-1 min-w-0">
                      {/* Topic Name */}
                      <div className="text-sm text-slate-700 font-medium leading-tight truncate">
                        {topic.name}
                      </div>

                      {/* Keywords */}
                      {topic.keywords && topic.keywords.length > 0 && (
                        <div className="text-[11px] text-slate-400 mt-1 truncate">
                          {topic.keywords.join(", ")}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {availableDomains.length === 0 && (
                  <div className="p-2 text-sm text-slate-500 text-center">
                    No domains available
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

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
