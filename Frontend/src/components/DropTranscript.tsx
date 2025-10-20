// src/DropTranscript.tsx
import React, { useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerSrc from "pdfjs-dist/build/pdf.worker?url"; // Vite-friendly worker URL
import type { TextItem } from "pdfjs-dist/types/src/display/api";
import { parseTranscript, type ParsedCourse } from "../utils/parseTranscript";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

export default function DropTranscript() {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [text, setText] = useState("");
  const [courses, setCourses] = useState<ParsedCourse[]>([]);
  const [unparsed, setUnparsed] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [pagesWithText, setPagesWithText] = useState(0);
  const [numPages, setNumPages] = useState(0);

  async function handleFile(file: File) {
    try {
      setError(null);
      setLoading(true);
      setText("");
      setCourses([]);
      setUnparsed([]);
      setPagesWithText(0);
      setNumPages(0);

      if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
        setError("Please choose a PDF (.pdf).");
        return;
      }

      const buf = await file.arrayBuffer();
      const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(buf) }).promise;
      setNumPages(pdf.numPages);

      let all = "";
      let pages = 0;

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

      // ⬇️ use the new parser + types
      const { courses, unparsed } = parseTranscript(clean);
      setCourses(courses);
      setUnparsed(unparsed);
    } catch (e: any) {
      setError(e?.message || "Failed to read PDF.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", padding: 16 }}>
      <h1>Drop Transcript (Dept • Number • Course • Grade)</h1>
      <p>Parsed locally in-browser. Planned/no-grade rows are hidden by default.</p>

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

      {courses.length > 0 && (
        <>
          <h3>Parsed</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 12 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Dept</th>
                <th style={{ textAlign: "left" }}>Number</th>
                <th style={{ textAlign: "left" }}>Course</th>
                <th style={{ textAlign: "left" }}>Grade</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((c, i) => (
                <tr key={i}>
                  <td>{c.dept ?? ""}</td>
                  <td>{c.number}</td>
                  <td>{c.name}</td>
                  <td>{c.grade}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {unparsed.length > 0 && (
        <>
          <h4 style={{ marginTop: 16 }}>Unparsed course-like lines (for tweaking)</h4>
          <ul>
            {unparsed.slice(0, 20).map((l, i) => (
              <li key={i}>
                <code>{l}</code>
              </li>
            ))}
          </ul>
        </>
      )}

      {text && (
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
      )}
    </div>
  );
}



