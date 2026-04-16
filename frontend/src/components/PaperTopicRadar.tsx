import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

interface PaperTopicRadarProps {
  distribution: number[];
  topicMap: Record<number, string>;
}

const PaperTopicRadar: React.FC<PaperTopicRadarProps> = ({
  distribution,
  topicMap,
}) => {
  const prepareRadarData = (dist: number[]) => {
    if (!dist || dist.length === 0) return [];

    return dist
      .map((prob, index) => {
        const rawSubject = topicMap[index] || `Topic ${index}`;
        const shortSubject =
          rawSubject.length > 22
            ? rawSubject.substring(0, 22) + "..."
            : rawSubject;

        return {
          subject: shortSubject,
          originalProb: prob,
        };
      })
      .filter((item) => item.originalProb > 0.02)
      .sort((a, b) => b.originalProb - a.originalProb)
      .slice(0, 6)
      .map((item) => ({
        subject: item.subject,
        probability: Math.round(item.originalProb * 100),
      }));
  };

  const radarData = prepareRadarData(distribution);

  if (radarData.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
      <h3 className="text-lg font-bold text-slate-800 mb-2">
        Topic Distribution
      </h3>
      <p className="text-xs text-slate-500 mb-4">
        Probability breakdown of research domains
      </p>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis
              dataKey="subject"
              tick={{ fill: "#64748b", fontSize: 10 }}
            />
            <PolarRadiusAxis
              angle={30}
              domain={[0, "auto"]}
              tick={{ fill: "#94a3b8", fontSize: 10 }}
              axisLine={false}
            />
            <Tooltip formatter={(value: any) => [`${value}%`, "Probability"]} />
            <Radar
              name="Paper"
              dataKey="probability"
              stroke="#2563eb"
              fill="#3b82f6"
              fillOpacity={0.4}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PaperTopicRadar;
