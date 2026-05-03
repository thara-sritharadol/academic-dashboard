import React from "react";
import { Filter, Check, X } from "lucide-react";

interface TopicResponse {
  topic_id: number;
  name: string;
  keywords: string[];
}

interface NetworkTopicFilterProps {
  availableDomains: TopicResponse[];
  selectedDomains: string[];
  pendingDomains: string[];
  isFilterOpen: boolean;
  setIsFilterOpen: (isOpen: boolean) => void;
  toggleDomain: (domain: string) => void;
  applyFilter: () => void;
  clearFilter: () => void;
}

const NetworkTopicFilter: React.FC<NetworkTopicFilterProps> = ({
  availableDomains,
  selectedDomains,
  pendingDomains,
  isFilterOpen,
  setIsFilterOpen,
  toggleDomain,
  applyFilter,
  clearFilter,
}) => {
  return (
    <div className="relative z-20">
      <button
        onClick={() => setIsFilterOpen(!isFilterOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 rounded-lg shadow-sm hover:bg-slate-50 text-slate-700 font-medium transition-colors"
      >
        <Filter
          size={18}
          className={
            selectedDomains.length > 0 ? "text-red-600" : "text-red-400"
          }
        />
        Filter Topics{" "}
        {selectedDomains.length > 0 && (
          <span className="bg-red-100 text-red-700 py-0.5 px-2 rounded-full text-xs font-bold">
            {selectedDomains.length}
          </span>
        )}
      </button>

      {isFilterOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden flex flex-col">
          <div className="p-3 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
            <span className="font-semibold text-slate-700 text-sm">
              Select Topics
            </span>
            <button
              onClick={() => setIsFilterOpen(false)}
              className="text-slate-400 hover:text-slate-600"
            >
              <X size={16} />
            </button>
          </div>

          <div className="max-h-[22rem] overflow-y-auto p-2 custom-scrollbar">
            {availableDomains.length === 0 ? (
              <p className="p-2 text-sm text-slate-500 text-center">
                No topics available.
              </p>
            ) : (
              availableDomains.map((topic) => {
                const isChecked = pendingDomains.includes(topic.name);

                return (
                  <div
                    key={topic.topic_id}
                    onClick={() => toggleDomain(topic.name)}
                    className="flex items-start gap-3 p-2.5 hover:bg-slate-50 rounded-lg cursor-pointer transition-colors group select-none"
                  >
                    <div
                      className={`mt-0.5 shrink-0 w-4 h-4 rounded flex items-center justify-center border transition-colors ${
                        isChecked
                          ? "bg-yellow-600 border-yellow-600"
                          : "border-slate-300 group-hover:border-blue-400"
                      }`}
                    >
                      {isChecked && <Check size={12} className="text-white" />}
                    </div>

                    <div className="flex-1 min-w-0 pointer-events-none">
                      {/* Keywords label */}
                      <div className="flex flex-wrap gap-1 mb-1.5">
                        {topic.keywords && topic.keywords.length > 0 ? (
                          <>
                            {topic.keywords.slice(0, 4).map((kw, i) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-semibold border border-slate-200"
                              >
                                {kw}
                              </span>
                            ))}
                            {topic.keywords.length > 4 && (
                              <span className="px-1.5 py-0.5 bg-slate-50 text-slate-400 rounded text-[10px] font-medium border border-slate-100">
                                +{topic.keywords.length - 4}
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-[11px] font-semibold text-slate-400">
                            No keywords
                          </span>
                        )}
                      </div>

                      {/* Topic (Subtitle) */}
                      <span className="text-xs text-slate-500 truncate block">
                        {topic.name}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          <div className="p-3 border-t border-slate-100 bg-slate-50 flex gap-2">
            <button
              onClick={clearFilter}
              className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded-md transition-colors"
            >
              Clear All
            </button>
            <button
              onClick={applyFilter}
              className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-md shadow-sm transition-colors"
            >
              Apply Filter
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NetworkTopicFilter;
