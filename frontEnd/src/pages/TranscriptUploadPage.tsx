import React, { useRef, useState } from "react";
import "pdfjs-dist/web/pdf_viewer.css";

export default function TranscriptUploadPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [classes, setClasses] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    setClasses([]);

    try {
      // ✅ Lazy load pdf.js only when needed
      const pdfjsLib = await import("pdfjs-dist");
      pdfjsLib.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

      const fileUrl = URL.createObjectURL(file);
      const pdf = await pdfjsLib.getDocument(fileUrl).promise;

      let allText = "";

      // Extract text from all pages
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();
        const textItems = textContent.items.map((item: any) => item.str).join(" ");
        allText += textItems + " ";
      }

      // Find course codes
      const regex = /\b[A-Z]{2,4}\s?\d{3,4}\b/g;
      const found = Array.from(new Set(allText.match(regex) || []));
      setClasses(found);

      // Render first page preview — smaller scale for compact view
      const page1 = await pdf.getPage(1);
      const viewport = page1.getViewport({ scale: 0.7 }); // smaller scale
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext("2d")!;

      canvas.width = viewport.width;
      canvas.height = viewport.height;

      await page1.render({ canvasContext: ctx, viewport, canvas }).promise;
    } catch (err) {
      console.error(err);
      setError("Failed to process PDF. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-6 bg-gray-50">
      <h1 className="text-2xl font-bold mb-4 text-emoryBlue">Upload Your Transcript</h1>

      <input
        type="file"
        accept="application/pdf"
        onChange={handleFileUpload}
        className="mb-6"
      />

      {loading && <p className="text-gray-600 mb-4">Scanning transcript...</p>}
      {error && <p className="text-red-500 mb-4">{error}</p>}

      {/* 🖼️ Smaller preview box */}
      <canvas
        ref={canvasRef}
        className="border border-emoryBlue shadow-md bg-white mb-6 rounded-lg max-w-md"
        style={{ width: "80%", height: "auto" }}
      />

      {/* 📋 Class results */}
      <div className="w-full max-w-md bg-white p-4 rounded-xl shadow-sm border border-emoryBlue text-center">
        <h2 className="text-lg font-semibold mb-2 text-emoryBlue">Detected Classes</h2>
        {classes.length > 0 ? (
          <ul className="list-disc list-inside text-gray-700 text-left">
            {classes.map((cls) => (
              <li key={cls}>{cls}</li>
            ))}
          </ul>
        ) : (
          !loading && <p className="text-gray-500 italic">No classes detected. Try another transcript.</p>
        )}
      </div>
    </div>
  );
}
