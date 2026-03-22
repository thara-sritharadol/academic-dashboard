import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import {
  BookOpen,
  Users,
  Calendar,
  ExternalLink,
  Quote,
  Tag,
  Building2,
  ChevronLeft,
} from "lucide-react";
import api from "../services/api";

export default function PaperDetail() {
  const { id } = useParams();
  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPaperDetail = async () => {
      try {
        const response = await api.get(`/papers/${id}/`);
        setPaper(response.data);
      } catch (error) {
        console.error("Error fetching paper details:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchPaperDetail();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500">
        Paper not found.
      </div>
    );
  }

  // Convert the topic_distribution array into data for a radar chart.
  const prepareRadarData = (distribution: number[]) => {
    if (!distribution || distribution.length === 0) return [];

    return distribution
      .map((prob, index) => ({
        subject: `Topic ${index}`,
        probability: Math.round(prob * 100), // Convert to percentage.
      }))
      .filter((item) => item.probability > 2) // Filter to include only topics that account for more than 2%.
      .sort((a, b) => b.probability - a.probability) // Sorted from highest to lowest.
      .slice(0, 6); // Just display the top 6 to make the graph look nice.
  };

  const radarData = prepareRadarData(paper.topic_distribution);

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Back */}
        <Link
          to="/papers"
          className="inline-flex items-center text-slate-500 hover:text-blue-600 transition-colors mb-4"
        >
          <ChevronLeft size={20} className="mr-1" /> Back to Search
        </Link>

        {/* HEADER SECTION */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
          <div className="flex flex-wrap items-center gap-3 mb-4 text-sm font-medium">
            <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full">
              {paper.cluster_label || "Uncategorized"}
            </span>
            <span className="flex items-center text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
              <Calendar size={14} className="mr-1.5" /> {paper.year || "N/A"}
            </span>
            <span className="flex items-center text-amber-600 bg-amber-50 px-3 py-1 rounded-full">
              <Quote size={14} className="mr-1.5" /> {paper.citation_count}{" "}
              Citations
            </span>
          </div>

          <h1 className="text-3xl font-bold text-slate-800 leading-tight mb-6">
            {paper.title}
          </h1>

          <div className="flex flex-wrap gap-3">
            {paper.authors?.map((author: any) => (
              <div
                key={author.id}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                  author.faculty
                    ? "bg-blue-50 border-blue-100 text-blue-800"
                    : "bg-slate-50 border-slate-200 text-slate-700"
                }`}
              >
                <Users
                  size={16}
                  className={
                    author.faculty ? "text-blue-500" : "text-slate-400"
                  }
                />
                <div>
                  <div className="font-semibold text-sm">{author.name}</div>
                  {author.faculty && (
                    <div className="text-xs opacity-75">{author.faculty}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CONTENT GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Abstract & Details */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-4">
                <BookOpen className="text-blue-600" /> Abstract
              </h2>
              <p className="text-slate-600 leading-relaxed text-justify">
                {paper.abstract || "No abstract available for this paper."}
              </p>
            </div>

            {/* Related Topics (Multi-labels) */}
            {paper.predicted_multi_labels &&
              paper.predicted_multi_labels.length > 0 && (
                <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
                  <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-4">
                    <Tag className="text-blue-600" /> Related Topics
                  </h2>
                  <div className="flex flex-wrap gap-2">
                    {paper.predicted_multi_labels.map(
                      (label: string, idx: number) => (
                        <span
                          key={idx}
                          className="bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-sm"
                        >
                          {label}
                        </span>
                      ),
                    )}
                  </div>
                </div>
              )}
          </div>

          {/* Radar Chart & Meta Info */}
          <div className="space-y-6">
            {/* Topic Distribution Radar Chart */}
            {radarData.length > 0 && (
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
                <h3 className="text-lg font-bold text-slate-800 mb-2">
                  Topic Distribution
                </h3>
                <p className="text-xs text-slate-500 mb-4">
                  Probability breakdown of research domains
                </p>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart
                      cx="50%"
                      cy="50%"
                      outerRadius="70%"
                      data={radarData}
                    >
                      <PolarGrid stroke="#e2e8f0" />
                      <PolarAngleAxis
                        dataKey="subject"
                        tick={{ fill: "#64748b", fontSize: 10 }}
                      />
                      {/* เปลี่ยนจาก domain={[0, 100]} เป็น 'auto' และเปิด tick ให้แสดงตัวเลขสเกล */}
                      <PolarRadiusAxis
                        angle={30}
                        domain={[0, "auto"]}
                        tick={{ fill: "#94a3b8", fontSize: 10 }}
                        axisLine={false}
                      />
                      <Tooltip
                        formatter={(value) => [`${value}%`, "Probability"]}
                      />
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
            )}

            {/* Publication Meta */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
              <h3 className="text-lg font-bold text-slate-800 mb-4">
                Publication Details
              </h3>
              <div className="space-y-4">
                {paper.venue && (
                  <div>
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Journal / Venue
                    </div>
                    <div className="flex items-start gap-2 text-slate-700 text-sm font-medium">
                      <Building2
                        size={16}
                        className="text-slate-400 shrink-0 mt-0.5"
                      />
                      {paper.venue}
                    </div>
                  </div>
                )}

                {paper.doi && (
                  <div>
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      DOI
                    </div>
                    <a
                      href={paper.url || `https://doi.org/${paper.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 hover:underline font-medium break-all"
                    >
                      {paper.doi} <ExternalLink size={14} />
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
