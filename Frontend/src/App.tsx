import { useState } from 'react'
import './index.css'
import HomePage from "./pages/HomePage";
import { Routes, Route, Link } from "react-router-dom";
import TranscriptUploadPage from "./pages/TranscriptUploadPage";


function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/transcript-upload" element={<TranscriptUploadPage />} />
    </Routes>
  );
}

export default App
