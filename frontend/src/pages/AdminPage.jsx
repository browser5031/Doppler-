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
  const [defaultPageLimit, setDefaultPageLimit] = useState(null); // null = all pages
  const [stuckTasks, setStuckTasks] = useState({ stuck_processing: [], stuck_queued: [], total_stuck: 0 });
  const [recoveryStats, setRecoveryStats] = useState({});

  useEffect(() => {
    fetchScrapingStatus();
    fetchJobs();
    fetchYearbooks();
    fetchStuckTasks();
    fetchRecoveryStats();
    
    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchScrapingStatus();
      fetchJobs();
      fetchYearbooks();
      fetchStuckTasks();
      fetchRecoveryStats();
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
      const response = await axios.get(`${API}/scraper/progress?limit=10`);
      setJobs(response.data.yearbooks || []);
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

  const fetchStuckTasks = async () => {
    try {
      const response = await axios.get(`${API}/recovery/stuck-tasks`);
      setStuckTasks(response.data);
    } catch (error) {
      console.error("Error fetching stuck tasks:", error);
    }
  };

  const fetchRecoveryStats = async () => {
    try {
      const response = await axios.get(`${API}/recovery/stats`);
      setRecoveryStats(response.data);
    } catch (error) {
      console.error("Error fetching recovery stats:", error);
    }
  };

  const resetAllStuckTasks = async () => {
    try {
      const response = await axios.post(`${API}/recovery/reset-all-stuck`);
      toast.success(`Reset ${response.data.reset_count} stuck tasks!`);
      fetchStuckTasks();
      fetchRecoveryStats();
      fetchJobs();
    } catch (error) {
      toast.error("Failed to reset stuck tasks");
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
      const errorMsg = error.response?.data?.detail || "Failed to start scraping";
      toast.error(errorMsg);
      console.error("Scraping error:", error);
    }
  };

  const startBulkScraping = async () => {
    if (searchResults.length === 0) {
      toast.error("No search results to scrape");
      return;
    }

    const identifiers = searchResults.map(r => r.identifier);
    
    try {
      const response = await axios.post(`${API}/scraper/batch-start`, identifiers, {
        params: {
          max_pages: defaultPageLimit,
        },
      });
      toast.success(`Started scraping ${identifiers.length} yearbooks!`);
      fetchScrapingStatus();
      fetchJobs();
    } catch (error) {
      toast.error("Failed to start bulk scraping");
    }
  };

  const autoDiscover = async () => {
    try {
      const response = await axios.post(`${API}/scraper/auto-discover`, null, {
        params: {
          query: "high school yearbook",
          year_start: 2000,
          year_end: 2015,
          limit: 200,
          max_pages_per_book: defaultPageLimit || 50,
        },
      });
      toast.success(response.data.message);
      fetchScrapingStatus();
    } catch (error) {
      toast.error("Failed to auto-discover");
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
          {["search", "jobs", "yearbooks", "recovery"].map((tab) => (
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
                ${tab === "recovery" && stuckTasks.total_stuck > 0 ? "relative" : ""}
              `}
              data-testid={`tab-${tab}`}
            >
              {tab}
              {tab === "recovery" && stuckTasks.total_stuck > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                  {stuckTasks.total_stuck}
                </span>
              )}
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
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
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
                <Input
                  type="number"
                  value={defaultPageLimit || ''}
                  onChange={(e) => setDefaultPageLimit(e.target.value ? parseInt(e.target.value) : null)}
                  placeholder="All pages"
                  className="bg-white/5 border-white/10 text-white"
                />
              </div>
              <div className="flex items-center gap-4">
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
                {searchResults.length > 0 && (
                  <Button
                    onClick={startBulkScraping}
                    className="bg-[#6366F1] text-white hover:bg-[#5558E3] font-bold"
                    data-testid="bulk-scrape-button"
                  >
                    <Play className="w-4 h-4 mr-2" />
                    Scrape All {searchResults.length} Results
                  </Button>
                )}
                <Button
                  onClick={autoDiscover}
                  variant="outline"
                  className="border-[#00FF94] text-[#00FF94] hover:bg-[#00FF94] hover:text-black font-bold"
                  data-testid="auto-discover-button"
                >
                  🚀 Auto-Discover & Scrape 200
                </Button>
                <span className="text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  Page limit: {defaultPageLimit ? `${defaultPageLimit} pages` : 'All pages'}
                </span>
              </div>
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
                    <div className="flex gap-2 ml-4">
                      <a
                        href={`https://archive.org/details/${result.identifier}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                      <Button
                        onClick={() => startScraping(result.identifier, defaultPageLimit)}
                        size="sm"
                        className="bg-[#00FF94] text-black hover:bg-[#00CC76] whitespace-nowrap"
                        data-testid={`scrape-button-${index}`}
                      >
                        <Play className="w-4 h-4 mr-1" />
                        {defaultPageLimit ? `Scrape (${defaultPageLimit} pages)` : 'Scrape All'}
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
                      {getStatusIcon(job.scraping_status)}
                      <span className="font-bold">{job.identifier}</span>
                    </div>
                    <span
                      className="text-sm px-3 py-1 rounded-full capitalize"
                      style={{
                        background:
                          job.scraping_status === "completed"
                            ? "rgba(0, 255, 148, 0.2)"
                            : job.scraping_status === "failed"
                            ? "rgba(239, 68, 68, 0.2)"
                            : "rgba(99, 102, 241, 0.2)",
                      }}
                    >
                      {job.scraping_status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    <div>
                      Faces: <span className="text-[#00FF94]">{job.faces_extracted || 0}</span>
                    </div>
                    <div>
                      Pages: <span className="text-[#6366F1]">{job.pages_processed || 0} / {job.total_pages || '?'}</span>
                    </div>
                    <div>
                      Year: {job.year || 'N/A'}
                    </div>
                  </div>
                  {job.progress_percent > 0 && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-[#A1A1AA] mb-1">
                        <span>Progress</span>
                        <span>{job.progress_percent}%</span>
                      </div>
                      <Progress value={job.progress_percent} className="h-2" />
                    </div>
                  )}
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

        {/* Recovery Tab */}
        {activeTab === "recovery" && (
          <div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-6 mb-6">
              <h2 className="text-xl font-bold mb-4" style={{ fontFamily: 'Unbounded, sans-serif' }}>
                Task Recovery System
              </h2>
              
              {/* Stats Overview */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <div className="text-2xl font-bold text-[#00FF94]">{recoveryStats.stuck_processing || 0}</div>
                  <div className="text-sm text-[#A1A1AA]">Stuck Processing</div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <div className="text-2xl font-bold text-[#FFA500]">{recoveryStats.stuck_queued || 0}</div>
                  <div className="text-sm text-[#A1A1AA]">Stuck Queued</div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <div className="text-2xl font-bold text-[#6366F1]">{recoveryStats.processing || 0}</div>
                  <div className="text-sm text-[#A1A1AA]">Currently Processing</div>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <div className="text-2xl font-bold text-red-500">{recoveryStats.failed || 0}</div>
                  <div className="text-sm text-[#A1A1AA]">Failed</div>
                </div>
              </div>

              {/* Action Button */}
              {stuckTasks.total_stuck > 0 && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 mb-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-bold text-red-400 mb-2">
                        ⚠️ {stuckTasks.total_stuck} Stuck Tasks Detected
                      </h3>
                      <p className="text-sm text-[#A1A1AA] mb-4">
                        These tasks have been stuck for over 30 minutes. Click below to reset them and restart processing.
                      </p>
                    </div>
                  </div>
                  <Button
                    onClick={resetAllStuckTasks}
                    className="w-full bg-red-500 hover:bg-red-600 text-white font-semibold"
                    data-testid="reset-stuck-tasks-button"
                  >
                    🔧 Reset All Stuck Tasks
                  </Button>
                </div>
              )}

              {stuckTasks.total_stuck === 0 && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-6 mb-6 text-center">
                  <CheckCircle2 className="w-12 h-12 text-[#00FF94] mx-auto mb-2" />
                  <h3 className="text-lg font-bold text-[#00FF94] mb-2">
                    ✅ No Stuck Tasks!
                  </h3>
                  <p className="text-sm text-[#A1A1AA]">
                    All tasks are progressing normally. Your scraper is running smoothly.
                  </p>
                </div>
              )}

              {/* Stuck Tasks List */}
              {stuckTasks.stuck_processing && stuckTasks.stuck_processing.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-bold mb-4 text-red-400">Stuck Processing ({stuckTasks.stuck_processing.length})</h3>
                  <div className="space-y-3">
                    {stuckTasks.stuck_processing.map((task, idx) => (
                      <div
                        key={idx}
                        className="bg-white/5 border border-red-500/30 rounded-lg p-4"
                      >
                        <div className="font-bold text-white mb-2">{task.title || task.identifier}</div>
                        <div className="grid grid-cols-3 gap-2 text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                          <div>Pages: {task.pages_processed || 0}</div>
                          <div>Faces: {task.faces_extracted || 0}</div>
                          <div>Started: {new Date(task.started_at).toLocaleTimeString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {stuckTasks.stuck_queued && stuckTasks.stuck_queued.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold mb-4 text-[#FFA500]">Stuck Queued ({stuckTasks.stuck_queued.length})</h3>
                  <div className="space-y-3">
                    {stuckTasks.stuck_queued.map((task, idx) => (
                      <div
                        key={idx}
                        className="bg-white/5 border border-[#FFA500]/30 rounded-lg p-4"
                      >
                        <div className="font-bold text-white mb-2">{task.title || task.identifier}</div>
                        <div className="text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                          Updated: {new Date(task.updated_at || task.created_at).toLocaleTimeString()}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Instructions */}
            <div className="bg-white/5 border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold mb-4">How to Use Recovery System</h3>
              <div className="space-y-3 text-sm text-[#A1A1AA]" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                <div>
                  <span className="text-[#00FF94]">1.</span> The system automatically detects tasks stuck for over 30 minutes
                </div>
                <div>
                  <span className="text-[#00FF94]">2.</span> Click "Reset All Stuck Tasks" to move them back to queued status
                </div>
                <div>
                  <span className="text-[#00FF94]">3.</span> Restart scraping from the "Search" tab or use the auto-discover feature
                </div>
                <div>
                  <span className="text-[#00FF94]">4.</span> Monitor progress in the "Jobs" tab
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;