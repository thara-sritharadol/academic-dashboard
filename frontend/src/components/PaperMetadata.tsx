import React from "react";
import { Building2, ExternalLink } from "lucide-react";

interface PaperMetadataProps {
  venue?: string;
  doi?: string;
  url?: string;
}

const PaperMetadata: React.FC<PaperMetadataProps> = ({ venue, doi, url }) => {
  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
      <h3 className="text-lg font-bold text-slate-800 mb-4">
        Publication Details
      </h3>
      <div className="space-y-4">
        {venue && (
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Journal / Venue
            </div>
            <div className="flex items-start gap-2 text-slate-700 text-sm font-medium">
              <Building2 size={16} className="text-slate-400 shrink-0 mt-0.5" />
              {venue}
            </div>
          </div>
        )}

        {doi && (
          <div>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              DOI
            </div>
            <a
              href={url || `https://doi.org/${doi}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 hover:underline font-medium break-all"
            >
              {doi} <ExternalLink size={14} />
            </a>
          </div>
        )}

        {!venue && !doi && (
          <div className="text-sm text-slate-500 italic">
            No publication details available.
          </div>
        )}
      </div>
    </div>
  );
};

export default PaperMetadata;
