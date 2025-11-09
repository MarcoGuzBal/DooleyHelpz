import { useState } from 'react'
import './index.css'
import React from "react";
import { onAuthStateChanged, signOut} from "firebase/auth";
import type { User } from "firebase/auth";
import { auth } from "./firebase"
import { Routes, Route, useNavigate} from "react-router-dom";

import HomePage from "./pages/HomePage";
import RegisterPage from "./pages/RegisterPage";
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ProtectedRoute from "./components/ProtectedRoute";
import DropTranscript from "./components/DropTranscript";
import PreferencesPage from './pages/PreferencesPage';

export default function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  React.useEffect(() => {
    // Firebase tells us when someone logs in or out
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setCurrentUser(user); // user object or null
      setLoading(false); // stop showing the loading screen
    }, (error) => {
      console.error("Auth state change error:", error);
      setLoading(false);
    });
    return () => unsubscribe(); // cleanup when component unmounts
  }, []);

  // Will work on logout later
  // async function handleLogout() {
  //   await signOut(auth); // clear Firebase session
  //   navigate("/login");
  // }

  return (
    <div>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={
            <ProtectedRoute isAuthed={!!currentUser}>
              <DashboardPage />
            </ProtectedRoute>
            }
          />
          <Route path="/droptranscript" element={<DropTranscript />} />
          <Route path="/preferences" element={<PreferencesPage />} />

          {/* wildcard for 404s */}
          <Route path="*" element={<h1>Not found</h1>} />
        </Routes>
    </div>
  )
}


