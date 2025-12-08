import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Upload, FileText, Clock, CheckCircle2, AlertCircle, Send } from "lucide-react";
import { Link } from "react-router-dom";
import { API_URL, api } from "../utils/api";
import { auth } from "../firebase";
import {
  GlobalWorkerOptions,
  getDocument,
  type PDFDocumentProxy,
} from "pdfjs-dist";
// Vite-friendly worker import; falls back to CDN if unavailable
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

import applogo from "../assets/dooleyHelpzAppLogo.png";
import { parseTranscript, type ParseResult } from "../utils/parseTranscript";

try {
  GlobalWorkerOptions.workerSrc = workerSrc;
} catch (e) {
  console.warn("Failed to load PDF worker from bundler URL, using CDN fallback...", e);
  GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js`;
}

type UploadedItem = {
  name: string;
  size: number;
  file: File;
  url: string;
  text: string;
  time: string;
};

// Simple prerequisite graph for common CS courses.
// Each course maps to OR-groups of prerequisites. Example:
// CS350: [["CS253"], ["CS255"]] means you need one course from each group (AND between groups, OR within group).
const PREREQ_GRAPH: Record<string, string[][]> = {
  MATH112: [["MATH111"]],
  CS171: [["CS170"]],
  CS224: [["CS171"]],
  CS253: [["CS171"]],
  CS255: [["CS171"]],
  CS326: [["CS253"]],
  CS350: [["CS253"], ["CS255"]],
};

const normalizeCode = (code: string) => code.toUpperCase().replace(/\s+/g, "");

function collectMissingPrereqs(
  course: string,
  selected: Set<string>,
  missing: Set<string>,
  graph: Record<string, string[][]>,
  visiting = new Set<string>()
) {
  const code = normalizeCode(course);
  if (visiting.has(code)) return;
  visiting.add(code);

  const prereqGroups = graph[code] || [];
  const isEmptyGroups =
    !prereqGroups ||
    prereqGroups.length === 0 ||
    (prereqGroups.length === 1 && prereqGroups[0].length === 0);
  if (isEmptyGroups) {
    visiting.delete(code);
    return;
  }

  prereqGroups.forEach((group) => {
    const groupSatisfied = group.some((req) => selected.has(normalizeCode(req)));
    if (groupSatisfied) return;

    group.forEach((req) => {
      const reqNorm = normalizeCode(req);
      if (!selected.has(reqNorm)) {
        missing.add(reqNorm);
      }
      if (graph[reqNorm]) {
        collectMissingPrereqs(reqNorm, selected, missing, graph, visiting);
      }
    });
  });

  visiting.delete(code);
}

export default function DropTranscript() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedItem[]>([]);
  const [selected, setSelected] = useState<UploadedItem | null>(null);

  const [buckets, setBuckets] = useState<ParseResult | null>(null);

  const [selIncomingTransfer, setSelIncomingTransfer] = useState<Set<string>>(new Set());
  const [selIncomingTest, setSelIncomingTest] = useState<Set<string>>(new Set());
  const [selEmory, setSelEmory] = useState<Set<string>>(new Set());
  const [selSpring2026, setSelSpring2026] = useState<Set<string>>(new Set());
  const [prereqMap, setPrereqMap] = useState<Record<string, string[][]>>({});

  const [transferInput, setTransferInput] = useState("");
  const [testInput, setTestInput] = useState("");
  const [emoryInput, setEmoryInput] = useState("");
  const [springInput, setSpringInput] = useState("");

  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [postedOk, setPostedOk] = useState<null | boolean>(null);
  const [postError, setPostError] = useState<string | null>(null);

  // Derived prerequisite suggestions (base courses missing)
  const selectedCodes = new Set<string>([
    ...Array.from(selIncomingTransfer).map(normalizeCode),
    ...Array.from(selIncomingTest).map(normalizeCode),
    ...Array.from(selEmory).map(normalizeCode),
    ...Array.from(selSpring2026).map(normalizeCode),
  ]);
  const mergedGraph: Record<string, string[][]> = { ...PREREQ_GRAPH, ...prereqMap };
  const missingPrereqs = new Set<string>();
  selectedCodes.forEach((code) => collectMissingPrereqs(code, selectedCodes, missingPrereqs, mergedGraph));
  const missingPrereqList = Array.from(missingPrereqs).sort();

  // Fetch prerequisites for all selected codes from backend
  useEffect(() => {
    const rootCodes = Array.from(selectedCodes);
    if (rootCodes.length === 0) {
      setPrereqMap({});
      return;
    }

    const fetchPrereqsRecursive = async () => {
      const seen = new Set<string>();
      const graph: Record<string, string[][]> = {};
      let toVisit = rootCodes.map(normalizeCode);
      const maxDepth = 5; // guard against runaway loops

      for (let depth = 0; depth < maxDepth && toVisit.length > 0; depth++) {
        const batch = Array.from(new Set(toVisit)).filter((code) => !seen.has(code));
        if (batch.length === 0) break;
        batch.forEach((code) => seen.add(code));

        try {
          const res = await fetch(
            `${API_URL}/api/course-prereqs?codes=${encodeURIComponent(batch.join(","))}`
          );
          const data = await res.json();
          if (data.success && data.prereqs) {
            Object.entries<any>(data.prereqs).forEach(([key, val]) => {
              const normKey = normalizeCode(key);
              if (Array.isArray(val)) {
                graph[normKey] = val as string[][];
              }
            });
          }
        } catch (err) {
          console.error("Failed to fetch prerequisites:", err);
        }

        // Collect newly discovered prereq codes to explore
        const newlyFound = new Set<string>();
        Object.values(graph).forEach((groups) => {
          groups.forEach((group) => {
            group.forEach((code) => {
              const norm = normalizeCode(code);
              if (!seen.has(norm)) newlyFound.add(norm);
            });
          });
        });
        toVisit = Array.from(newlyFound);
      }

      setPrereqMap(graph);
    };

    fetchPrereqsRecursive();
  }, [selIncomingTransfer, selIncomingTest, selEmory, selSpring2026, selectedCodes]);

  async function extractPdfText(file: File): Promise<string> {
    try {
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
      return all.trim();
    } catch (err) {
      console.error("PDF extraction error:", err);
      const msg = err instanceof Error ? err.message : "Failed to extract text from PDF";
      throw new Error(msg);
    }
  }

  async function sendToBackendSeparated(
    incoming_transfer_courses: string[],
    incoming_test_courses: string[],
    emory_courses: string[],
    spring_2026_courses: string[],
    _uid?: number
  ) {
    try {
      setPosting(true);
      setPostedOk(null);
      setPostError(null);

      const uid = auth.currentUser?.uid;
      if (!uid) {
        setPostedOk(false);
        setPostError("Not signed in");
        return;
      }

      const result = await api.uploadCourses({
        incoming_transfer_courses,
        incoming_test_courses,
        emory_courses,
        spring_2026_courses,
        uid: uid,
      });

      setPostedOk(result.success);
      if (!result.success) {
        throw new Error(result.error || "Failed to upload courses");
      }
    } catch (err: any) {
      setPostedOk(false);
      setPostError(err?.message || "Failed to send to backend");
    } finally {
      setPosting(false);
    }
  }

  useEffect(() => {
    if (selected) {
      try {
        const parsed = parseTranscript(selected.text);

        if (!parsed) {
          console.error("parseTranscript returned null/undefined");
          setBuckets({
            incoming_transfer_courses: [],
            incoming_test_courses: [],
            emory_courses: [],
            spring_2026_courses: [],
          });
          setSelIncomingTransfer(new Set());
          setSelIncomingTest(new Set());
          setSelEmory(new Set());
          setSelSpring2026(new Set());
          return;
        }

        setBuckets(parsed);
        setSelIncomingTransfer(new Set(parsed.incoming_transfer_courses || []));
        setSelIncomingTest(new Set(parsed.incoming_test_courses || []));
        setSelEmory(new Set(parsed.emory_courses || []));
        setSelSpring2026(new Set(parsed.spring_2026_courses || []));
        setPostedOk(null);
        setPostError(null);
      } catch (err) {
        console.error("Error parsing transcript:", err);
        setBuckets({
          incoming_transfer_courses: [],
          incoming_test_courses: [],
          emory_courses: [],
          spring_2026_courses: [],
        });
        setSelIncomingTransfer(new Set());
        setSelIncomingTest(new Set());
        setSelEmory(new Set());
        setSelSpring2026(new Set());
        setExtractError("Failed to parse transcript. Please try again.");
      }
    } else {
      setBuckets(null);
      setSelIncomingTransfer(new Set());
      setSelIncomingTest(new Set());
      setSelEmory(new Set());
      setSelSpring2026(new Set());
      setPostedOk(null);
      setPostError(null);
    }
  }, [selected]);

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
        const text = await extractPdfText(file);

        newItems.push({ name: file.name, size: file.size, file, url, text, time });
      }

      if (newItems.length === 0) {
        setExtractError("No valid PDF selected. Please choose a text-based transcript PDF.");
        return;
      }

      setUploadedFiles((prev) => [...newItems, ...prev]);
      setSelected(newItems[0]);
    } catch (err) {
      console.error(err);
      setExtractError("We couldn't read that PDF. If it's a scanned image, export a text-based PDF first.");
    } finally {
      setIsExtracting(false);
    }
  }

  function toggle(setter: React.Dispatch<React.SetStateAction<Set<string>>>, code: string) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  function handleAdd(setter: React.Dispatch<React.SetStateAction<Set<string>>>, value: string) {
    const code = value.trim().toUpperCase();
    if (!code) return;
    setter((prev) => {
      const next = new Set(prev);
      next.add(code);
      return next;
    });
  }

  function handleSubmit() {
    const incoming_transfer_courses = Array.from(selIncomingTransfer);
    const incoming_test_courses = Array.from(selIncomingTest);
    const emory_courses = Array.from(selEmory);
    const spring_2026_courses = Array.from(selSpring2026);

    if (
      !incoming_transfer_courses.length &&
      !incoming_test_courses.length &&
      !emory_courses.length &&
      !spring_2026_courses.length
    ) {
      setPostedOk(false);
      setPostError("No courses selected.");
      return;
    }
    const uid = auth.currentUser?.uid;
    if (!uid) throw new Error("Not signed in");

    sendToBackendSeparated(
      incoming_transfer_courses,
      incoming_test_courses,
      emory_courses,
      spring_2026_courses
    );
  }

  const displayIncomingTransfer = buckets
    ? Array.from(new Set([...(buckets.incoming_transfer_courses || []), ...selIncomingTransfer]))
    : Array.from(selIncomingTransfer);

  const displayIncomingTest = buckets
    ? Array.from(new Set([...(buckets.incoming_test_courses || []), ...selIncomingTest]))
    : Array.from(selIncomingTest);

  const displayEmory = buckets
    ? Array.from(new Set([...(buckets.emory_courses || []), ...selEmory]))
    : Array.from(selEmory);

  const displaySpring2026 = buckets
    ? Array.from(new Set([...(buckets.spring_2026_courses || []), ...selSpring2026]))
    : Array.from(selSpring2026);

  function Chip({ code, isSelected, onClick }: { code: string; isSelected: boolean; onClick: () => void }) {
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
    selIncomingTransfer.size +
    selIncomingTest.size +
    selEmory.size +
    selSpring2026.size;

  return (
    <div className="min-h-screen bg-white text-zinc-900">
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
          Back to Dashboard
        </Link>
      </header>

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
          Upload a <strong>.pdf</strong> transcript. We'll extract <strong>course codes</strong> locally.
          Click codes to toggle validity (green = include, red = exclude), then submit to save.
        </p>

        <div className="mb-8 rounded-2xl border border-zinc-200 bg-linear-to-br from-emoryBlue/5 via-white to-paleGold/20 p-6 shadow-sm">
          <label
            htmlFor="fileUpload"
            className="flex cursor-pointer flex-col items-center justify-center gap-3 py-6 text-center text-emoryBlue transition-colors hover:text-Gold"
          >
            <Upload className="h-8 w-8 opacity-80" />
            <p className="text-sm font-medium">
              Click to choose <span className="font-semibold">PDF transcript</span> (you can select multiple)
            </p>
            <p className="text-xs text-zinc-500 max-w-md">
              If you're a freshman, just drop in any PDF and manually add a fake course code like "1" so you can move
              forward.
            </p>
            {isExtracting && <p className="text-xs text-zinc-600">Extracting text from PDF...</p>}
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

        {selected && buckets && (
          <section className="grid gap-6 md:grid-cols-2">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Incoming — Transfer</h2>
                <span className="text-sm text-zinc-600">{selIncomingTransfer.size} selected</span>
              </div>
              {displayIncomingTransfer.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {displayIncomingTransfer.map((code) => {
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

              <div className="mt-3 flex items-center gap-2">
                <input
                  type="text"
                  value={transferInput}
                  onChange={(e) => setTransferInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAdd(setSelIncomingTransfer, transferInput);
                      setTransferInput("");
                    }
                  }}
                  placeholder="e.g. CHEM150"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelIncomingTransfer, transferInput);
                    setTransferInput("");
                  }}
                  className="rounded-md bg-emoryBlue px-3 py-1 text-sm text-white hover:bg-emoryBlue/90"
                >
                  Add
                </button>
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Incoming — Test (AP/IB/etc.)</h2>
                <span className="text-sm text-zinc-600">{selIncomingTest.size} selected</span>
              </div>
              {displayIncomingTest.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {displayIncomingTest.map((code) => {
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

              <div className="mt-3 flex items-center gap-2">
                <input
                  type="text"
                  value={testInput}
                  onChange={(e) => setTestInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAdd(setSelIncomingTest, testInput);
                      setTestInput("");
                    }
                  }}
                  placeholder="e.g. PSYC111"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelIncomingTest, testInput);
                    setTestInput("");
                  }}
                  className="rounded-md bg-emoryBlue px-3 py-1 text-sm text-white hover:bg-emoryBlue/90"
                >
                  Add
                </button>
              </div>
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Incoming — Spring 2026 (Planned)</h2>
                <span className="text-sm text-zinc-600">{selSpring2026.size} selected</span>
              </div>
              {displaySpring2026.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {displaySpring2026.map((code) => {
                    const isSelected = selSpring2026.has(code);
                    return (
                      <Chip
                        key={`sp-26-${code}`}
                        code={code}
                        isSelected={isSelected}
                        onClick={() => toggle(setSelSpring2026, code)}
                      />
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm italic text-zinc-500">No Spring 2026 courses found.</p>
              )}

              <div className="mt-3 flex items-center gap-2">
                <input
                  type="text"
                  value={springInput}
                  onChange={(e) => setSpringInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAdd(setSelSpring2026, springInput);
                      setSpringInput("");
                    }
                  }}
                  placeholder="e.g. BUS494"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelSpring2026, springInput);
                    setSpringInput("");
                  }}
                  className="rounded-md bg-emoryBlue px-3 py-1 text-sm text-white hover:bg-emoryBlue/90"
                >
                  Add
                </button>
              </div>
            </div>

            <div className="md:col-span-2">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Emory — Academic Record</h2>
                <span className="text-sm text-zinc-600">{selEmory.size} selected</span>
              </div>
              {displayEmory.length ? (
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
                  {displayEmory.map((code) => {
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

              <div className="mt-3 flex items-center gap-2">
                <input
                  type="text"
                  value={emoryInput}
                  onChange={(e) => setEmoryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleAdd(setSelEmory, emoryInput);
                      setEmoryInput("");
                    }
                  }}
                  placeholder="e.g. CS377"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelEmory, emoryInput);
                    setEmoryInput("");
                  }}
                  className="rounded-md bg-emoryBlue px-3 py-1 text-sm text-white hover:bg-emoryBlue/90"
                >
                  Add
                </button>
              </div>
            </div>
          </section>
        )}

        {selected && buckets && (
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-zinc-600">
              <span className="font-medium text-emoryBlue">{totalSelected}</span> total selected
              {posting && <span className="ml-2 italic">• posting...</span>}
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
              {missingPrereqList.length > 0 && (
                <span className="ml-2 inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                  Add: {missingPrereqList.join(", ")} before submitting
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={
                posting ||
                (!selIncomingTransfer.size &&
                  !selIncomingTest.size &&
                  !selEmory.size &&
                  !selSpring2026.size)
              }
              className={
                "inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold shadow-sm " +
                (posting ||
                (!selIncomingTransfer.size &&
                  !selIncomingTest.size &&
                  !selEmory.size &&
                  !selSpring2026.size)
                  ? "cursor-not-allowed bg-zinc-200 text-zinc-500"
                  : "bg-emoryBlue text-white hover:bg-emoryBlue/90")
              }
            >
              <Send className="h-4 w-4" />
              Submit selected
            </button>
          </div>
        )}

        <div className="mt-10 rounded-xl border border-zinc-200 bg-zinc-50 p-5 text-sm text-zinc-600">
          <p className="mb-1 font-semibold text-emoryBlue">Data Privacy Disclaimer</p>
          <p>
            DooleyHelpz only stores information about <strong>classes taken or planned</strong> (course codes) for the
            purpose of schedule planning. We do <strong>not</strong> store any grades, GPA data, personal names, or
            identifying information. Failed (F) and withdrawn (W) courses are excluded.
          </p>
        </div>
      </main>

      <footer className="mt-8 border-t border-zinc-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 text-center text-sm text-zinc-600">
          © {new Date().getFullYear()} DooleyHelpz — Transcript Parser Utility
        </div>
      </footer>
    </div>
  );
}
