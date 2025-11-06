import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage"
import RegisterPage from "./pages/RegisterPage";
import TranscriptParserPage from "./pages/TranscriptParserPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
      <Route path="transcript" element={<TranscriptParserPage />} />
    </Routes>
  );
}
