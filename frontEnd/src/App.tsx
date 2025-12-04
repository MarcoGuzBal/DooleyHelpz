// import { useState } from "react";
// import "./index.css";
// import { onAuthStateChanged } from "firebase/auth";
// import type { User } from "firebase/auth";
// import { auth } from "./firebase";
import { Routes, Route } from "react-router-dom";

import AuthProvider from "./utils/AuthProvider";
//import RequireAuth from "./utils/RequireAuth";
import HomePage from "./pages/HomePage";
import RegisterPage from "./pages/RegisterPage";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
//import ProtectedRoute from "./components/ProtectedRoute";
import DropTranscript from "./components/DropTranscript";
import PreferencesPage from "./pages/PreferencesPage";
import ScheduleBuilderPage from "./pages/ScheduleBuilderPage";
// function Protected() { return <Outlet /> }

export default function App() {
// import ScheduleBattle from "./pages/ScheduleBattle";

  // Will work on logout later
  // async function handleLogout() {
  //   await signOut(auth); // clear Firebase session
  //   navigate("/login");
  // }

  
  return (   
    <AuthProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<DashboardPage />}/>
          <Route path="/droptranscript" element={<DropTranscript />} />
          <Route path="/preferences" element={<PreferencesPage />} />
          <Route path="/schedule-builder" element={<ScheduleBuilderPage />} />
          
          {/* <Route element={<RequireAuth><Protected /></RequireAuth>}>
            <Route path="/dashboard" element={<DashboardPage />}/>
            <Route path="/droptranscript" element={<DropTranscript />} />
            <Route path="/preferences" element={<PreferencesPage />} />
          </Route> */}
          {/* wildcard for 404s */}
          <Route path="*" element={<h1>Not found</h1>} />
        </Routes>
    </AuthProvider>   
  );
}
