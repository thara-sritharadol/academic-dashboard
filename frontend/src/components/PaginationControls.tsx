import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
}

const PaginationControls: React.FC<PaginationControlsProps> = ({
  currentPage,
  totalPages,
  totalCount,
  pageSize,
  onPageChange,
}) => {
  // Lenght
  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalCount);

  if (totalCount === 0) return null;

  return (
    <div className="bg-white px-6 py-4 border-t border-slate-200 flex items-center justify-between shrink-0">
      <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-slate-700">
            Showing <span className="font-semibold">{startItem}</span> to{" "}
            <span className="font-semibold">{endItem}</span> of{" "}
            <span className="font-semibold">{totalCount}</span> results
          </p>
        </div>
        <div>
          <nav
            className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px"
            aria-label="Pagination"
          >
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className={`relative inline-flex items-center px-2 py-2 rounded-l-md border border-slate-300 bg-white text-sm font-medium ${
                currentPage === 1
                  ? "text-slate-300 cursor-not-allowed"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
            >
              <span className="sr-only">Previous</span>
              <ChevronLeft size={18} aria-hidden="true" />
            </button>

            <span className="relative inline-flex items-center px-4 py-2 border border-slate-300 bg-white text-sm font-medium text-slate-700">
              Page {currentPage} of {totalPages}
            </span>

            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className={`relative inline-flex items-center px-2 py-2 rounded-r-md border border-slate-300 bg-white text-sm font-medium ${
                currentPage === totalPages
                  ? "text-slate-300 cursor-not-allowed"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
            >
              <span className="sr-only">Next</span>
              <ChevronRight size={18} aria-hidden="true" />
            </button>
          </nav>
        </div>
      </div>
    </div>
  );
};

export default PaginationControls;
