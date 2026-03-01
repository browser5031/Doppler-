import React, { useState, useRef } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [topN, setTopN] = useState(10);
  const [stats, setStats] = useState(null);
  const fileInputRef = useRef(null);

  // Fetch stats on mount
  React.useEffect(() => {
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
      
      // Create preview
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
            {stats && (
              <div className="text-right">
                <div className="text-2xl font-bold text-indigo-600">
                  {stats.total_faces.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">faces in database</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Upload Section */}
        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800">
            Upload Your Photo
          </h2>
          
          <div className="space-y-6">
            {/* File Input */}
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

            {/* Preview */}
            {preview && (
              <div className="flex flex-col items-center">
                <img
                  src={preview}
                  alt="Preview"
                  className="max-w-xs rounded-lg shadow-md mb-4"
                />
                
                {/* Top N Selector */}
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

                {/* Action Buttons */}
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

            {/* Error Message */}
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
                    {/* Rank Badge */}
                    <div className="flex items-center justify-between mb-3">
                      <span className="bg-indigo-100 text-indigo-800 text-xs font-semibold px-3 py-1 rounded-full">
                        #{index + 1}
                      </span>
                      <span className="text-lg font-bold text-green-600">
                        {match.similarity_score.toFixed(1)}% Match
                      </span>
                    </div>

                    {/* Thumbnail */}
                    {match.thumbnail_url && (
                      <img
                        src={match.thumbnail_url}
                        alt={`Match ${index + 1}`}
                        className="w-full h-48 object-cover rounded-lg mb-3"
                      />
                    )}

                    {/* Info */}
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
