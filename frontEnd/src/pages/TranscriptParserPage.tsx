// frontEnd/src/pages/TranscriptParserPage.tsx
import React, { useEffect, useRef, useState } from "react";
import { parseTranscript, type ParseResult } from "../utils/parseTranscript";
import { motion } from "framer-motion";
import { Upload, FileText, Clock } from "lucide-react";
import { Link } from "react-router-dom";

// Your logo
import applogo from "../assets/dooleyHelpzAppLogo.png";

// pdfjs-dist (client-side PDF text extraction + preview)
import {
  GlobalWorkerOptions,
  getDocument,
  type PDFDocumentProxy,
} from "pdfjs-dist";
// Vite-friendly worker import (if your setup complains, see the fallback below)
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
GlobalWorkerOptions.workerSrc = workerSrc;
// Fallback:
// GlobalWorkerOptions.workerSrc = new URL("pdf.worker.min.mjs", import.meta.url).toString();

type UploadedItem = {
  name: string;
  size: number;
  file: File;
  url: string;
  text: string;   // extracted text (used for parsing only; never displayed)
  time: string;
};

export default function TranscriptParserPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedItem[]>([]);
  const [selected, setSelected] = useState<UploadedItem | null>(null);
  const [parseResult, setParseResult] = useState<ParseResult | null>(null);
  const [isExtracting, setIsExtracting] = useState<boolean>(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // ---- Extract all text from PDF (for parsing only) ----
  async function extractPdfText(file: File): Promise<string> {
    const buf = await file.arrayBuffer();
    const pdf: PDFDocumentProxy = await getDocument({ data: buf }).promise;
    let all = "";
    for (let p = 1; p <= pdf.numPages; p++) {
      const page = await pdf.getPage(p);
      const content = await page.getTextContent();
      const items = content.items as any[];
      const pageText = items
        .map((it) => (typeof it?.str === "string" ? (it.str as string) : ""))
        .join(" ");
      all += (p > 1 ? "\n\n" : "") + pageText;
    }
    return all;
  }

  // ---- Render first page preview to a canvas ----
  async function renderPreview(item: UploadedItem) {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const buf = await item.file.arrayBuffer();
    const pdf: PDFDocumentProxy = await getDocument({ data: buf }).promise;
    const page = await pdf.getPage(1);

    const desiredWidth = 640;
    const viewport = page.getViewport({ scale: 1 });
    const scale = desiredWidth / viewport.width;
    const scaled = page.getViewport({ scale });

    canvas.width = Math.floor(scaled.width);
    canvas.height = Math.floor(scaled.height);

    await page.render({
      canvasContext: ctx,
      viewport: scaled,
      canvas, // ✅ required by your pdfjs-dist version
    }).promise;
  }

  // Re-render preview & parse when selection changes
  useEffect(() => {
    if (selected) {
      renderPreview(selected).catch((e) => console.error("Preview render failed:", e));
      setParseResult(parseTranscript(selected.text));
    } else {
      setParseResult(null);
    }
  }, [selected]);

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      uploadedFiles.forEach((u) => URL.revokeObjectURL(u.url));
    };
  }, [uploadedFiles]);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files) return;

    setIsExtracting(true);
    setExtractError(null);

    try {
      const fileArray = Array.from(files);
      const newItems: UploadedItem[] = [];

      for (const file of fileArray) {
        if (!file.name.toLowerCase().endsWith(".pdf")) continue;

        const url = URL.createObjectURL(file);
        const time = new Date().toLocaleString();
        const text = await extractPdfText(file); // parse-only

        newItems.push({ name: file.name, size: file.size, file, url, text, time });
      }

      if (newItems.length === 0) {
        setExtractError("No valid PDF selected. Please choose a text-based transcript PDF.");
        return;
      }

      setUploadedFiles((prev) => [...newItems, ...prev]);
      setSelected(newItems[0]); // auto-select newest
    } catch (err) {
      console.error(err);
      setExtractError(
        "We couldn’t read that PDF. If it’s a scanned image, export a text-based PDF first."
      );
    } finally {
      setIsExtracting(false);
      // allow re-uploading the same file
      e.currentTarget.value = "";
    }
  }

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      {/* ===== Header (with your logo) ===== */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-Gold">
            <img src={applogo} alt="DooleyHelpz" className="h-6 w-6 object-contain" />
          </div>
          <span className="text-lg font-semibold text-emoryBlue">DooleyHelpz</span>
        </Link>

        <Link
          to="/dash"
          className="hidden rounded-xl bg-lighterBlue px-3 py-1.5 text-sm font-semibold text-white hover:bg-emoryBlue/90 md:inline-block"
        >
          Back to Home
        </Link>
      </header>

      {/* ===== Main ===== */}
      <main className="mx-auto max-w-6xl px-4 py-8">
        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="mb-2 text-3xl font-bold text-emoryBlue"
        >
          Transcript Parser (PDF)
        </motion.h1>

        <p className="mb-6 text-zinc-600">
          Upload a <strong>.pdf</strong> transcript. We’ll preview the first page and extract course
          info locally in your browser. (No raw text is shown.)
        </p>

        {/* ===== Upload Section (PDF only) ===== */}
        <div className="mb-8 rounded-2xl border border-zinc-200 bg-gradient-to-br from-emoryBlue/5 via-white to-paleGold/20 p-6 shadow-sm">
          <label
            htmlFor="fileUpload"
            className="flex cursor-pointer flex-col items-center justify-center gap-3 py-6 text-center text-emoryBlue transition-colors hover:text-Gold"
          >
            <Upload className="h-8 w-8 opacity-80" />
            <p className="text-sm font-medium">
              Click to choose <span className="font-semibold">PDF transcript</span>{" "}
              (you can select multiple)
            </p>
            {isExtracting && (
              <p className="text-xs text-zinc-600">Extracting text from PDF…</p>
            )}
          </label>
          <input
            id="fileUpload"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            onChange={handleFileUpload}
            className="hidden"
          />

        {extractError && (
          <div
            className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
            role="alert"
          >
            {extractError}
          </div>
        )}
        </div>

        {/* ===== Recently Uploaded ===== */}
        {uploadedFiles.length > 0 && (
          <section className="mb-10">
            <h2 className="mb-3 text-xl font-semibold text-emoryBlue">Recently Uploaded</h2>
            <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white shadow-sm">
              <table className="min-w-full text-sm">
                <thead className="bg-zinc-100 text-zinc-700">
                  <tr>
                    <th className="px-4 py-2 text-left">File</th>
                    <th className="px-4 py-2 text-left">Size</th>
                    <th className="px-4 py-2 text-left">Uploaded</th>
                    <th className="px-4 py-2 text-left"></th>
                  </tr>
                </thead>
                <tbody>
                  {uploadedFiles.map((f, i) => (
                    <tr
                      key={i}
                      className="border-t border-zinc-100 transition-colors hover:bg-paleGold/10"
                    >
                      <td className="flex items-center gap-2 px-4 py-2">
                        <FileText className="h-4 w-4 text-emoryBlue" />
                        {f.name}
                      </td>
                      <td className="px-4 py-2">{(f.size / 1024).toFixed(1)} KB</td>
                      <td className="flex items-center gap-1 px-4 py-2">
                        <Clock className="h-3.5 w-3.5 opacity-70" />
                        {f.time}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={() => setSelected(f)}
                          className="text-sm font-medium text-emoryBlue transition-colors hover:text-Gold"
                        >
                          Preview & Parse
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ===== Preview + Parsed Courses ===== */}
        {selected && (
          <section className="grid gap-6 md:grid-cols-2">
            {/* PDF Preview (first page) */}
            <div>
              <h2 className="mb-2 text-xl font-semibold text-emoryBlue">PDF Preview</h2>
              <div className="rounded-lg border border-zinc-200 bg-white p-3 shadow-sm">
                <canvas ref={canvasRef} className="w-full h-auto" />
              </div>
              <p className="mt-2 text-xs text-zinc-500">
                Showing first page to confirm you uploaded the right document.
              </p>
            </div>

            {/* Parsed Courses */}
            <div>
              <h2 className="mb-2 text-xl font-semibold text-emoryBlue">Parsed Courses</h2>
              {parseResult && parseResult.courses.length > 0 ? (
                <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white shadow-sm">
                  <table className="min-w-full text-sm">
                    <thead className="bg-zinc-100 text-zinc-700">
                      <tr>
                        <th className="px-3 py-2 text-left">Course</th>
                        <th className="px-3 py-2 text-left">Title</th>
                        <th className="px-3 py-2 text-left">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {parseResult.courses.map((c, i) => (
                        <tr
                          key={i}
                          className="border-t border-zinc-100 transition-colors hover:bg-paleGold/10"
                        >
                          <td className="px-3 py-2">{c.course}</td>
                          <td className="px-3 py-2">{c.name}</td>
                          <td className="px-3 py-2">
                            {c.inProgress ? (
                              <span className="rounded bg-paleGold px-2 py-0.5 text-xs text-emoryBlue">
                                In progress
                              </span>
                            ) : (
                              <span className="text-xs text-zinc-600">Completed</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-sm italic text-zinc-500">No courses detected.</p>
              )}
            </div>
          </section>
        )}

        {/* ===== Privacy Disclaimer ===== */}
        <div className="mt-10 rounded-xl border border-zinc-200 bg-zinc-50 p-5 text-sm text-zinc-600">
          <p className="mb-1 font-semibold text-emoryBlue">Data Privacy Disclaimer</p>
          <p>
            DooleyHelpz only stores information about <strong>classes taken</strong> (course and
            title) for the purpose of schedule planning. We do <strong>not</strong> store any
            grades, GPA data, personal names, or identifying information. Failed (F) and withdrawn
            (W) courses are excluded.
          </p>
        </div>
      </main>

      {/* ===== Footer ===== */}
      <footer className="mt-8 border-t border-zinc-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 text-center text-sm text-zinc-600">
          © {new Date().getFullYear()} DooleyHelpz — Transcript Parser Utility
        </div>
      </footer>
    </div>
  );
}
