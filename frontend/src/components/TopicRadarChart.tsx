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

interface DistributionItem {
  subject: string;
  probability: number;
  keywords?: string[];
}

interface TopicRadarChartProps {
  topicProfile: DistributionItem[];
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white/95 backdrop-blur-sm p-4 border border-slate-200 rounded-xl shadow-lg max-w-xs z-50">
        <p className="font-bold text-slate-800 text-sm mb-1 leading-tight">
          {data.fullSubject}
        </p>
        <p className="text-yellow-600 font-semibold text-sm mb-3">
          Relevance: {data.probability}%
        </p>
        {data.keywords && data.keywords.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 font-semibold mb-1.5 uppercase tracking-wider">
              Keywords
            </p>
            <div className="flex flex-wrap gap-1.5">
              {data.keywords.slice(0, 5).map((kw: string, i: number) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-medium border border-slate-200"
                >
                  {kw}
                </span>
              ))}
              {data.keywords.length > 5 && (
                <span className="px-1.5 py-0.5 text-slate-400 text-[10px] font-medium">
                  +{data.keywords.length - 5} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }
  return null;
};

const TopicRadarChart: React.FC<TopicRadarChartProps> = ({ topicProfile }) => {
  const prepareExpertiseData = (profile: DistributionItem[]) => {
    if (!profile || profile.length === 0) return [];

    return profile
      .filter((item) => item.probability > 0.02)
      .sort((a, b) => b.probability - a.probability)
      .slice(0, 6)
      .map((item) => {
        const rawSubject = item.subject;
        const shortSubject =
          rawSubject.length > 22
            ? rawSubject.substring(0, 22) + "..."
            : rawSubject;

        return {
          subject: shortSubject,
          fullSubject: rawSubject,
          probability: Math.round(item.probability * 100),
          keywords: item.keywords || [],
        };
      });
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
              {/* 🛠️ เรียกใช้ CustomTooltip */}
              <Tooltip
                content={<CustomTooltip />}
                cursor={{ fill: "rgba(226, 232, 240, 0.4)" }}
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
