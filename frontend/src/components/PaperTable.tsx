import React from "react";
import { Link } from "react-router-dom";
import { BookOpen, ExternalLink } from "lucide-react";
import type { Paper } from "../types/models";
import { getDynamicColor } from "../utils/colors";

interface PaperTableProps {
  papers: Paper[];
  loading: boolean;
}

const PaperTable: React.FC<PaperTableProps> = ({ papers, loading }) => {
  const getLabelName = (str: string) => {
    if (!str) return "";
    const parts = str.split(":");
    return parts.length > 1 ? parts[1].trim() : str.trim();
  };

  const getLabelId = (str: string) => {
    if (!str) return 0;
    const parts = str.split(":");
    return parts.length > 1 ? parseInt(parts[0], 10) : 0;
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500">
        <div className="animate-pulse flex flex-col items-center gap-2">
          <BookOpen size={32} className="text-slate-300" />
          <p>Searching database...</p>
        </div>
      </div>
    );
  }

  if (papers.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500">
        No papers found matching your criteria.
      </div>
    );
  }

  return (
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
                    const labelId = getLabelId(label);

                    return (
                      <span
                        key={idx}
                        className="px-2.5 py-1 inline-flex text-[11px] leading-4 font-semibold rounded-full border"
                        style={{
                          backgroundColor: getDynamicColor(labelId, 0.1), //
                          borderColor: getDynamicColor(labelId, 0.3), //
                          color: getDynamicColor(labelId, 1), //
                        }}
                      >
                        {getLabelName(label)}
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
  );
};

export default PaperTable;
