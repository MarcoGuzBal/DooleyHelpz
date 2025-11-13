import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Upload, FileText, Clock, CheckCircle2, AlertCircle, Send } from "lucide-react";
import { Link } from "react-router-dom";

// Logo
import applogo from "../assets/dooleyHelpzAppLogo.png";

// pdfjs-dist (client-side PDF text extraction + preview)
import {
  GlobalWorkerOptions,
  getDocument,
  type PDFDocumentProxy,
} from "pdfjs-dist";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
GlobalWorkerOptions.workerSrc = workerSrc;

// Parser now returns 3 buckets
import { parseTranscript, type ParseResult } from "../utils/parseTranscript";

type UploadedItem = {
  name: string;
  size: number;
  file: File;
  url: string;
  text: string; // extracted text (used for parsing only; never displayed)
  time: string;
};

export default function TranscriptParserPage() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedItem[]>([]);
  const [selected, setSelected] = useState<UploadedItem | null>(null);

  // Parsed buckets to display
  const [buckets, setBuckets] = useState<ParseResult | null>(null);

  // Which codes are currently INCLUDED (green). Start with all parsed codes included.
  const [selIncomingTransfer, setSelIncomingTransfer] = useState<Set<string>>(new Set());
  const [selIncomingTest, setSelIncomingTest] = useState<Set<string>>(new Set());
  const [selEmory, setSelEmory] = useState<Set<string>>(new Set());

  // UX state
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [postedOk, setPostedOk] = useState<null | boolean>(null);
  const [postError, setPostError] = useState<string | null>(null);

  // store the last submitted payload (for JSON preview)
  const [submittedPayload, setSubmittedPayload] = useState<Record<string, unknown> | null>(null);
  
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
      const pageText = items.map((it) => (typeof it?.str === "string" ? (it.str as string) : "")).join(" ");
      all += (p > 1 ? "\n\n" : "") + pageText;
    }
    return all.trim();
  }

  // ---- Render first page preview to a canvas (optional visual) ----
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

    await page.render({ canvasContext: ctx, viewport: scaled, canvas }).promise;
  }

  // ---- POST separated buckets to backend ----
  async function sendToBackendSeparated(
    incoming_transfer_courses: string[],
    incoming_test_courses: string[],
    emory_courses: string[]
  ) {
    try {
      setPosting(true);
      setPostedOk(null);
      setPostError(null);

      const res = await fetch("http://localhost:5001/api/userCourses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incoming_transfer_courses, incoming_test_courses, emory_courses }),
      });

      setPostedOk(res.ok);
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `Backend responded ${res.status}`);
      }
    } catch (err: any) {
      setPostedOk(false);
      setPostError(err?.message || "Failed to send to backend");
    } finally {
      setPosting(false);
    }
  }

  // Re-render preview & parse when selection changes (no auto-send)
  useEffect(() => {
    if (selected) {
      renderPreview(selected).catch((e) => console.error("Preview render failed:", e));

      const parsed = parseTranscript(selected.text);
      setBuckets(parsed);

      setSelIncomingTransfer(new Set(parsed.incoming_transfer_courses));
      setSelIncomingTest(new Set(parsed.incoming_test_courses));
      setSelEmory(new Set(parsed.emory_courses));

      setPostedOk(null);
      setPostError(null);
    } else {
      setBuckets(null);
      setSelIncomingTransfer(new Set());
      setSelIncomingTest(new Set());
      setSelEmory(new Set());
      setPostedOk(null);
      setPostError(null);
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
      setExtractError("We couldn’t read that PDF. If it’s a scanned image, export a text-based PDF first.");
    } finally {
      setIsExtracting(false);
      e.currentTarget.value = "";
    }
  }

  // --- Toggle helpers ---
  function toggle(setter: React.Dispatch<React.SetStateAction<Set<string>>>, code: string) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code); else next.add(code);
      return next;
    });
  }

  // --- Submit handler ---
  function handleSubmit() {
    const incoming_transfer_courses = Array.from(selIncomingTransfer);
    const incoming_test_courses = Array.from(selIncomingTest);
    const emory_courses = Array.from(selEmory);

    if (!incoming_transfer_courses.length && !incoming_test_courses.length && !emory_courses.length) {
      setPostedOk(false);
      setPostError("No courses selected.");
      return;
    }
    sendToBackendSeparated(incoming_transfer_courses, incoming_test_courses, emory_courses);

    setSubmittedPayload({
      incoming_transfer_courses,
      incoming_test_courses,
      emory_courses,
    });
  }

  // --- Small UI helpers ---
  function Chip({
    code,
    isSelected,
    onClick,
  }: {
    code: string;
    isSelected: boolean;
    onClick: () => void;
  }) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={
          "rounded-md border px-2.5 py-2 text-sm shadow-sm transition-colors " +
          (isSelected
            ? "border-green-300 bg-green-50 text-green-800 hover:bg-green-100"
            : "border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100")
        }
        title={isSelected ? "Selected (will send)" : "Deselected (won't send)"}
      >
        {code}
      </button>
    );
  }

  const totalSelected =
    selIncomingTransfer.size + selIncomingTest.size + selEmory.size;

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
          to="/dashboard"
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
          Upload a <strong>.pdf</strong> transcript. We’ll preview the first page and extract{" "}
          <strong>course codes</strong> locally. Click codes to toggle validity (green = include,
          red = exclude), then submit to save.
        </p>

        {/* ===== Upload Section (PDF only) ===== */}
        <div className="mb-8 rounded-2xl border border-zinc-200 bg-linear-to-br from-emoryBlue/5 via-white to-paleGold/20 p-6 shadow-sm">
          <label
            htmlFor="fileUpload"
            className="flex cursor-pointer flex-col items-center justify-center gap-3 py-6 text-center text-emoryBlue transition-colors hover:text-Gold"
          >
            <Upload className="h-8 w-8 opacity-80" />
            <p className="text-sm font-medium">
              Click to choose <span className="font-semibold">PDF transcript</span> (you can select multiple)
            </p>
            {isExtracting && <p className="text-xs text-zinc-600">Extracting text from PDF…</p>}
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
            <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
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
                    <tr key={i} className="border-t border-zinc-100 transition-colors hover:bg-paleGold/10">
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

        {/* ===== Preview + Parsed Course Codes (toggleable) ===== */}
        {selected && buckets && (
          <section className="grid gap-6 md:grid-cols-2">
            {/* Incoming Transfer */}
            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Incoming — Transfer</h2>
                <span className="text-sm text-zinc-600">{selIncomingTransfer.size} selected</span>
              </div>
              {buckets.incoming_transfer_courses.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {buckets.incoming_transfer_courses.map((code) => {
                    const isSelected = selIncomingTransfer.has(code);
                    return (
                      <Chip
                        key={`in-tr-${code}`}
                        code={code}
                        isSelected={isSelected}
                        onClick={() => toggle(setSelIncomingTransfer, code)}
                      />
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm italic text-zinc-500">No transfer credits found.</p>
              )}
            </div>

            {/* Incoming Test */}
            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Incoming — Test (AP/IB/etc.)</h2>
                <span className="text-sm text-zinc-600">{selIncomingTest.size} selected</span>
              </div>
              {buckets.incoming_test_courses.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {buckets.incoming_test_courses.map((code) => {
                    const isSelected = selIncomingTest.has(code);
                    return (
                      <Chip
                        key={`in-te-${code}`}
                        code={code}
                        isSelected={isSelected}
                        onClick={() => toggle(setSelIncomingTest, code)}
                      />
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm italic text-zinc-500">No test credits found.</p>
              )}
            </div>

            {/* Emory bucket */}
            <div className="md:col-span-2">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Emory — Academic Record</h2>
                <span className="text-sm text-zinc-600">{selEmory.size} selected</span>
              </div>
              {buckets.emory_courses.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                  {buckets.emory_courses.map((code) => {
                    const isSelected = selEmory.has(code);
                    return (
                      <Chip
                        key={`em-${code}`}
                        code={code}
                        isSelected={isSelected}
                        onClick={() => toggle(setSelEmory, code)}
                      />
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm italic text-zinc-500">No Emory courses found.</p>
              )}
            </div>
          </section>
        )}

        {/* ===== Submit row ===== */}
        {selected && buckets && (
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-zinc-600">
              <span className="font-medium text-emoryBlue">{totalSelected}</span> total selected
              {posting && <span className="ml-2 italic">• posting…</span>}
              {postError && <span className="ml-2 text-rose-600">• {postError}</span>}
              {postedOk === true && (
                <span className="ml-2 inline-flex items-center gap-1 rounded-md bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Saved
                </span>
              )}
              {postedOk === false && (
                <span className="ml-2 inline-flex items-center gap-1 rounded-md bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
                  <AlertCircle className="h-3.5 w-3.5" /> Failed
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={
                posting ||
                (!selIncomingTransfer.size && !selIncomingTest.size && !selEmory.size)
              }
              className={
                "inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold shadow-sm " +
                (posting ||
                (!selIncomingTransfer.size && !selIncomingTest.size && !selEmory.size)
                  ? "cursor-not-allowed bg-zinc-200 text-zinc-500"
                  : "bg-emoryBlue text-white hover:bg-emoryBlue/90")
              }
            >
              <Send className="h-4 w-4" />
              Submit selected
            </button>
          </div>
        )}

        <div className="mt-6">
          <h3 className="font-semibold">Submitted JSON Preview</h3>
          <pre className="bg-gray-100 text-sm p-3 rounded overflow-auto">
            {submittedPayload
              ? JSON.stringify(submittedPayload, null, 2)
              : "No data submitted yet."}
          </pre>
        </div>

        {/* ===== Privacy Disclaimer ===== */}
        <div className="mt-10 rounded-xl border border-zinc-200 bg-zinc-50 p-5 text-sm text-zinc-600">
          <p className="mb-1 font-semibold text-emoryBlue">Data Privacy Disclaimer</p>
          <p>
            DooleyHelpz only stores information about <strong>classes taken</strong> (course codes)
            for the purpose of schedule planning. We do <strong>not</strong> store any grades, GPA
            data, personal names, or identifying information. Failed (F) and withdrawn (W) courses are excluded.
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

