import React from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "../firebase";

export default function DashboardPage() {
  const user = auth.currentUser;
  const navigate = useNavigate();

  // Logout function (optional)
  const handleLogout = () => {
    auth.signOut();
    navigate("/login"); // Redirect to login page after logout
  };

  return (
    <div className="p-6 bg-gray-100 min-h-screen">
      {/* Header Section */}
      <div className="bg-white shadow-md rounded-lg p-6 mb-6 border-l-4 border-emoryBlue">
        <h1 className="text-2xl font-bold text-emoryBlue">
          Welcome, {user?.email || "Guest"}!
        </h1>
        {user && (
          <button
            onClick={handleLogout}
            className="mt-4 px-4 py-2 bg-emoryGold text-white rounded hover:bg-emoryGold/90"
          >
            Logout
          </button>
        )}
      </div>

      {/* Navigation Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Navigate to TranscriptDrop */}
        <div className="bg-white shadow-md rounded-lg p-6 flex flex-col items-center border-l-4 border-emoryBlue">
          <h2 className="text-lg font-semibold text-emoryBlue mb-4">
            Upload Your Transcript
          </h2>
          <button
            onClick={() => navigate("/droptranscript")}
            className="px-4 py-2 bg-emoryBlue text-white rounded hover:bg-emoryBlue/90"
          >
            Go to Transcript Drop
          </button>
        </div>
      </div>
    </div>
  );
}


