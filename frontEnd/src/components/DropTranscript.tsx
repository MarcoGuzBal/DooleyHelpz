// src/DropTranscript.tsx
import React, { useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerSrc from "pdfjs-dist/build/pdf.worker?url"; // Vite-friendly worker URL
import type { TextItem } from "pdfjs-dist/types/src/display/api";
import { parseTranscript } from "../utils/parseTranscript";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

export default function DropTranscript() {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [text, setText] = useState("");
  const [courseCodes, setCourseCodes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pagesWithText, setPagesWithText] = useState(0);
  const [numPages, setNumPages] = useState(0);
  const [postedOk, setPostedOk] = useState<null | boolean>(null);

  async function handleFile(file: File) {
    try {
      // Reset UI if new file is uploaded
      setError(null);
      setPostedOk(null);
      setLoading(true);
      setText("");
      setCourseCodes([]);
      setPagesWithText(0);
      setNumPages(0);
      
      // Validates that the file is a PDF
      if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
        setError("Please choose a PDF (.pdf).");
        return;
      }

      
      const buf = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(buf) }).promise;
      setNumPages(pdf.numPages);

      let all = ""; // The entire text
      let pages = 0; // Num of Pages

      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        const strings = (content.items as TextItem[]).map((it) => it.str).filter(Boolean);
        if (strings.length) pages++;
        all += strings.join(" ") + "\n";
      }

      setPagesWithText(pages);

      if (pages / pdf.numPages < 0.3) {
        setError("This looks like a scanned PDF (no text layer). Try a native registrar PDF or run OCR.");
      }

      const clean = all.trim();
      setText(clean);

      // only extract codes like "CS170", "ECON101", etc.
      const codes = parseTranscript(clean);
      setCourseCodes(codes);
      sendToBackend(codes);
    } catch (e: any) {
      setError(e?.message || "Failed to read PDF.");
    } finally {
      setLoading(false);
    }
  }

  async function sendToBackend(codes) {
    try {
      setPostedOk(null);
      console.log(codes)
      const res = await fetch("http://localhost:5001/api/userCourses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ courses: codes }),
      });
      setPostedOk(res.ok);
      if (!res.ok) throw new Error(`Backend responded ${res.status}`);
    } catch (err: any) {
      setPostedOk(false);
      alert(err?.message || "Failed to send to backend");
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", padding: 16 }}>
      <h1>Drop Transcript → Course Codes Only</h1>
      <p>We extract only course identifiers like <code>CS170</code>, <code>ECON112</code>, etc. (including transfer/AP).</p>

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        onClick={() => inputRef.current?.click()}
        style={{
          border: "2px dashed #ccc",
          borderRadius: 12,
          padding: 24,
          textAlign: "center",
          cursor: "pointer",
          marginBottom: 16,
        }}
      >
        Drop PDF here or click to choose
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </div>

      {loading && <div>Extracting text…</div>}
      {error && <div style={{ color: "#a00", marginBottom: 12 }}>{error}</div>}

      {numPages > 0 && (
        <div style={{ marginBottom: 12, color: "#555" }}>
          Pages: {numPages} • Pages with text: {pagesWithText}
        </div>
      )}

      {courseCodes.length > 0 && (
        <>
          <div style={{ marginBottom: 8 }}>
            <strong>Found {courseCodes.length}</strong> unique course codes
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
              gap: 8,
              marginBottom: 12,
            }}
          >
            {courseCodes.map((code) => (
              <div
                key={code}
                style={{
                  border: "1px solid #ddd",
                  borderRadius: 8,
                  padding: "8px 10px",
                  background: "#fafafa",
                }}
              >
                {code}
              </div>
            ))}
          </div>
        </>
      )}

      {/* {text && (
        <>
          <h3 style={{ marginTop: 16 }}>Raw extracted text (debug)</h3>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              background: "#f7f7f7",
              padding: 12,
              borderRadius: 8,
              maxHeight: 300,
              overflow: "auto",
            }}
          >
            {text}
          </pre>
        </>
      )} */}
    </div>
  );
}




