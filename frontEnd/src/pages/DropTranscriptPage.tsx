import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { API_URL } from "../utils/api";

export default function DropTranscriptPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const getSharedId = (): number => {
    let id = localStorage.getItem("shared_id");
    if (!id) {
      id = Date.now().toString();
      localStorage.setItem("shared_id", id);
    }
    return parseInt(id);
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf") {
        setFile(droppedFile);
        setError(null);
      } else {
        setError("Please upload a PDF file");
      }
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === "application/pdf") {
        setFile(selectedFile);
        setError(null);
      } else {
        setError("Please upload a PDF file");
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a file first");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const sharedId = getSharedId();

      // For now, we'll send a placeholder - in production, you'd parse the PDF
      // or send it to a backend endpoint that handles PDF parsing
      const coursesData = {
        shared_id: sharedId,
        courses: {
          emory_courses: [],
          transfer_credits: [],
          test_credits: [],
          total_emory_credits: 0,
        },
        filename: file.name,
        uploaded_at: new Date().toISOString(),
      };

      const response = await fetch(`${API_URL}/api/userCourses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(coursesData),
      });

      const data = await response.json();

      if (response.ok) {
        navigate("/preferences");
      } else {
        setError(data.error || "Failed to upload transcript");
      }
    } catch (err) {
      console.error("Error uploading transcript:", err);
      setError("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Upload Your Transcript</h1>
        <p className="text-gray-600 mb-8">
          Upload your unofficial transcript PDF to import your completed courses
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded-lg">{error}</div>
        )}

        <div
          className={`border-2 border-dashed rounded-lg p-12 text-center transition ${
            dragActive
              ? "border-blue-500 bg-blue-50"
              : file
              ? "border-green-500 bg-green-50"
              : "border-gray-300 hover:border-gray-400"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            type="file"
            accept=".pdf"
            onChange={handleChange}
            className="hidden"
            id="file-input"
          />

          {file ? (
            <div>
              <svg
                className="w-12 h-12 mx-auto text-green-500 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <p className="text-lg font-medium text-gray-900">{file.name}</p>
              <p className="text-sm text-gray-500 mt-1">
                {(file.size / 1024).toFixed(1)} KB
              </p>
              <button
                onClick={() => setFile(null)}
                className="mt-4 text-sm text-red-600 hover:text-red-700"
              >
                Remove file
              </button>
            </div>
          ) : (
            <div>
              <svg
                className="w-12 h-12 mx-auto text-gray-400 mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <p className="text-lg text-gray-700 mb-2">
                Drag and drop your transcript PDF here
              </p>
              <p className="text-gray-500 mb-4">or</p>
              <label
                htmlFor="file-input"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer transition"
              >
                Browse Files
              </label>
            </div>
          )}
        </div>

        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="w-full mt-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition font-medium"
        >
          {loading ? "Uploading..." : "Upload & Continue"}
        </button>

        <p className="text-sm text-gray-500 text-center mt-4">
          Your transcript is processed securely and never stored permanently
        </p>
      </div>
    </div>
  );
}