import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";
import {
  User,
  Building2,
  BookOpen,
  ChevronLeft,
  Award,
  ExternalLink,
  Calendar,
} from "lucide-react";
import api from "../services/api";

export default function AuthorDetail() {
  const { id } = useParams();
  const [author, setAuthor] = useState<any>(null);
  const [topicMap, setTopicMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Sending two API calls
        const [authorRes, topicsRes] = await Promise.all([
          api.get(`/authors/${id}/`),
          api.get("/analytics/topics/"),
        ]);

        setAuthor(authorRes.data);

        // Create a map that matches Topic ID with LLM name.
        const map: Record<number, string> = {};
        if (Array.isArray(topicsRes.data)) {
          topicsRes.data.forEach((topicStr: string) => {
            // Use Regex to capture the numbers at the beginning and the text at the end (supports both "0: AI" and "-1: Noise").
            const match = topicStr.match(/(-?\d+)\s*:\s*(.+)/);
            if (match) {
              const topicId = parseInt(match[1], 10);
              const topicName = match[2].trim();
              map[topicId] = topicName;
            }
          });
        }

        // Logging
        console.log("Topic Map Generated:", map);
        setTopicMap(map);
      } catch (error) {
        console.error("Error fetching data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600"></div>
      </div>
    );
  }

  if (!author) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500">
        Author profile not found.
      </div>
    );
  }

  const prepareExpertiseData = (profile: number[]) => {
    if (!profile || profile.length === 0) return [];

    return profile
      .map((prob, index) => {
        // Pull the name from the map. If it's not there, use "Topic X" as an alternative.
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

  const expertiseData = prepareExpertiseData(author.topic_profile);

  //Primary Cluster
  const primaryClusterName =
    author.primary_cluster !== null
      ? topicMap[parseInt(author.primary_cluster)] ||
        `Topic ${author.primary_cluster}`
      : null;

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Back */}
        <Link
          to="/network"
          className="inline-flex items-center text-slate-500 hover:text-red-600 transition-colors mb-4"
        >
          <ChevronLeft size={20} className="mr-1" /> Back to Network
        </Link>

        {/* HEADER SECTION*/}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-50 rounded-full -translate-y-1/2 translate-x-1/3 opacity-50 blur-3xl pointer-events-none"></div>

          <div className="relative z-10 flex flex-col md:flex-row gap-8 items-start md:items-center">
            <div className="w-24 h-24 rounded-full bg-yellow-100 flex items-center justify-center shrink-0 border-4 border-white shadow-md">
              <User size={40} className="text-yellow-600" />
            </div>

            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1">
                  <Award size={14} /> {author.works_count} Publications
                </span>
              </div>

              <h1 className="text-3xl md:text-4xl font-bold text-slate-800 mb-3">
                {author.name}
              </h1>

              <div className="flex flex-col sm:flex-row gap-2 sm:gap-6 text-slate-600 font-medium text-sm">
                {author.faculty || author.department || author.institution ? (
                  <>
                    <div className="flex items-center gap-2">
                      <Building2 size={18} className="text-slate-400" />
                      <span>
                        {[author.department, author.faculty]
                          .filter(Boolean)
                          .join(", ")}
                      </span>
                    </div>
                    {author.institution && (
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-300 hidden sm:block"></span>
                        {author.institution}
                      </div>
                    )}
                  </>
                ) : (
                  <span className="text-slate-400 italic">
                    External Researcher
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* CONTENT GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 sticky top-6">
              <h2 className="text-xl font-bold text-slate-800 mb-2">
                Topic Profile
              </h2>
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
                        tick={{
                          fill: "#64748b",
                          fontSize: 11,
                          fontWeight: 500,
                        }}
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
                  <Radar className="mb-3 opacity-20" />
                  <p>Not enough data to generate profile</p>
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-6">
                <BookOpen className="text-red-600" /> Published Papers
              </h2>

              {author.papers && author.papers.length > 0 ? (
                <div className="space-y-4">
                  {author.papers.map((paper: any) => (
                    <Link
                      key={paper.id}
                      to={`/papers/${paper.id}`}
                      className="block p-5 rounded-xl border border-slate-100 bg-slate-50 hover:bg-white hover:border-red-200 hover:shadow-md transition-all group"
                    >
                      <div className="flex justify-between items-start gap-4">
                        <div className="flex-1">
                          <h3 className="font-bold text-slate-800 group-hover:text-red-600 transition-colors line-clamp-2 mb-2">
                            {paper.title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-3 text-sm text-slate-500">
                            <span className="flex items-center gap-1.5">
                              <Calendar size={14} /> {paper.year || "N/A"}
                            </span>
                            <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                            <span className="truncate max-w-[200px] md:max-w-md">
                              {paper.authors_list?.join(", ")}
                            </span>
                          </div>
                        </div>

                        {paper.cluster_label && (
                          <div className="shrink-0 hidden sm:block">
                            <span className="bg-yellow-50 text-yellow-700 border border-yellow-100 px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap">
                              {paper.cluster_label.split(":")[1] ||
                                paper.cluster_label}
                            </span>
                          </div>
                        )}

                        <ExternalLink
                          size={18}
                          className="text-slate-300 group-hover:text-red-500 shrink-0 mt-1"
                        />
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  No papers found for this author.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
