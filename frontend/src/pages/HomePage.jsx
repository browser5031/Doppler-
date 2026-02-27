import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import { toast } from "sonner";
import { Upload, Scan, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const HomePage = () => {
  const [uploading, setUploading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stats, setStats] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchStats();
    seedDatabase();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error("Error fetching stats:", error);
    }
  };

  const seedDatabase = async () => {
    try {
      await axios.post(`${API}/seed-database`);
    } catch (error) {
      console.error("Error seeding database:", error);
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploading(true);
    setProgress(0);

    try {
      setTimeout(() => setProgress(30), 200);

      const formData = new FormData();
      formData.append("file", file);

      setProgress(50);
      setScanning(true);

      const response = await axios.post(`${API}/upload-compare`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        params: {
          top_n: 100,
        },
      });

      setProgress(100);

      setTimeout(() => {
        navigate("/results", { 
          state: { 
            results: response.data.results,
            totalCompared: response.data.total_faces_compared,
            processingTime: response.data.processing_time 
          } 
        });
      }, 500);

    } catch (error) {
      console.error("Error uploading file:", error);
      const errorMessage = error.response?.data?.detail || "Failed to process image. Please try again.";
      toast.error(errorMessage);
      setUploading(false);
      setScanning(false);
      setProgress(0);
    }
  }, [navigate]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".png", ".jpg", ".jpeg", ".webp"],
    },
    multiple: false,
    disabled: uploading,
  });

  return (
    <div className="min-h-screen noise-texture">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gradient" style={{ fontFamily: 'Unbounded, sans-serif' }}>
                DOPPELGÄNGER
              </h1>
              <p className="text-sm text-[#A1A1AA] mt-1" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                Archive Face Recognition System
              </p>
            </div>
            {stats && (
              <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-full px-4 py-2">
                <Database className="w-4 h-4 text-[#00FF94]" />
                <span className="text-sm" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                  {stats.total_faces.toLocaleString()} faces indexed
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h2 
            className="text-5xl md:text-6xl lg:text-7xl font-bold mb-6"
            style={{ fontFamily: 'Unbounded, sans-serif', lineHeight: '1.1' }}
          >
            Find Your
            <span className="block text-[#00FF94] mt-2">Historic Twin</span>
          </h2>
          <p className="text-lg md:text-xl text-[#A1A1AA] max-w-2xl mx-auto">
            Upload your photo and discover your doppelgänger in thousands of yearbook archives from 2000-2015
          </p>
        </div>

        {/* Upload Area */}
        <div className="max-w-2xl mx-auto">
          <div
            {...getRootProps()}
            data-testid="upload-dropzone"
            className={`
              relative border-2 border-dashed rounded-3xl p-16 
              transition-all duration-300 cursor-pointer
              bg-white/5 backdrop-blur-xl
              ${
                isDragActive
                  ? "border-[#00FF94] bg-[#00FF94]/10 glow-primary"
                  : "border-white/20 hover:border-[#00FF94]/50 hover:bg-white/10"
              }
              ${uploading ? "pointer-events-none opacity-60" : ""}
            `}
          >
            <input {...getInputProps()} />
            
            {scanning && <div className="scanner-line" />}
            
            <div className="flex flex-col items-center gap-6">
              {!uploading ? (
                <>
                  <div className="w-20 h-20 rounded-full bg-[#00FF94]/20 flex items-center justify-center">
                    <Upload className="w-10 h-10 text-[#00FF94]" />
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-semibold mb-2">
                      {isDragActive ? "Drop your photo here" : "Upload Your Photo"}
                    </p>
                    <p className="text-sm text-[#A1A1AA]">
                      Drag & drop or click to browse • JPG, PNG, WEBP
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-20 h-20 rounded-full bg-[#00FF94]/20 flex items-center justify-center biometric-scanner">
                    <Scan className="w-10 h-10 text-[#00FF94] animate-pulse" />
                  </div>
                  <div className="text-center w-full">
                    <p className="text-xl font-semibold mb-4" style={{ fontFamily: 'Unbounded, sans-serif' }}>
                      {scanning ? "Scanning Face Biometrics..." : "Processing Image..."}
                    </p>
                    <Progress value={progress} className="w-full h-2" />
                    <p className="text-sm text-[#A1A1AA] mt-2" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                      {progress}% complete
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="mt-8 text-center text-sm text-[#A1A1AA]">
            <p>✓ Your photo is processed securely and not stored</p>
            <p>✓ Searching across high schools, colleges, and universities (2000-2015)</p>
          </div>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mt-20 max-w-5xl mx-auto">
          <div className="bg-white/5 border border-white/10 rounded-xl p-6 backdrop-blur-xl">
            <div className="w-12 h-12 rounded-lg bg-[#00FF94]/20 flex items-center justify-center mb-4">
              <Scan className="w-6 h-6 text-[#00FF94]" />
            </div>
            <h3 className="text-lg font-bold mb-2" style={{ fontFamily: 'Unbounded, sans-serif' }}>
              Advanced Face Recognition
            </h3>
            <p className="text-sm text-[#A1A1AA]">
              Using state-of-the-art deep learning to find your closest matches
            </p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6 backdrop-blur-xl">
            <div className="w-12 h-12 rounded-lg bg-[#6366F1]/20 flex items-center justify-center mb-4">
              <Database className="w-6 h-6 text-[#6366F1]" />
            </div>
            <h3 className="text-lg font-bold mb-2" style={{ fontFamily: 'Unbounded, sans-serif' }}>
              Vast Archive Database
            </h3>
            <p className="text-sm text-[#A1A1AA]">
              Sourced from Archive.org's extensive yearbook collection
            </p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl p-6 backdrop-blur-xl">
            <div className="w-12 h-12 rounded-lg bg-[#00FF94]/20 flex items-center justify-center mb-4">
              <Upload className="w-6 h-6 text-[#00FF94]" />
            </div>
            <h3 className="text-lg font-bold mb-2" style={{ fontFamily: 'Unbounded, sans-serif' }}>
              Privacy First
            </h3>
            <p className="text-sm text-[#A1A1AA]">
              Your uploaded photo is never stored, only processed temporarily
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;