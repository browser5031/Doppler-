import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { ArrowLeft, ExternalLink, Users, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import Masonry from "react-masonry-css";
import { motion } from "framer-motion";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const YearbookDetailPage = () => {
  const { identifier } = useParams();
  const navigate = useNavigate();
  const [yearbook, setYearbook] = useState(null);
  const [faces, setFaces] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchYearbookDetails();
    fetchFaces();
  }, [identifier]);

  const fetchYearbookDetails = async () => {
    try {
      const response = await axios.get(`${API}/yearbooks?limit=1000`);
      const found = response.data.yearbooks.find(y => y.identifier === identifier);
      setYearbook(found);
    } catch (error) {
      console.error("Error fetching yearbook:", error);
    }
  };

  const fetchFaces = async () => {
    try {
      const response = await axios.get(`${API}/yearbooks/${identifier}/faces?limit=100`);
      setFaces(response.data.faces || []);
    } catch (error) {
      console.error("Error fetching faces:", error);
    } finally {
      setLoading(false);
    }
  };

  const breakpointColumns = {
    default: 4,
    1536: 3,
    1024: 2,
    640: 1,
  };

  if (loading || !yearbook) {
    return (
      <div className="min-h-screen flex items-center justify-center noise-texture">
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-[#00FF94] border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-[#A1A1AA]">Loading yearbook...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen noise-texture">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-md sticky top-0 z-50 bg-[#050505]/80">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Button
              onClick={() => navigate("/admin")}
              variant="ghost"
              className="text-white hover:text-[#00FF94] hover:bg-white/10"
              data-testid="back-button"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Admin
            </Button>
            <a
              href={yearbook.archive_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-[#00FF94] hover:text-[#00CC76] transition-colors"
            >
              <span>View on Archive.org</span>
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      </header>

      <div className="max-w-[1800px] mx-auto px-6 py-12">
        {/* Yearbook Info */}
        <div className="mb-12">
          <h1
            className="text-4xl md:text-5xl font-bold mb-4"
            style={{ fontFamily: 'Unbounded, sans-serif' }}
          >
            {yearbook.title}
          </h1>
          <div className="flex flex-wrap gap-6 text-lg text-[#A1A1AA]">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-[#6366F1]" />
              <span>Year: {yearbook.year || 'N/A'}</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-[#00FF94]" />
              <span>{faces.length} Faces Extracted</span>
            </div>
          </div>
          {yearbook.description && (
            <p className="text-[#A1A1AA] mt-4 max-w-3xl">
              {yearbook.description}
            </p>
          )}
        </div>

        {/* Faces Grid */}
        {faces.length > 0 ? (
          <>
            <h2
              className="text-2xl font-bold mb-6"
              style={{ fontFamily: 'Unbounded, sans-serif' }}
            >
              Extracted <span className="text-[#00FF94]">Faces</span>
            </h2>
            <Masonry
              breakpointCols={breakpointColumns}
              className="masonry-grid"
              columnClassName="masonry-grid-column"
            >
              {faces.map((face, index) => (
                <motion.div
                  key={face.face_id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: index * 0.02 }}
                  className="group"
                >
                  <div
                    className="
                      bg-white/5 backdrop-blur-xl border border-white/10 
                      rounded-xl overflow-hidden hover:border-[#00FF94]/50 
                      transition-all duration-300
                    "
                    data-testid={`face-card-${index}`}
                  >
                    {/* Image */}
                    <div className="relative overflow-hidden aspect-square bg-[#0A0A0A]">
                      {face.face_id ? (
                        <img
                          src={`${process.env.REACT_APP_BACKEND_URL}/api/thumbnail/${face.face_id}`}
                          alt={`Face from page ${face.page_num}`}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          onError={(e) => {
                            e.target.src = face.thumbnail_url || '';
                            if (!e.target.src) e.target.style.display = 'none';
                          }}
                        />
                      ) : face.thumbnail_url ? (
                        <img
                          src={face.thumbnail_url}
                          alt={`Face from page ${face.page_num}`}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-[#A1A1AA]">
                          <Users className="w-12 h-12" />
                        </div>
                      )}
                    </div>

                    {/* Info */}
                    <div className="p-3">
                      <p
                        className="text-xs text-[#A1A1AA] mb-2"
                        style={{ fontFamily: 'JetBrains Mono, monospace' }}
                      >
                        Page {face.page_num}
                      </p>
                      <a
                        href={face.page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm text-[#00FF94] hover:text-[#00CC76] transition-colors"
                        data-testid={`view-page-${index}`}
                      >
                        <span>View Page</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </motion.div>
              ))}
            </Masonry>
          </>
        ) : (
          <div className="text-center py-20">
            <Users className="w-16 h-16 text-[#A1A1AA] mx-auto mb-4" />
            <p className="text-xl text-[#A1A1AA]">
              No faces extracted yet. Start scraping to populate this yearbook.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default YearbookDetailPage;