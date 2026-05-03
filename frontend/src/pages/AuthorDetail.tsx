import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { BookOpen, ChevronLeft } from "lucide-react";
import api from "../services/api";
import AuthorProfileHeader from "../components/AuthorProfileHeader";
import TopicRadarChart from "../components/TopicRadarChart";
import PaperListCard from "../components/PaperListCard";

export default function AuthorDetail() {
  const { id } = useParams();
  const [author, setAuthor] = useState<any>(null);
  const [papers, setPapers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [authorRes, papersRes] = await Promise.all([
          api.get(`/authors/${id}/`),
          api.get(`/papers/?author_id=${id}`),
        ]);

        setAuthor(authorRes.data);

        if (papersRes.data && papersRes.data.data) {
          setPapers(papersRes.data.data);
        } else if (Array.isArray(papersRes.data)) {
          setPapers(papersRes.data);
        }
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
              // distribution_chart
              topicProfile={author.distribution_chart}
            />
          </div>

          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-200">
              <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2 mb-6">
                <BookOpen className="text-red-600" /> Published Papers
              </h2>

              {/* State papers */}
              {papers.length > 0 ? (
                <div className="space-y-4">
                  {papers.map((paper: any) => (
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
