import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, ExternalLink, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import Masonry from "react-masonry-css";
import { motion } from "framer-motion";

const ResultsPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { results, totalCompared, processingTime } = location.state || {
    results: [],
    totalCompared: 0,
    processingTime: 0,
  };

  if (!results || results.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-xl text-[#A1A1AA] mb-4">No results found</p>
          <Button
            onClick={() => navigate("/")}
            className="bg-[#00FF94] text-black hover:bg-[#00CC76] font-bold"
            data-testid="back-home-button"
          >
            Back to Home
          </Button>
        </div>
      </div>
    );
  }

  const breakpointColumns = {
    default: 4,
    1536: 3,
    1024: 2,
    640: 1,
  };

  return (
    <div className="min-h-screen noise-texture">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-md sticky top-0 z-50 bg-[#050505]/80">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Button
              onClick={() => navigate("/")}
              variant="ghost"
              className="text-white hover:text-[#00FF94] hover:bg-white/10"
              data-testid="back-button"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              New Search
            </Button>
            <div className="flex items-center gap-4 text-sm" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
              <span className="text-[#A1A1AA]">
                {results.length} matches • {totalCompared.toLocaleString()} faces scanned
              </span>
              <span className="text-[#00FF94]">
                {processingTime.toFixed(2)}s
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-[1800px] mx-auto px-6 py-12">
        {/* Title */}
        <div className="mb-12">
          <h1 
            className="text-4xl md:text-5xl font-bold mb-4"
            style={{ fontFamily: 'Unbounded, sans-serif' }}
          >
            Your <span className="text-[#00FF94]">Doppelgängers</span>
          </h1>
          <p className="text-lg text-[#A1A1AA]">
            Ranked by facial similarity from yearbook archives
          </p>
        </div>

        {/* Results Grid */}
        <Masonry
          breakpointCols={breakpointColumns}
          className="masonry-grid"
          columnClassName="masonry-grid-column"
        >
          {results.map((result, index) => (
            <motion.div
              key={result.face_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.05 }}
              className="group"
            >
              <div
                className="
                  bg-white/5 backdrop-blur-xl border border-white/10 
                  rounded-xl overflow-hidden hover:border-[#00FF94]/50 
                  transition-all duration-300 relative
                "
                data-testid={`result-card-${index}`}
              >
                {/* Image */}
                <div className="relative overflow-hidden aspect-[3/4] bg-[#0A0A0A]">
                  <img
                    src={result.thumbnail_url || "https://images.unsplash.com/photo-1542850083-aff0f80c1646?w=400"}
                    alt={result.name || "Match"}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  
                  {/* Similarity Badge */}
                  <div className="absolute top-3 right-3">
                    <div className="bg-[#00FF94] text-black px-3 py-1.5 rounded-full flex items-center gap-1.5 font-bold">
                      <TrendingUp className="w-3.5 h-3.5" />
                      <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                        {result.similarity_score.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* Rank Badge */}
                  {index < 10 && (
                    <div className="absolute top-3 left-3">
                      <div className="bg-black/80 backdrop-blur-sm text-white px-2.5 py-1 rounded-full text-xs font-bold border border-white/20">
                        #{index + 1}
                      </div>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-4">
                  <h3 className="font-bold text-lg mb-1">
                    {result.name || "Unknown"}
                  </h3>
                  <p className="text-sm text-[#A1A1AA] mb-2">
                    {result.school || "School Unknown"}
                  </p>
                  <p 
                    className="text-xs text-[#6366F1] mb-3" 
                    style={{ fontFamily: 'JetBrains Mono, monospace' }}
                  >
                    Class of {result.year || "N/A"}
                  </p>

                  {/* View Original Link */}
                  <a
                    href={result.page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="
                      inline-flex items-center gap-2 text-sm 
                      text-[#00FF94] hover:text-[#00CC76] 
                      transition-colors group/link
                    "
                    data-testid={`view-original-${index}`}
                  >
                    <span>View Original</span>
                    <ExternalLink className="w-3.5 h-3.5 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
                  </a>
                </div>
              </div>
            </motion.div>
          ))}
        </Masonry>
      </div>
    </div>
  );
};

export default ResultsPage;