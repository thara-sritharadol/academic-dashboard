import React from "react";
import { Filter, Check, X } from "lucide-react";

interface NetworkTopicFilterProps {
  availableDomains: string[];
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
          <span className="bg-red-100 text-red-700 py-0.5 px-2 rounded-full text-xs">
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

          <div className="max-h-64 overflow-y-auto p-2">
            {availableDomains.length === 0 ? (
              <p className="p-2 text-sm text-slate-500 text-center">
                No topics available.
              </p>
            ) : (
              availableDomains.map((domainStr) => {
                const parts = domainStr.split(":");
                const shortName = parts[0] ? parts[0].trim() : domainStr;
                const fullName =
                  parts.length > 1
                    ? parts.slice(1).join(":").trim()
                    : domainStr;
                const isChecked = pendingDomains.includes(domainStr);

                return (
                  <div
                    key={domainStr}
                    onClick={() => toggleDomain(domainStr)}
                    className="flex items-start gap-3 p-2 hover:bg-slate-50 rounded-lg cursor-pointer transition-colors group"
                  >
                    <div
                      className={`mt-0.5 w-4 h-4 rounded flex items-center justify-center border ${
                        isChecked
                          ? "bg-yellow-600 border-yellow-600"
                          : "border-slate-300 group-hover:border-blue-400"
                      }`}
                    >
                      {isChecked && <Check size={12} className="text-white" />}
                    </div>
                    <div className="flex-1 text-sm pointer-events-none">
                      <span className="font-medium text-slate-700 block">
                        {shortName}
                      </span>
                      <span
                        className="text-xs text-slate-400 line-clamp-1"
                        title={fullName}
                      >
                        {fullName}
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
