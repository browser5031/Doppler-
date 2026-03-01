import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Admin Panel Component
function AdminPanel() {
  const [stats, setStats] = useState(null);
  const [scraperStatus, setScraperStatus] = useState(null);
  const [yearbooks, setYearbooks] = useState([]);
  const [searchQuery, setSearchQuery] = useState('high school yearbook');
  const [yearStart, setYearStart] = useState(2000);
  const [yearEnd, setYearEnd] = useState(2015);
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null);

  const refreshData = async () => {
    try {
      const [statsRes, statusRes, progressRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/stats`),
        fetch(`${BACKEND_URL}/api/scraper/status`),
        fetch(`${BACKEND_URL}/api/scraper/progress?limit=10`)
      ]);
      
      setStats(await statsRes.json());
      setScraperStatus(await statusRes.json());
      setYearbooks(await progressRes.json());
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  };

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handleSearchYearbooks = async () => {
    setSearching(true);
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/scraper/search-yearbooks?query=${encodeURIComponent(searchQuery)}&year_start=${yearStart}&year_end=${yearEnd}&limit=20`
      );
      const data = await response.json();
      setSearchResults(data);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setSearching(false);
    }
  };

  const handleStartScraping = async (identifier) => {
    try {
      await fetch(`${BACKEND_URL}/api/scraper/start?identifier=${identifier}&max_pages=0&priority=5`, {
        method: 'POST'
      });
      alert(`Started scraping ${identifier}`);
      refreshData();
    } catch (err) {
      alert('Failed to start scraping: ' + err.message);
    }
  };

  return (
    <div className="p-8">
      <h2 className="text-3xl font-bold mb-6">📊 Scraper Admin Panel</h2>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {stats && (
          <>
            <div className="bg-blue-100 p-6 rounded-lg">
              <div className="text-3xl font-bold text-blue-900">{stats.total_faces.toLocaleString()}</div>
              <div className="text-sm text-blue-700">Total Faces</div>
            </div>
            <div className="bg-green-100 p-6 rounded-lg">
              <div className="text-3xl font-bold text-green-900">{stats.total_yearbooks}</div>
              <div className="text-sm text-green-700">Total Yearbooks</div>
            </div>
          </>
        )}
        {scraperStatus && (
          <>
            <div className="bg-yellow-100 p-6 rounded-lg">
              <div className="text-3xl font-bold text-yellow-900">{scraperStatus.processing}</div>
              <div className="text-sm text-yellow-700">Processing</div>
            </div>
            <div className="bg-purple-100 p-6 rounded-lg">
              <div className="text-3xl font-bold text-purple-900">{scraperStatus.completed}</div>
              <div className="text-sm text-purple-700">Completed</div>
            </div>
          </>
        )}
      </div>

      {/* Search Yearbooks */}
      <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
        <h3 className="text-xl font-semibold mb-4">🔍 Search Archive.org for Yearbooks</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search query..."
            className="col-span-2 border border-gray-300 rounded-md px-4 py-2"
          />
          <input
            type="number"
            value={yearStart}
            onChange={(e) => setYearStart(parseInt(e.target.value))}
            placeholder="Year start"
            className="border border-gray-300 rounded-md px-4 py-2"
          />
          <input
            type="number"
            value={yearEnd}
            onChange={(e) => setYearEnd(parseInt(e.target.value))}
            placeholder="Year end"
            className="border border-gray-300 rounded-md px-4 py-2"
          />
        </div>
        <button
          onClick={handleSearchYearbooks}
          disabled={searching}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-semibold py-2 px-6 rounded-lg"
        >
          {searching ? 'Searching...' : 'Search Yearbooks'}
        </button>

        {searchResults && (
          <div className="mt-6">
            <h4 className="font-semibold mb-3">Found {searchResults.total} yearbooks:</h4>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {searchResults.results.map((yb) => (
                <div key={yb.identifier} className="border border-gray-200 rounded p-3 flex justify-between items-center">
                  <div>
                    <div className="font-medium">{yb.title}</div>
                    <div className="text-sm text-gray-600">{yb.identifier} • {yb.year || 'N/A'}</div>
                  </div>
                  <button
                    onClick={() => handleStartScraping(yb.identifier)}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded text-sm"
                  >
                    Start Scraping
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Yearbook Progress */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold">📚 Yearbook Processing Status</h3>
          <button
            onClick={refreshData}
            className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded text-sm"
          >
            Refresh
          </button>
        </div>
        
        {yearbooks.yearbooks && yearbooks.yearbooks.length > 0 ? (
          <div className="space-y-3">
            {yearbooks.yearbooks.map((yb) => (
              <div key={yb.identifier} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <div className="font-semibold">{yb.identifier}</div>
                    <div className="text-sm text-gray-600">
                      Status: <span className="font-medium">{yb.scraping_status}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-green-600">{yb.faces_extracted}</div>
                    <div className="text-xs text-gray-500">faces</div>
                  </div>
                </div>
                
                <div className="mt-2">
                  <div className="flex justify-between text-sm mb-1">
                    <span>Progress: {yb.pages_processed} / {yb.total_pages || '?'} pages</span>
                    <span>{yb.total_pages ? Math.round((yb.pages_processed / yb.total_pages) * 100) : 0}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{ width: `${yb.total_pages ? (yb.pages_processed / yb.total_pages) * 100 : 0}%` }}
                    ></div>
                  </div>
                </div>
                
                {yb.error_message && (
                  <div className="mt-2 text-sm text-red-600">Error: {yb.error_message}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            No yearbooks being processed. Search and start scraping above.
          </div>
        )}
      </div>
    </div>
  );
}

// Main App Component
function App() {
  const [view, setView] = useState('search'); // 'search' or 'admin'
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [topN, setTopN] = useState(10);
  const [stats, setStats] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/stats`)
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error('Error fetching stats:', err));
  }, []);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setError(null);
      setResults(null);
      
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a photo first');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('top_n', topN);

    try {
      const response = await fetch(`${BACKEND_URL}/api/upload-compare`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      setResults(data);
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Failed to process image. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreview(null);
    setResults(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                📚 Yearbook Face Finder
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Find your doppelganger in vintage yearbooks
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {stats && (
                <div className="text-right">
                  <div className="text-2xl font-bold text-indigo-600">
                    {stats.total_faces.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500">faces in database</div>
                </div>
              )}
              <button
                onClick={() => setView(view === 'search' ? 'admin' : 'search')}
                className="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium"
              >
                {view === 'search' ? '⚙️ Admin' : '🔍 Search'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {view === 'admin' ? (
          <AdminPanel />
        ) : (
          <>
            {/* Upload Section */}
            <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
              <h2 className="text-2xl font-semibold mb-6 text-gray-800">
                Upload Your Photo
              </h2>
              
              <div className="space-y-6">
                <div className="flex flex-col items-center">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="file-upload"
                  />
                  <label
                    htmlFor="file-upload"
                    className="cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-8 rounded-lg transition duration-200 inline-flex items-center"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    Choose Photo
                  </label>
                  <p className="text-sm text-gray-500 mt-2">
                    Upload a clear photo of your face
                  </p>
                </div>

                {preview && (
                  <div className="flex flex-col items-center">
                    <img
                      src={preview}
                      alt="Preview"
                      className="max-w-xs rounded-lg shadow-md mb-4"
                    />
                    
                    <div className="flex items-center space-x-4 mb-4">
                      <label className="text-sm font-medium text-gray-700">
                        Show top:
                      </label>
                      <select
                        value={topN}
                        onChange={(e) => setTopN(parseInt(e.target.value))}
                        className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        <option value="5">5 matches</option>
                        <option value="10">10 matches</option>
                        <option value="20">20 matches</option>
                        <option value="50">50 matches</option>
                        <option value="100">100 matches</option>
                      </select>
                    </div>

                    <div className="flex space-x-4">
                      <button
                        onClick={handleUpload}
                        disabled={loading}
                        className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold py-3 px-8 rounded-lg transition duration-200"
                      >
                        {loading ? (
                          <span className="flex items-center">
                            <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Finding Matches...
                          </span>
                        ) : (
                          '🔍 Find My Doppelganger'
                        )}
                      </button>
                      
                      <button
                        onClick={handleReset}
                        className="bg-gray-500 hover:bg-gray-600 text-white font-semibold py-3 px-8 rounded-lg transition duration-200"
                      >
                        Reset
                      </button>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                    <p className="font-medium">Error:</p>
                    <p className="text-sm">{error}</p>
                  </div>
                )}
              </div>
            </div>

            {/* Results Section */}
            {results && (
              <div className="bg-white rounded-lg shadow-lg p-8">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-2xl font-semibold text-gray-800">
                    Your Matches
                  </h2>
                  <div className="text-sm text-gray-600">
                    Compared against {results.total_faces_compared.toLocaleString()} faces
                    in {results.processing_time.toFixed(2)}s
                  </div>
                </div>

                {results.results.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    No matches found. Try a different photo or check back later when we have more faces in the database.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {results.results.map((match, index) => (
                      <div
                        key={match.face_id}
                        className="border border-gray-200 rounded-lg p-4 hover:shadow-lg transition duration-200"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span className="bg-indigo-100 text-indigo-800 text-xs font-semibold px-3 py-1 rounded-full">
                            #{index + 1}
                          </span>
                          <span className="text-lg font-bold text-green-600">
                            {match.similarity_score.toFixed(1)}% Match
                          </span>
                        </div>

                        {match.thumbnail_url && (
                          <img
                            src={match.thumbnail_url}
                            alt={`Match ${index + 1}`}
                            className="w-full h-48 object-cover rounded-lg mb-3"
                          />
                        )}

                        <div className="space-y-2 text-sm">
                          {match.name && (
                            <p className="font-semibold text-gray-800">
                              {match.name}
                            </p>
                          )}
                          {match.school && (
                            <p className="text-gray-600">
                              🏫 {match.school}
                            </p>
                          )}
                          {match.year && (
                            <p className="text-gray-600">
                              📅 Class of {match.year}
                            </p>
                          )}
                          {match.page_url && (
                            <a
                              href={match.page_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center text-indigo-600 hover:text-indigo-800 font-medium"
                            >
                              View Original Page
                              <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="text-center text-sm text-gray-500">
          <p>Powered by Emergent AI • Yearbook data from Archive.org</p>
        </div>
      </div>
    </div>
  );
}

export default App;
