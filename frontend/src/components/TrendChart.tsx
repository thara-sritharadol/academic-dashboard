import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  Brush,
} from "recharts";
import { getDynamicColor } from "../utils/colors";

interface TrendChartProps {
  data: any[];
  domainInfo: any[];
  selectedDomains: string[];
}

const TrendChart: React.FC<TrendChartProps> = ({
  data,
  domainInfo,
  selectedDomains,
}) => {
  return (
    <div className="lg:col-span-3 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
      <h2 className="text-lg font-bold mb-6">Domain Publications Over Time</h2>
      <div className="h-[450px] w-full">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                stroke="#e2e8f0"
              />
              <XAxis
                dataKey="year"
                tick={{ fill: "#64748b" }}
                tickMargin={10}
              />
              <YAxis tick={{ fill: "#64748b" }} tickMargin={10} />
              <RechartsTooltip
                contentStyle={{
                  borderRadius: "8px",
                  border: "none",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
              />
              <Legend wrapperStyle={{ paddingTop: "20px" }} />

              {domainInfo
                .filter((d) => selectedDomains.includes(d.fullKey))
                .map((domain) => {
                  const colorIndex = domainInfo.findIndex(
                    (d) => d.fullKey === domain.fullKey,
                  );
                  return (
                    <Line
                      key={domain.fullKey}
                      name={domain.shortName}
                      dataKey={domain.fullKey}
                      type="monotone"
                      stroke={getDynamicColor(colorIndex)}
                      strokeWidth={3}
                      dot={{ r: 4, strokeWidth: 2 }}
                      activeDot={{ r: 6 }}
                    />
                  );
                })}
              <Brush
                dataKey="year"
                height={30}
                stroke="#94a3b8"
                fill="#f8fafc"
                startIndex={data.length > 10 ? data.length - 21 : 0}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-400">
            No trend data available
          </div>
        )}
      </div>
    </div>
  );
};

export default TrendChart;
