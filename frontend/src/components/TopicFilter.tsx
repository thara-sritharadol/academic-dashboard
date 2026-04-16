import React from "react";
import { CheckSquare, Square } from "lucide-react";
import { getDynamicColor } from "../utils/colors";

interface TopicFilterProps {
  domainInfo: any[];
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
                <div className="font-semibold text-sm text-slate-800 flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: dotColor }}
                  ></span>
                  {domain.shortName}
                </div>
                {domain.names && (
                  <div className="text-xs text-slate-500 mt-1 line-clamp-2 leading-tight">
                    {domain.names}
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
