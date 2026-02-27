import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import HomePage from "@/pages/HomePage";
import ResultsPage from "@/pages/ResultsPage";
import AdminPage from "@/pages/AdminPage";
import YearbookDetailPage from "@/pages/YearbookDetailPage";
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/results" element={<ResultsPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/yearbook/:identifier" element={<YearbookDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" theme="dark" />
    </div>
  );
}

export default App;