import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

interface DistributionChartProps {
  data: any[];
}

const DistributionChart: React.FC<DistributionChartProps> = ({ data }) => {
  return (
    <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col lg:col-span-1">
      <h2 className="text-lg font-bold text-slate-800 mb-1">
        Overall Distribution
      </h2>
      <p className="text-xs text-slate-500 mb-4">
        All-time publications by domain
      </p>

      {/* Container for Scrollbar */}
      <div className="flex-1 w-full overflow-y-auto custom-scrollbar pr-2 max-h-[400px]">
        {data.length > 0 ? (
          <ResponsiveContainer
            width="100%"
            height={Math.max(250, data.length * 40)}
          >
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 0, right: 10, left: -20, bottom: 0 }}
            >
              <XAxis type="number" hide />
              <YAxis
                dataKey="name"
                type="category"
                width={130}
                tick={{ fontSize: 11, fill: "#64748b" }}
                axisLine={false}
                tickLine={false}
              />
              <RechartsTooltip
                cursor={{ fill: "#f1f5f9" }}
                formatter={(value: any) => [`${value} Papers`, "Publications"]}
                contentStyle={{
                  borderRadius: "8px",
                  border: "none",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full min-h-[250px] flex items-center justify-center text-slate-400">
            No data available
          </div>
        )}
      </div>
    </div>
  );
};

export default DistributionChart;
