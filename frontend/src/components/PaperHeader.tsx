import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import { Calendar, Quote, Users } from "lucide-react";

interface PaperHeaderProps {
  paper: {
    title: string;
    year?: number | string;
    citation_count?: number;
    authors?: any[];
  };
}

const PaperHeader: React.FC<PaperHeaderProps> = ({ paper }) => {
  const sortedAuthors = useMemo(() => {
    if (!paper.authors) return [];

    const internalAuthors = paper.authors.filter(
      (a) => a.institution && a.institution !== "External",
    );

    const externalAuthors = paper.authors.filter(
      (a) => !a.institution || a.institution === "External",
    );

    return [...internalAuthors, ...externalAuthors];
  }, [paper.authors]);

  return (
    <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
      <div className="flex flex-wrap items-center gap-3 mb-4 text-sm font-medium">
        <span className="flex items-center text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
          <Calendar size={14} className="mr-1.5" /> {paper.year || "N/A"}
        </span>
        <span className="flex items-center text-amber-600 bg-amber-50 px-3 py-1 rounded-full">
          <Quote size={14} className="mr-1.5" /> {paper.citation_count || 0}{" "}
          Citations
        </span>
      </div>

      <h1 className="text-3xl font-bold text-slate-800 leading-tight mb-6">
        {paper.title}
      </h1>

      <div className="flex flex-wrap gap-3">
        {sortedAuthors.map((author: any) => {
          const isInternal =
            author.institution && author.institution !== "External";

          return (
            <div
              key={author.id}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                isInternal
                  ? "bg-red-50 border-red-100 text-red-800"
                  : "bg-slate-50 border-slate-200 text-slate-700"
              }`}
            >
              <Users
                size={16}
                className={isInternal ? "text-red-500" : "text-slate-400"}
              />
              <Link to={`/authors/${author.id}`}>
                <div className="font-semibold text-sm">{author.name}</div>
                {isInternal && (
                  <div className="text-xs opacity-75">{author.institution}</div>
                )}
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PaperHeader;
