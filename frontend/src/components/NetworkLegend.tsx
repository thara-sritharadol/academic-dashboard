import React from "react";

const NetworkLegend: React.FC = () => {
  return (
    <div className="absolute bottom-4 right-4 z-10 bg-white/95 p-4 rounded-xl border border-slate-200 shadow-lg w-56 pointer-events-none">
      <h3 className="text-sm font-bold text-slate-700 mb-3 uppercase tracking-wider">
        Institution
      </h3>
      <div className="space-y-2.5">
        <div className="flex items-center gap-2.5 text-sm">
          <span
            className="w-4 h-4 rounded-full shrink-0 shadow-sm"
            style={{ backgroundColor: "#FFD13F" }}
          ></span>
          <span className="font-semibold text-slate-800">Thammasat Univ.</span>
        </div>
        <div className="flex items-center gap-2.5 text-sm">
          <span
            className="w-4 h-4 rounded-full shrink-0 shadow-sm"
            style={{ backgroundColor: "#d1d5db" }}
          ></span>
          <span className="text-slate-600">External Network</span>
        </div>
      </div>
    </div>
  );
};

export default NetworkLegend;
