import React from "react";
import { User, Building2, Award } from "lucide-react";

interface AuthorProfileHeaderProps {
  author: {
    name: string;
    works_count: number;
    faculty?: string;
    department?: string;
    institution?: string;
  };
}

const AuthorProfileHeader: React.FC<AuthorProfileHeaderProps> = ({
  author,
}) => {
  return (
    <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200 relative overflow-hidden">
      {/* Decorative Background */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-red-50 rounded-full -translate-y-1/2 translate-x-1/3 opacity-50 blur-3xl pointer-events-none"></div>

      <div className="relative z-10 flex flex-col md:flex-row gap-8 items-start md:items-center">
        {/* Avatar Area */}
        <div className="w-24 h-24 rounded-full bg-yellow-100 flex items-center justify-center shrink-0 border-4 border-white shadow-md">
          <User size={40} className="text-yellow-600" />
        </div>

        {/* Author Info Area */}
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1">
              <Award size={14} /> {author.works_count} Publications
            </span>
          </div>

          <h1 className="text-3xl md:text-4xl font-bold text-slate-800 mb-3">
            {author.name}
          </h1>

          <div className="flex flex-col sm:flex-row gap-2 sm:gap-6 text-slate-600 font-medium text-sm">
            {author.faculty || author.department || author.institution ? (
              <>
                <div className="flex items-center gap-2">
                  <Building2 size={18} className="text-slate-400" />
                  <span>
                    {[author.department, author.faculty]
                      .filter(Boolean)
                      .join(", ")}
                  </span>
                </div>
                {author.institution && (
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-300 hidden sm:block"></span>
                    {author.institution}
                  </div>
                )}
              </>
            ) : (
              <span className="text-slate-400 italic">External Researcher</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthorProfileHeader;
