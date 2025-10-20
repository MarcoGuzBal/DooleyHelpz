import { useState } from 'react'
import './index.css'
import HomePage from "./pages/HomePage";
import { Routes, Route, Link } from "react-router-dom";


function App() {

  return (
    <div>
        <Routes>
          <Route path="/" element={<HomePage />} />
          {/* wildcard for 404s */}
          <Route path="*" element={<h1>Not found</h1>} />
        </Routes>
    </div>
  )
}

export default App
