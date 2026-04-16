import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { BookOpen, Tag, ChevronLeft } from "lucide-react";
import api from "../services/api";
import PaperHeader from "../components/PaperHeader";
import PaperMetadata from "../components/PaperMetadata";
import PaperTopicRadar from "../components/PaperTopicRadar";

export default function PaperDetail() {
  const { id } = useParams();
  const [paper, setPaper] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [topicMap, setTopicMap] = useState<Record<number, string>>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [paperRes, topicRes] = await Promise.all([
          api.get(`/papers/${id}/`),
          api.get("/analytics/topics/"),
        ]);

        setPaper(paperRes.data);

        const map: Record<number, string> = {};
        if (Array.isArray(topicRes.data)) {
          topicRes.data.forEach((topicStr: string) => {
            const match = topicStr.match(/(-?\d+)\s*:\s*(.+)/);
            if (match) {
              const topicId = parseInt(match[1], 10);
              const topicName = match[2].trim();
              map[topicId] = topicName;
            }
          });
        }

        setTopicMap(map);
      } catch {
        console.error("Error fetching data:");
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

  if (!paper) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 text-slate-500">
        Paper not found.
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Back Button */}
        <Link
          to="/papers"
          className="inline-flex items-center text-slate-500 hover:text-red-600 transition-colors mb-4"
        >
          <ChevronLeft size={20} className="mr-1" /> Back
        </Link>

        {/* 1. Header Section */}
        <PaperHeader paper={paper} />

        {/* CONTENT GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Abstract & Tags */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-4">
                <BookOpen className="text-red-600" /> Abstract
              </h2>
              <p className="text-slate-600 leading-relaxed text-justify">
                {paper.abstract || "No abstract available for this paper."}
              </p>
            </div>

            {paper.predicted_multi_labels &&
              paper.predicted_multi_labels.length > 0 && (
                <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
                  <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2 mb-4">
                    <Tag className="text-red-600" /> Related Topics
                  </h2>
                  <div className="flex flex-wrap gap-2">
                    {paper.predicted_multi_labels.map(
                      (label: string, idx: number) => (
                        <span
                          key={idx}
                          className="bg-slate-100 text-slate-600 border border-slate-200 px-3 py-1.5 rounded-lg text-sm"
                        >
                          {label.split(":")[1] || label}
                        </span>
                      ),
                    )}
                  </div>
                </div>
              )}
          </div>

          {/* Right Column: Radar & Meta */}
          <div className="space-y-6">
            {/* 2. Radar Chart */}
            <PaperTopicRadar
              distribution={paper.topic_distribution}
              topicMap={topicMap}
            />

            {/* 3. Meta Data */}
            <PaperMetadata
              venue={paper.venue}
              doi={paper.doi}
              url={paper.url}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
