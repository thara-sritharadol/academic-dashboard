import React from "react";
import { Link } from "react-router-dom";
import { FileText } from "lucide-react";

interface TopResearchersListProps {
  authors: any[];
  topicMap: Record<string, string>;
}

const TopResearchersList: React.FC<TopResearchersListProps> = ({
  authors,
  topicMap,
}) => {
  return (
    <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Top Researchers</h2>
          <p className="text-xs text-slate-500">
            Authors with the highest number of publications
          </p>
        </div>
        <span className="text-sm text-red-600 hover:text-red-800 font-medium cursor-pointer">
          View All
        </span>
      </div>

      <div className="flex-1 flex flex-col gap-3 justify-center">
        {authors.map((author, index) => {
          const cleanId = String(author.primary_cluster).trim();
          const topicName =
            topicMap[cleanId] || `Topic ${author.primary_cluster}`;

          return (
            <Link
              key={author.id}
              to={`/authors/${author.id}`}
              className="flex items-center p-3 rounded-lg border border-slate-100 hover:bg-red-50 hover:border-red-200 transition-all group"
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm mr-4 shrink-0
                ${
                  index === 0
                    ? "bg-amber-100 text-amber-600"
                    : index === 1
                      ? "bg-slate-200 text-slate-600"
                      : index === 2
                        ? "bg-orange-100 text-orange-600"
                        : "bg-slate-100 text-slate-400"
                }`}
              >
                #{index + 1}
              </div>

              <div className="flex-1 min-w-0 pr-4">
                <h3 className="font-bold text-slate-800 group-hover:text-red-600 transition-colors truncate">
                  {author.name}
                </h3>
                <p className="text-xs text-slate-500 truncate">
                  {author.faculty || "External Researcher"}
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                {author.primary_cluster !== null &&
                  author.primary_cluster !== undefined && (
                    <span
                      className="hidden sm:inline-block bg-yellow-50 text-yellow-700 border border-yellow-100 px-2.5 py-1 rounded text-[11px] font-semibold max-w-[150px] truncate"
                      title={topicName}
                    >
                      {topicName}
                    </span>
                  )}
                <div className="flex items-center gap-1.5 bg-slate-100 px-3 py-1.5 rounded-lg text-sm font-bold text-slate-700">
                  <FileText size={14} className="text-slate-400" />
                  {author.works_count}
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
};

export default TopResearchersList;
