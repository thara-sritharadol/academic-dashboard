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
import AuthorProfileHeader from "../components/AuthorProfileHeader";
import TopicRadarChart from "../components/TopicRadarChart";
import PaperListCard from "../components/PaperListCard";

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
        <AuthorProfileHeader author={author} />

        {/* CONTENT GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <TopicRadarChart
              topicProfile={author.topic_profile}
              topicMap={topicMap}
            />
          </div>

          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-6">
                <BookOpen className="text-red-600" /> Published Papers
              </h2>

              {author.papers && author.papers.length > 0 ? (
                <div className="space-y-4">
                  {author.papers.map((paper: any) => (
                    <PaperListCard key={paper.id} paper={paper} />
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
