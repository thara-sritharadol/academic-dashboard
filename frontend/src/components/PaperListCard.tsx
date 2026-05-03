import React from "react";
import { Link } from "react-router-dom";
import { Calendar, ExternalLink } from "lucide-react";

interface TopicItem {
  id: number;
  name: string;
  keywords?: string[];
}

interface PaperListCardProps {
  paper: {
    id: string | number;
    title: string;
    year?: string | number;
    authors?: string[];
    topics?: TopicItem[];
  };
}

const PaperListCard: React.FC<PaperListCardProps> = ({ paper }) => {
  return (
    <Link
      to={`/papers/${paper.id}`}
      className="block p-5 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white hover:border-red-200 hover:shadow-md transition-all group"
    >
      <div className="flex justify-between items-start gap-4">
        {/* Paper Description */}
        <div className="flex-1">
          <h3 className="font-bold text-slate-800 group-hover:text-red-600 transition-colors line-clamp-2 mb-2">
            {paper.title}
          </h3>
          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500">
            <span className="flex items-center gap-1.5">
              <Calendar size={14} /> {paper.year || "N/A"}
            </span>
            <span className="w-1 h-1 rounded-full bg-slate-300"></span>
            <span className="truncate max-w-[200px] md:max-w-md">
              {paper.authors?.join(", ")}
            </span>
          </div>
        </div>

        {paper.topics && paper.topics.length > 0 && (
          <div className="shrink-0 hidden sm:block">
            <span className="bg-yellow-50 text-yellow-700 border border-yellow-100 px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap">
              {paper.topics[0].name}
            </span>
          </div>
        )}

        {/* link Icon */}
        <ExternalLink
          size={18}
          className="text-slate-300 group-hover:text-red-500 shrink-0 mt-1"
        />
      </div>
    </Link>
  );
};

export default PaperListCard;
