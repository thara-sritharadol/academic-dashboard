import React from "react";
import { CheckSquare, Square } from "lucide-react";
import { getDynamicColor } from "../utils/colors";
import type { DomainInfo } from "../types/models";

interface TopicFilterProps {
  domainInfo: DomainInfo[];
  selectedDomains: string[];
  onToggle: (key: string) => void;
  onSelectAll: () => void;
  onClearAll: () => void;
}

const TopicFilter: React.FC<TopicFilterProps> = ({
  domainInfo,
  selectedDomains,
  onToggle,
  onSelectAll,
  onClearAll,
}) => {
  return (
    <div className="lg:col-span-1 bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col h-[530px]">
      <h2 className="text-sm font-bold text-slate-700 mb-3 px-2 uppercase tracking-wider">
        Filter Topics ({selectedDomains.length}/{domainInfo.length})
      </h2>
      <div className="flex-1 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
        {domainInfo.map((domain, index) => {
          const isSelected = selectedDomains.includes(domain.fullKey);
          const dotColor = getDynamicColor(index);

          return (
            <div
              key={domain.fullKey}
              onClick={() => onToggle(domain.fullKey)}
              className={`p-3 rounded-lg border cursor-pointer transition-all flex items-start gap-3
                ${isSelected ? "bg-yellow-50 border-yellow-200" : "bg-white border-slate-100 hover:border-slate-300 opacity-60 hover:opacity-100"}`}
            >
              <div
                className="mt-0.5"
                style={{ color: isSelected ? dotColor : "#cbd5e1" }}
              >
                {isSelected ? <CheckSquare size={18} /> : <Square size={18} />}
              </div>
              <div className="flex-1">
                <div className="flex items-start gap-2">
                  <span
                    className="w-2 h-2 rounded-full mt-1.5 shrink-0 shadow-sm"
                    style={{ backgroundColor: dotColor }}
                  ></span>

                  <div className="flex flex-wrap gap-1">
                    {domain.keywords && domain.keywords.length > 0 ? (
                      <>
                        {domain.keywords.slice(0, 7).map((keyword, i) => (
                          <span
                            key={i}
                            className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md text-xs font-semibold border border-slate-200"
                          >
                            {keyword}
                          </span>
                        ))}
                        {domain.keywords.length > 4 && (
                          <span className="px-2 py-0.5 bg-slate-50 text-slate-400 rounded-md text-xs font-semibold">
                            +{domain.keywords.length - 4}
                          </span>
                        )}
                      </>
                    ) : (
                      <span className="text-sm font-semibold text-slate-800">
                        Unknown Keywords
                      </span>
                    )}
                  </div>
                </div>

                {domain.name && (
                  <div className="mt-1.5 ml-4 text-xs text-slate-500 line-clamp-2 leading-relaxed">
                    {domain.name}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-3 mt-2 border-t border-slate-100 flex gap-2">
        <button
          onClick={onSelectAll}
          className="flex-1 text-xs py-1.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-700 font-medium transition"
        >
          Select All
        </button>
        <button
          onClick={onClearAll}
          className="flex-1 text-xs py-1.5 bg-slate-100 hover:bg-slate-200 rounded text-slate-700 font-medium transition"
        >
          Clear All
        </button>
      </div>
    </div>
  );
};

export default TopicFilter;
