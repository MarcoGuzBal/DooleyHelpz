import { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Upload, FileText, Clock, CheckCircle2, AlertCircle, Send, AlertTriangle, Loader2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
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

// Normalize course code: "CS 350" -> "CS350", "cs350" -> "CS350"
const normalizeCode = (code: string) => code.toUpperCase().replace(/[^A-Z0-9]/g, "")
// Types for prerequisite validation
type PrereqGroup = string[][]; // Each inner array is an OR group, outer is AND
type PrereqMap = Record<string, PrereqGroup>;

// Course existence: undefined = not checked yet, true = exists, false = doesn't exist
type CourseExistenceMap = Record<string, boolean | undefined>;

type CourseValidation = {
  exists: boolean | undefined; // undefined = pending
  missingPrereqs: string[];
  prereqDetails: { group: string[]; satisfied: boolean; satisfiedBy?: string }[];
};

export default function DropTranscript() {
  const navigate = useNavigate();
  
  const [uploadedFiles, setUploadedFiles] = useState<UploadedItem[]>([]);
  const [selected, setSelected] = useState<UploadedItem | null>(null);

  const [buckets, setBuckets] = useState<ParseResult | null>(null);

  // Keep track of all codes per bucket (including deselected/manual) so chips stay visible
  const [allIncomingTransfer, setAllIncomingTransfer] = useState<Set<string>>(new Set());
  const [allIncomingTest, setAllIncomingTest] = useState<Set<string>>(new Set());
  const [allEmory, setAllEmory] = useState<Set<string>>(new Set());
  const [allSpring2026, setAllSpring2026] = useState<Set<string>>(new Set());

  const [selIncomingTransfer, setSelIncomingTransfer] = useState<Set<string>>(new Set());
  const [selIncomingTest, setSelIncomingTest] = useState<Set<string>>(new Set());
  const [selEmory, setSelEmory] = useState<Set<string>>(new Set());
  const [selSpring2026, setSelSpring2026] = useState<Set<string>>(new Set());
  
  // Prerequisite map from backend
  const [prereqMap, setPrereqMap] = useState<PrereqMap>({});
  
  // Course existence validation - undefined = not checked, true = exists, false = doesn't exist
  const [courseExistence, setCourseExistence] = useState<CourseExistenceMap>({});
  const [validatingCourses, setValidatingCourses] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [transferInput, setTransferInput] = useState("");
  const [testInput, setTestInput] = useState("");
  const [emoryInput, setEmoryInput] = useState("");
  const [springInput, setSpringInput] = useState("");

  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);
  const [postedOk, setPostedOk] = useState<null | boolean>(null);
  const [postError, setPostError] = useState<string | null>(null);
  const [acknowledgePrereqRisk, setAcknowledgePrereqRisk] = useState(false);

  // Track if initial validation has completed
  const [initialValidationDone, setInitialValidationDone] = useState(false);
  
  // Ref to track validation in progress to avoid race conditions
  const validationInProgress = useRef(false);

  // Get ALL displayed course codes (for validation purposes)
  const getAllDisplayedCodes = useCallback((): Set<string> => {
    return new Set<string>([
      ...Array.from(allIncomingTransfer).map(normalizeCode),
      ...Array.from(allIncomingTest).map(normalizeCode),
      ...Array.from(allEmory).map(normalizeCode),
      ...Array.from(allSpring2026).map(normalizeCode),
    ]);
  }, [allIncomingTransfer, allIncomingTest, allEmory, allSpring2026]);

  // All selected course codes (normalized) - for prereq checking
  const getAllSelectedCodes = useCallback((): Set<string> => {
    return new Set<string>([
      ...Array.from(selIncomingTransfer).map(normalizeCode),
      ...Array.from(selIncomingTest).map(normalizeCode),
      ...Array.from(selEmory).map(normalizeCode),
      ...Array.from(selSpring2026).map(normalizeCode),
    ]);
  }, [selIncomingTransfer, selIncomingTest, selEmory, selSpring2026]);

  // Validate a single course's prerequisites
  const validateCoursePrereqs = useCallback((courseCode: string, selectedCodes: Set<string>): CourseValidation => {
    const norm = normalizeCode(courseCode);
    const exists = courseExistence[norm]; // Can be undefined, true, or false
    const prereqGroups = prereqMap[norm] || [];
    
    const prereqDetails: CourseValidation["prereqDetails"] = [];
    const missingPrereqs: string[] = [];
    
    // Only check prereqs if course exists
    if (exists === true) {
      for (const orGroup of prereqGroups) {
        if (!orGroup || orGroup.length === 0) continue;
        
        let satisfied = false;
        let satisfiedBy: string | undefined;
        
        for (const prereqCode of orGroup) {
          const prereqNorm = normalizeCode(prereqCode);
          if (selectedCodes.has(prereqNorm)) {
            satisfied = true;
            satisfiedBy = prereqNorm;
            break;
          }
        }
        
        prereqDetails.push({
          group: orGroup,
          satisfied,
          satisfiedBy
        });
        
        if (!satisfied) {
          orGroup.forEach(p => {
            const pNorm = normalizeCode(p);
            if (!missingPrereqs.includes(pNorm)) {
              missingPrereqs.push(pNorm);
            }
          });
        }
      }
    }
    
    return { exists, missingPrereqs, prereqDetails };
  }, [prereqMap, courseExistence]);

  // Recursively collect all missing prerequisites
  const collectAllMissingPrereqs = useCallback((
    courseCode: string,
    selectedCodes: Set<string>,
    visited: Set<string> = new Set()
  ): Set<string> => {
    const norm = normalizeCode(courseCode);
    if (visited.has(norm)) return new Set();
    visited.add(norm);
    
    const validation = validateCoursePrereqs(courseCode, selectedCodes);
    const allMissing = new Set<string>();
    
    validation.missingPrereqs.forEach(p => allMissing.add(p));
    
    for (const prereqCode of validation.missingPrereqs) {
      const nested = collectAllMissingPrereqs(prereqCode, selectedCodes, visited);
      nested.forEach(p => allMissing.add(p));
    }
    
    return allMissing;
  }, [validateCoursePrereqs]);

  // Validate ALL displayed courses (not just selected) - this runs on load
  useEffect(() => {
    const allDisplayedCodes = getAllDisplayedCodes();
    const codesToCheck = Array.from(allDisplayedCodes);
    
    if (codesToCheck.length === 0) {
      setPrereqMap({});
      setCourseExistence({});
      setInitialValidationDone(true);
      return;
    }

    // Don't re-run if already in progress
    if (validationInProgress.current) return;

    const validateAllCourses = async () => {
      validationInProgress.current = true;
      setValidatingCourses(true);
      setValidationError(null);
      
      const seen = new Set<string>();
      const graph: PrereqMap = {};
      const existence: CourseExistenceMap = {};
      
      // Initialize all codes as undefined (pending)
      codesToCheck.forEach(code => {
        existence[code] = undefined;
      });
      setCourseExistence(prev => ({ ...prev, ...existence }));
      
      let toVisit = codesToCheck.map(normalizeCode);
      const maxDepth = 5;

      for (let depth = 0; depth < maxDepth && toVisit.length > 0; depth++) {
        const batch = Array.from(new Set(toVisit)).filter((code) => !seen.has(code));
        if (batch.length === 0) break;
        batch.forEach((code) => seen.add(code));

        try {
          console.log(`Validating batch (depth ${depth}):`, batch);
          const res = await fetch(
            `${API_URL}/api/course-prereqs?codes=${encodeURIComponent(batch.join(","))}`
          );
          
          if (!res.ok) {
            throw new Error(`API returned ${res.status}: ${res.statusText}`);
          }
          
          const data = await res.json();
          console.log("API response:", data);
          
          if (data.success && data.prereqs) {
            // Use explicit existence map if provided
            if (data.exists) {
              Object.entries<any>(data.exists).forEach(([key, val]) => {
                existence[normalizeCode(key)] = Boolean(val);
              });
            }
            // Capture prereq graph regardless of existence (may be empty for missing)
            Object.entries<any>(data.prereqs).forEach(([key, val]) => {
              const normKey = normalizeCode(key);
              if (Array.isArray(val)) {
                graph[normKey] = val as string[][];
              }
              // If existence not set yet, assume true when returned
              if (existence[normKey] === undefined) {
                existence[normKey] = true;
              }
            });

            setCourseExistence(prev => ({ ...prev, ...existence }));
          } else {
            console.warn("API response missing prereqs:", data);
            setCourseExistence(prev => ({ ...prev, ...existence }));
          }
        } catch (err) {
          console.error("Failed to fetch prerequisites:", err);
          setValidationError(`Failed to validate courses: ${err instanceof Error ? err.message : 'Unknown error'}`);
          // On error, mark remaining as unknown (leave as undefined) so they show as pending
          // Don't mark them as false - we don't know if they exist or not
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
      setCourseExistence(prev => ({ ...prev, ...existence }));
      setValidatingCourses(false);
      setInitialValidationDone(true);
      validationInProgress.current = false;
    };

    validateAllCourses();
  }, [allIncomingTransfer, allIncomingTest, allEmory, allSpring2026, getAllDisplayedCodes]);

  // Calculate missing prerequisites for all selected courses
  const allMissingPrereqs = (() => {
    const selectedCodes = getAllSelectedCodes();
    const allMissing = new Set<string>();
    
    selectedCodes.forEach(code => {
      const missing = collectAllMissingPrereqs(code, selectedCodes);
      missing.forEach(m => {
        if (!selectedCodes.has(m)) {
          allMissing.add(m);
        }
      });
    });
    
    return Array.from(allMissing).sort();
  })();

  // Courses that don't exist in MongoDB (only show after validation is done)
  const nonExistentCourses = (() => {
    if (!initialValidationDone) return [];
    const allCodes = getAllDisplayedCodes();
    return Array.from(allCodes).filter(code => courseExistence[normalizeCode(code)] === false);
  })();

  useEffect(() => {
    // Require a fresh acknowledgement whenever the transcript or missing prereq set changes
    setAcknowledgePrereqRisk(false);
  }, [selected, allMissingPrereqs.length]);

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
        const inTransfer = new Set(parsed.incoming_transfer_courses || []);
        const inTest = new Set(parsed.incoming_test_courses || []);
        const inEmory = new Set(parsed.emory_courses || []);
        const inSpring = new Set(parsed.spring_2026_courses || []);

        setAllIncomingTransfer(inTransfer);
        setAllIncomingTest(inTest);
        setAllEmory(inEmory);
        setAllSpring2026(inSpring);

        setSelIncomingTransfer(new Set(inTransfer));
        setSelIncomingTest(new Set(inTest));
        setSelEmory(new Set(inEmory));
        setSelSpring2026(new Set(inSpring));
        
        // Reset validation state for new transcript
        setCourseExistence({});
        setPrereqMap({});
        setInitialValidationDone(false);
        validationInProgress.current = false;
        
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
      setAllIncomingTransfer(new Set());
      setAllIncomingTest(new Set());
      setAllEmory(new Set());
      setAllSpring2026(new Set());
      setSelIncomingTransfer(new Set());
      setSelIncomingTest(new Set());
      setSelEmory(new Set());
      setSelSpring2026(new Set());
      setCourseExistence({});
      setPrereqMap({});
      setInitialValidationDone(false);
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

  // Toggle function - toggles between selected (green) and deselected (red)
  function toggle(setter: React.Dispatch<React.SetStateAction<Set<string>>>, code: string) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  }

  function handleAdd(setter: React.Dispatch<React.SetStateAction<Set<string>>>, value: string, allSetter?: React.Dispatch<React.SetStateAction<Set<string>>>) {
    const code = normalizeCode(value.trim());
    if (!code) return;
    setter((prev) => {
      const next = new Set(prev);
      next.add(code);
      return next;
    });
    if (allSetter) {
      allSetter((prev) => {
        const next = new Set(prev);
        next.add(code);
        return next;
      });
    }
    // Mark as needing validation
    setCourseExistence(prev => {
      if (prev[code] === undefined) {
        return { ...prev, [code]: undefined };
      }
      return prev;
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
    if (!uid) {
      setPostedOk(false);
      setPostError("Not signed in");
      return;
    }

    sendToBackendSeparated(
      incoming_transfer_courses,
      incoming_test_courses,
      emory_courses,
      spring_2026_courses
    );
  }

  // Display arrays: include all known codes (manual + parsed) so deselected stay visible
  const displayIncomingTransfer = Array.from(new Set(allIncomingTransfer));
  const displayIncomingTest = Array.from(new Set(allIncomingTest));
  const displayEmory = Array.from(new Set(allEmory));
  const displaySpring2026 = Array.from(new Set(allSpring2026));

  // Chip component with validation status
  function Chip({ 
    code, 
    isSelected, 
    onClick 
  }: { 
    code: string; 
    isSelected: boolean; 
    onClick: () => void;
  }) {
    const norm = normalizeCode(code);
    const existenceStatus = courseExistence[norm]; // undefined = pending, true = exists, false = doesn't exist
    const selectedCodes = getAllSelectedCodes();
    const validation = validateCoursePrereqs(code, selectedCodes);
    const hasMissingPrereqs = validation.missingPrereqs.length > 0;
    
    // Determine chip style based on validation state
    let chipStyle = "";
    let statusIndicator = null;
    
    if (existenceStatus === undefined) {
      // Still validating or not checked yet - show neutral/pending state
      chipStyle = "border-zinc-300 bg-zinc-50 text-zinc-600";
      if (validatingCourses) {
        statusIndicator = (
          <span className="ml-1 text-zinc-400" title="Validating...">
            <Loader2 className="h-3 w-3 inline animate-spin" />
          </span>
        );
      }
    } else if (existenceStatus === false) {
      // Course doesn't exist in MongoDB - keep warning icon but allow deselect state to show red
      statusIndicator = (
        <span className="ml-1 text-orange-600" title="Course not found in database">
          <AlertTriangle className="h-3 w-3 inline" />
        </span>
      );
      chipStyle = isSelected
        ? "border-orange-400 bg-orange-50 text-orange-800 ring-2 ring-orange-300 ring-opacity-50"
        : "border-rose-300 bg-rose-50 text-rose-700 ring-2 ring-orange-200 ring-opacity-60 hover:bg-rose-100";
    } else if (isSelected) {
      // Course exists and is selected
      if (hasMissingPrereqs) {
        // Selected but missing prereqs - yellow warning
        chipStyle = "border-amber-400 bg-amber-50 text-amber-800";
        statusIndicator = (
          <span className="ml-1 text-amber-600" title={`Missing: ${validation.missingPrereqs.join(" or ")}`}>
            <AlertCircle className="h-3 w-3 inline" />
          </span>
        );
      } else {
        // Selected and valid - green
        chipStyle = "border-green-300 bg-green-50 text-green-800 hover:bg-green-100";
      }
    } else {
      // Deselected - red
      chipStyle = "border-rose-300 bg-rose-50 text-rose-700 hover:bg-rose-100";
    }
    
    return (
      <button
        type="button"
        onClick={onClick}
        className={`rounded-md border px-2.5 py-2 text-sm shadow-sm transition-colors flex items-center ${chipStyle}`}
        title={
          existenceStatus === undefined
            ? "Validating course..."
            : existenceStatus === false
              ? "Course not found in MongoDB database" 
              : isSelected 
                ? hasMissingPrereqs 
                  ? `Selected - Missing prereqs: ${validation.missingPrereqs.join(" or ")}` 
                  : "Selected (will send)" 
                : "Deselected (won't send)"
        }
      >
        {code}
        {statusIndicator}
      </button>
    );
  }

  const totalSelected =
    selIncomingTransfer.size +
    selIncomingTest.size +
    selEmory.size +
    selSpring2026.size;
  const requiresPrereqAck = initialValidationDone && allMissingPrereqs.length > 0;
  const nothingSelected =
    !selIncomingTransfer.size &&
    !selIncomingTest.size &&
    !selEmory.size &&
    !selSpring2026.size;
  const disableSubmit =
    posting || nothingSelected || (requiresPrereqAck && !acknowledgePrereqRisk);

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-Gold">
            <img src={applogo} alt="DooleyHelpz" className="h-6 w-6 object-contain" />
          </div>
          <span className="text-lg font-semibold text-emoryBlue">DooleyHelpz</span>
        </Link>

        <button
          onClick={() => navigate("/dashboard")}
          className="rounded-xl bg-lighterBlue px-3 py-1.5 text-sm font-semibold text-white hover:bg-emoryBlue/90"
        >
          Back to Dashboard
        </button>
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

        <div className="mb-8 rounded-2xl border border-zinc-200 bg-gradient-to-br from-emoryBlue/5 via-white to-paleGold/20 p-6 shadow-sm">
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
    <h2 className="mb-3 text-xl font-semibold text-emoryBlue">Recently Uploaded. Only the most recent .pdf is shown, you can't stack multiple for combined results.</h2>
    <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white shadow-sm">
      <table className="min-w-full text-sm">
        <thead className="bg-zinc-100 text-zinc-700">
          <tr>
            <th className="px-4 py-2 text-left">File</th>
            <th className="px-4 py-2 text-left">Size</th>
            <th className="px-4 py-2 text-left">Uploaded</th>
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
          </section>
        )}

        {/* Validation status banner */}
        {selected && buckets && validatingCourses && (
          <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
            <div className="flex items-center gap-2 text-blue-700">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="font-medium">Validating courses against database...</span>
            </div>
            <p className="mt-1 text-sm text-blue-600">
              This may take a moment. Courses will update as validation completes.
            </p>
          </div>
        )}

        {/* Validation error banner */}
        {validationError && (
          <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
            <div className="flex items-center gap-2 text-rose-700">
              <AlertCircle className="h-5 w-5" />
              <span className="font-medium">Validation Error</span>
            </div>
            <p className="mt-1 text-sm text-rose-600">{validationError}</p>
            <p className="mt-1 text-xs text-rose-500">
              Course validation may be incomplete. You can still submit, but some courses may not be verified.
            </p>
          </div>
        )}

        {/* Validation warnings - only show after initial validation is done */}
        {initialValidationDone && (nonExistentCourses.length > 0 || allMissingPrereqs.length > 0) && (
          <div className="mb-6 space-y-3">
            {nonExistentCourses.length > 0 && (
              <div className="rounded-lg border border-orange-300 bg-orange-50 px-4 py-3">
                <div className="flex items-center gap-2 text-orange-800">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-semibold">Courses not found in database:</span>
                </div>
                <p className="mt-1 text-sm text-orange-700">
                  {nonExistentCourses.join(", ")}
                </p>
                <p className="mt-1 text-xs text-orange-600">
                  These courses may be misspelled or not offered: these courses didn't exist on Altas (Atlanta campus only) from 2019-2025. 
                </p>
              </div>
            )}
            
            {allMissingPrereqs.length > 0 && (
              <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3">
                <div className="flex items-center gap-2 text-amber-800">
                  <AlertCircle className="h-5 w-5" />
                  <span className="font-semibold">Suggested prerequisites to add:</span>
                </div>
                <p className="mt-1 text-sm text-amber-700">
                  {allMissingPrereqs.join(", ")}
                </p>
                <p className="mt-1 text-xs text-amber-600">
                  Some selected courses require these prerequisites. Add them if you've completed them.
                </p>
                <label className="mt-3 flex items-start gap-2 text-xs text-amber-700">
                  <input
                    type="checkbox"
                    checked={acknowledgePrereqRisk}
                    onChange={(e) => setAcknowledgePrereqRisk(e.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-amber-300 text-emoryBlue focus:ring-emoryBlue"
                  />
                  <span className="leading-tight">
                    I believe my course codes are correct and accept that schedule recommendations may be wrong if these
                    prerequisites are missing.
                  </span>
                </label>
              </div>
            )}
          </div>
        )}

        {selected && buckets && (
          <section className="grid gap-6 md:grid-cols-2">
            {/* Incoming Transfer */}
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
                      handleAdd(setSelIncomingTransfer, transferInput, setAllIncomingTransfer);
                      setTransferInput("");
                    }
                  }}
                  placeholder="e.g. CHEM150"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelIncomingTransfer, transferInput, setAllIncomingTransfer);
                    setTransferInput("");
                  }}
                  className="rounded-md bg-emoryBlue px-3 py-1 text-sm text-white hover:bg-emoryBlue/90"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Incoming Test */}
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
                      handleAdd(setSelIncomingTest, testInput, setAllIncomingTest);
                      setTestInput("");
                    }
                  }}
                  placeholder="e.g. PSYC111"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelIncomingTest, testInput, setAllIncomingTest);
                    setTestInput("");
                  }}
                  className="rounded-md bg-emoryBlue px-3 py-1 text-sm text-white hover:bg-emoryBlue/90"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Spring 2026 */}
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
                      handleAdd(setSelSpring2026, springInput, setAllSpring2026);
                      setSpringInput("");
                    }
                  }}
                  placeholder="e.g. BUS494"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelSpring2026, springInput, setAllSpring2026);
                    setSpringInput("");
                  }}
                  className="rounded-md bg-emoryBlue px-3 py-1 text-sm text-white hover:bg-emoryBlue/90"
                >
                  Add
                </button>
              </div>
            </div>

            {/* Emory */}
            <div className="md:col-span-2">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emoryBlue">Emory — Academic Record</h2>
                <div className="flex items-center gap-2">
                  {validatingCourses && (
                    <span className="flex items-center gap-1 text-xs text-zinc-500">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Validating...
                    </span>
                  )}
                  <span className="text-sm text-zinc-600">{selEmory.size} selected</span>
                </div>
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
                      handleAdd(setSelEmory, emoryInput, setAllEmory);
                      setEmoryInput("");
                    }
                  }}
                  placeholder="e.g. CS377"
                  className="rounded-md border px-2 py-1 text-sm"
                />
                <button
                  type="button"
                  onClick={() => {
                    handleAdd(setSelEmory, emoryInput, setAllEmory);
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
              {requiresPrereqAck && !acknowledgePrereqRisk && (
                <span className="ml-2 inline-flex items-center gap-1 rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                  <AlertCircle className="h-3.5 w-3.5" /> Acknowledge missing prerequisites to continue
                </span>
              )}
            </div>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={disableSubmit}
              className={
                "inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold shadow-sm " +
                (disableSubmit
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

        {/* Legend */}
        <div className="mt-6 rounded-xl border border-zinc-200 bg-white p-4">
          <h3 className="text-sm font-semibold text-emoryBlue mb-2">Legend</h3>
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded border border-green-300 bg-green-50"></div>
              <span>Selected (will be saved)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded border border-rose-300 bg-rose-50"></div>
              <span>Deselected (won't be saved)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded border border-amber-400 bg-amber-50"></div>
              <span>Missing prerequisites</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rounded border-2 border-orange-400 bg-orange-50 ring-2 ring-orange-300 ring-opacity-50"></div>
              <span>Not found in database</span>
            </div>
          </div>
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
