import React from "react";

interface StatCardProps {
  title: string;
  value: number | string | undefined;
  icon: React.ReactNode;
  variant: "red" | "emerald" | "yellow";
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, variant }) => {
  // Mapping Color from variant to define Tailwind Classes
  const variants = {
    red: { bg: "bg-red-50", text: "text-red-600" },
    emerald: { bg: "bg-emerald-50", text: "text-emerald-600" },
    yellow: { bg: "bg-yellow-50", text: "text-yellow-600" },
  };

  const { bg, text } = variants[variant];

  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
      <div className={`p-4 ${bg} ${text} rounded-lg`}>{icon}</div>
      <div>
        <p className="text-sm text-slate-500 font-medium">{title}</p>
        <p className="text-3xl font-bold">
          {typeof value === "number" ? value.toLocaleString() : value || "0"}
        </p>
      </div>
    </div>
  );
};

export default StatCard;
