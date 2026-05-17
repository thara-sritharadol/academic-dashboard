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
              Article Title
            </th>
            <th
              scope="col"
              className="px-6 py-4 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider w-1/5"
            >
              Researcher
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
              Discovered Topics
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
                  {paper.authors?.join(", ") || "Unknown Author"}
                </div>
              </td>
              <td className="px-6 py-4 text-center whitespace-nowrap">
                <div className="text-sm text-slate-700">
                  {paper.year || "-"}
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="flex flex-col gap-4">
                  {" "}
                  {/* gap between */}
                  {paper.topics?.map((topic, idx) => {
                    const bgColor = getDynamicColor(topic.id, 0.1);
                    const borderColor = getDynamicColor(topic.id, 0.3);
                    const textColor = getDynamicColor(topic.id, 1);

                    return (
                      <div key={idx} className="flex flex-col items-start">
                        {topic.keywords && topic.keywords.length > 0 ? (
                          <div className="flex flex-wrap gap-1 mb-1">
                            {topic.keywords.slice(0, 6).map((kw, i) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded-md border text-[10px] font-semibold"
                                style={{
                                  backgroundColor: bgColor,
                                  borderColor: borderColor,
                                  color: textColor,
                                }}
                              >
                                {kw}
                              </span>
                            ))}
                            {/* rest total */}
                            {topic.keywords.length > 6 && (
                              <span className="px-1.5 py-0.5 bg-slate-50 text-slate-400 rounded-md border border-slate-100 text-[10px] font-medium">
                                +{topic.keywords.length - 4}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-[10px] font-semibold text-slate-400 mb-1">
                            No keywords
                          </span>
                        )}

                        {/* Topic name*/}
                        <div className="text-xs text-slate-500 leading-tight line-clamp-2">
                          {topic.name}
                        </div>
                      </div>
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
