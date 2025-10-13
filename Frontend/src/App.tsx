import { useState } from 'react'
import './index.css'
import HomePage from "./pages/HomePage";
import RegisterPage from "./pages/RegisterPage";
import { Routes, Route, Link } from "react-router-dom";
import LoginPage from './pages/LoginPage';


function App() {

  return (
    <div>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
          {/* wildcard for 404s */}
          <Route path="*" element={<h1>Not found</h1>} />
        </Routes>
    </div>
  )
}

export default App
