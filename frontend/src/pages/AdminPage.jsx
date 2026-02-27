import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import {
  Search,
  Database,
  ArrowLeft,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminPage = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("yearbook high school");
  const [yearStart, setYearStart] = useState(2000);
  const [yearEnd, setYearEnd] = useState(2015);
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [scrapingStatus, setScrapingStatus] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [yearbooks, setYearbooks] = useState([]);
  const [activeTab, setActiveTab] = useState("search");

  useEffect(() => {
    fetchScrapingStatus();
    fetchJobs();
    fetchYearbooks();
    
    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchScrapingStatus();
      fetchJobs();
      fetchYearbooks();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchScrapingStatus = async () => {
    try {
      const response = await axios.get(`${API}/scraper/status`);
      setScrapingStatus(response.data);
    } catch (error) {
      console.error("Error fetching status:", error);
    }
  };

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API}/scraper/jobs?limit=10`);
      setJobs(response.data.jobs || []);
    } catch (error) {
      console.error("Error fetching jobs:", error);
    }
  };

  const fetchYearbooks = async () => {
    try {
      const response = await axios.get(`${API}/yearbooks?limit=20`);
      setYearbooks(response.data.yearbooks || []);
    } catch (error) {
      console.error("Error fetching yearbooks:", error);
    }
  };

  const handleSearch = async () => {
    setSearching(true);
    try {
      const response = await axios.get(`${API}/scraper/search-yearbooks`, {
        params: {
          query: searchQuery,
          year_start: yearStart,
          year_end: yearEnd,
          limit: 50,
        },
      });
      setSearchResults(response.data.results || []);
      toast.success(`Found ${response.data.count} yearbooks`);
    } catch (error) {
      toast.error("Failed to search yearbooks");
    } finally {
      setSearching(false);
    }
  };

  const startScraping = async (identifier, maxPages = null) => {
    try {
      await axios.post(`${API}/scraper/start`, null, {
        params: {
          identifier,
          max_pages: maxPages,
          priority: 5,
        },
      });
      toast.success(`Started scraping ${identifier}`);
      fetchScrapingStatus();
      fetchJobs();
    } catch (error) {
      toast.error("Failed to start scraping");
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="w-4 h-4 text-[#00FF94]" />;
      case "failed":
      case "error":
        return <XCircle className="w-4 h-4 text-red-500" />;
      case "processing":
        return <Loader2 className="w-4 h-4 text-[#6366F1] animate-spin" />;
      case "queued":
        return <Clock className="w-4 h-4 text-[#A1A1AA]" />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen noise-texture">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                onClick={() => navigate("/")}
                variant="ghost"
                className="text-white hover:text-[#00FF94] hover:bg-white/10"
                data-testid="back-home-button"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Home
              </Button>
              <div>
                <h1 className="text-2xl font-bold" style={{ fontFamily: 'Unbounded, sans-serif' }}>
                  <span className="text-[#00FF94]">Admin</span> Dashboard
                </h1>
                <p className="text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  Scraper Management
                </p>
              </div>
            </div>
            {scrapingStatus && (
              <div className="bg-white/5 border border-white/10 rounded-full px-4 py-2">
                <div className="flex items-center gap-4 text-sm" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  <span className="text-[#00FF94]">
                    {scrapingStatus.completed} completed
                  </span>
                  <span className="text-[#6366F1]">
                    {scrapingStatus.processing} processing
                  </span>
                  <span className="text-[#A1A1AA]">
                    {scrapingStatus.queued} queued
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Tabs */}
        <div className="flex gap-4 mb-8">
          {["search", "jobs", "yearbooks"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                px-6 py-3 rounded-lg font-semibold capitalize transition-all
                ${
                  activeTab === tab
                    ? "bg-[#00FF94] text-black"
                    : "bg-white/5 text-white hover:bg-white/10"
                }
              `}
              data-testid={`tab-${tab}`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Search Tab */}
        {activeTab === "search" && (
          <div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-6 mb-6">
              <h2 className="text-xl font-bold mb-4" style={{ fontFamily: 'Unbounded, sans-serif' }}>
                Search Archive.org Yearbooks
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search query"
                  className="md:col-span-2 bg-white/5 border-white/10 text-white"
                  data-testid="search-query-input"
                />
                <Input
                  type="number"
                  value={yearStart}
                  onChange={(e) => setYearStart(parseInt(e.target.value))}
                  placeholder="Start year"
                  className="bg-white/5 border-white/10 text-white"
                />
                <Input
                  type="number"
                  value={yearEnd}
                  onChange={(e) => setYearEnd(parseInt(e.target.value))}
                  placeholder="End year"
                  className="bg-white/5 border-white/10 text-white"
                />
              </div>
              <Button
                onClick={handleSearch}
                disabled={searching}
                className="bg-[#00FF94] text-black hover:bg-[#00CC76] font-bold"
                data-testid="search-button"
              >
                {searching ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Search className="w-4 h-4 mr-2" />
                )}
                Search
              </Button>
            </div>

            {/* Search Results */}
            <div className="grid grid-cols-1 gap-4">
              {searchResults.map((result, index) => (
                <div
                  key={index}
                  className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-[#00FF94]/50 transition-colors"
                  data-testid={`search-result-${index}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-bold text-lg mb-2">{result.title}</h3>
                      <div className="flex flex-wrap gap-4 text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                        <span>Year: {result.year || 'N/A'}</span>
                        <span>Creator: {result.creator || 'Unknown'}</span>
                        <span>Downloads: {result.downloads}</span>
                      </div>
                      {result.description && (
                        <p className="text-sm text-[#A1A1AA] mt-2 line-clamp-2">
                          {result.description}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <a
                        href={`https://archive.org/details/${result.identifier}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                      <Button
                        onClick={() => startScraping(result.identifier, 10)}
                        size="sm"
                        className="bg-[#00FF94] text-black hover:bg-[#00CC76]"
                        data-testid={`scrape-button-${index}`}
                      >
                        <Play className="w-4 h-4 mr-1" />
                        Scrape (10 pages)
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Jobs Tab */}
        {activeTab === "jobs" && (
          <div>
            <h2 className="text-2xl font-bold mb-6" style={{ fontFamily: 'Unbounded, sans-serif' }}>
              Scraping Jobs
            </h2>
            <div className="grid grid-cols-1 gap-4">
              {jobs.map((job, index) => (
                <div
                  key={index}
                  className="bg-white/5 border border-white/10 rounded-xl p-4"
                  data-testid={`job-${index}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(job.status)}
                      <span className="font-bold">{job.identifier}</span>
                    </div>
                    <span
                      className="text-sm px-3 py-1 rounded-full capitalize"
                      style={{
                        background:
                          job.status === "completed"
                            ? "rgba(0, 255, 148, 0.2)"
                            : job.status === "failed"
                            ? "rgba(239, 68, 68, 0.2)"
                            : "rgba(99, 102, 241, 0.2)",
                      }}
                    >
                      {job.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    <div>
                      Faces: <span className="text-[#00FF94]">{job.faces_found || 0}</span>
                    </div>
                    <div>
                      Pages: <span className="text-[#6366F1]">{job.pages_processed || 0}</span>
                    </div>
                    <div>
                      Priority: {job.priority}
                    </div>
                  </div>
                  {job.error && (
                    <p className="text-sm text-red-400 mt-2">{job.error}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Yearbooks Tab */}
        {activeTab === "yearbooks" && (
          <div>
            <h2 className="text-2xl font-bold mb-6" style={{ fontFamily: 'Unbounded, sans-serif' }}>
              Yearbooks Database
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {yearbooks.map((yearbook, index) => (
                <div
                  key={index}
                  className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-[#00FF94]/50 transition-colors"
                  data-testid={`yearbook-${index}`}
                  onClick={() => navigate(`/yearbook/${yearbook.identifier}`)}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="flex items-start justify-between mb-3">
                    <h3 className="font-bold text-lg flex-1">{yearbook.title}</h3>
                    {getStatusIcon(yearbook.scraping_status)}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    <div>Year: {yearbook.year || 'N/A'}</div>
                    <div>Faces: <span className="text-[#00FF94]">{yearbook.faces_extracted || 0}</span></div>
                    <div>Pages: {yearbook.num_pages || 0}</div>
                    <div>Status: <span className="capitalize">{yearbook.scraping_status}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;