import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";

interface TopicRadarChartProps {
  topicProfile: number[];
  topicMap: Record<number, string>;
}

const TopicRadarChart: React.FC<TopicRadarChartProps> = ({
  topicProfile,
  topicMap,
}) => {
  // Logic
  const prepareExpertiseData = (profile: number[]) => {
    if (!profile || profile.length === 0) return [];

    return profile
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

  const expertiseData = prepareExpertiseData(topicProfile);

  return (
    <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 sticky top-6">
      <h2 className="text-xl font-bold text-slate-800 mb-2">Topic Profile</h2>
      <p className="text-xs text-slate-500 mb-6">
        Aggregated from all published papers
      </p>

      {expertiseData.length > 0 ? (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart
              cx="50%"
              cy="50%"
              outerRadius="65%"
              data={expertiseData}
            >
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{ fill: "#64748b", fontSize: 11, fontWeight: 500 }}
              />
              <PolarRadiusAxis
                angle={30}
                domain={[0, "auto"]}
                tick={{ fill: "#94a3b8", fontSize: 10 }}
                axisLine={false}
              />
              <RechartsTooltip
                formatter={(value) => [`${value}%`, "Relevance"]}
              />
              <Radar
                name="Expertise"
                dataKey="probability"
                stroke="#c79f20"
                fill="#FFD13F"
                fillOpacity={0.4}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-64 flex flex-col items-center justify-center text-slate-400">
          <div className="mb-3 opacity-20"> {/* Icon Radar*/} </div>
          <p>Not enough data to generate profile</p>
        </div>
      )}
    </div>
  );
};

export default TopicRadarChart;
