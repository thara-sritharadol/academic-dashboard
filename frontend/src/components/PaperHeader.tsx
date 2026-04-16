import React from "react";
import { Link } from "react-router-dom";
import { Calendar, Quote, Users } from "lucide-react";

interface PaperHeaderProps {
  paper: {
    title: string;
    cluster_label?: string;
    year?: number | string;
    citation_count?: number;
    authors?: any[];
  };
}

const PaperHeader: React.FC<PaperHeaderProps> = ({ paper }) => {
  return (
    <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
      <div className="flex flex-wrap items-center gap-3 mb-4 text-sm font-medium">
        <span className="bg-yellow-100 text-yellow-700 px-3 py-1 rounded-full">
          {paper.cluster_label || "Uncategorized"}
        </span>
        <span className="flex items-center text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
          <Calendar size={14} className="mr-1.5" /> {paper.year || "N/A"}
        </span>
        <span className="flex items-center text-amber-600 bg-amber-50 px-3 py-1 rounded-full">
          <Quote size={14} className="mr-1.5" /> {paper.citation_count}{" "}
          Citations
        </span>
      </div>

      <h1 className="text-3xl font-bold text-slate-800 leading-tight mb-6">
        {paper.title}
      </h1>

      <div className="flex flex-wrap gap-3">
        {paper.authors?.map((author: any) => (
          <div
            key={author.id}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
              author.faculty
                ? "bg-red-50 border-red-100 text-red-800"
                : "bg-slate-50 border-slate-200 text-slate-700"
            }`}
          >
            <Users
              size={16}
              className={author.faculty ? "text-red-500" : "text-slate-400"}
            />
            <Link to={`/authors/${author.id}`}>
              <div className="font-semibold text-sm">{author.name}</div>
              {author.faculty && (
                <div className="text-xs opacity-75">{author.faculty}</div>
              )}
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PaperHeader;
