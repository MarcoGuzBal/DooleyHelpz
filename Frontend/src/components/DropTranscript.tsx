import React, { useRef, useState } from "react";
import { getDocument} from "pdfjs-dist";
import * as pdfjsLib from "pdfjs-dist";
import type { TextItem } from "pdfjs-dist/types/src/display/api";
import workerSrc from "pdfjs-dist/build/pdf.worker?url";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc;

export default function DropTranscript() {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  async function handleFile(file: File) {
    try {
        setError(null);
        setText("");
        if (file.type !=="application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
            setError("Please choose a PDF (.pdf).");
            return;
        }
        const buf = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: new Uint8Array(buf) }).promise;

        let all = ""
        let pagesWithText = 0;

        for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const content = await page.getTextContent();
            const strings = content.items.map((it) => (it as TextItem).str).filter(Boolean);
            if (strings.length) pagesWithText++;
            all += strings.join(" ") + "\n";
        }

        if (pagesWithText / pdf.numPages < 0.3) {
            setError("This looks like a scanned PDF (no text layer). Try a native registrar PDF or run OCR.");
        }
        
        setText(all.trim());
    }
    catch(e: any) {
        setError(e?.message || "Failed to read PDF.");
    }

    // assume `text` contains your raw extracted string (from PDF.js)
    const raw = (text || "").replace(/\s+/g, " ").trim();

    // 1) split into chunks on boundaries like "BUS 290", "CS 171", "SPAN 302W", etc.
    const chunks = raw
    .split(/(?=(?:[A-Z&]{2,6}\s+\d{3,4}[A-Z]?)(?:\s|$))/g) // lookahead split
    .map(s => s.trim())
    .filter(s => s.length > 0);

    // 2) regex to capture: number, title, grade
    // Layout seen in your sample:
    // BUS   290   Tech Toolbox A: Excel   1.000   1.000   S   0.000
    // dept + number + title + attempted + earned + grade + qualityPoints
    const rx = new RegExp(
    String.raw`^[A-Z&]{2,6}\s+(?<num>\d{3,4}[A-Z]?)\s+(?<title>.+?)\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+(?<grade>[A-F][+\-]?|P|S|U|I|W)\s+\d+(?:\.\d+)?$`
    );

    // 3) parse into minimal fields (privacy-safe)
    type CourseMin = { number: string; name: string; grade: string };

    const courses: CourseMin[] = [];
    for (let i = 0; i < chunks.length; i++) {
    const m = chunks[i].match(rx);
    if (m && m.groups) {
        const number = m.groups["num"];
        const name = m.groups["title"].trim();
        const grade = m.groups["grade"];
        courses.push({ number, name, grade });
    }
    }

    // `courses` now has only the fields you want
    console.log(courses);

  }

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", padding: 16 }}>
      <h1>Transcript text extractor</h1>
      <p>Drop a PDF or click below.</p>

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
          marginBottom: 16
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

      {error && <div style={{ color: "#a00", marginBottom: 12 }}>{error}</div>}

      {text && (
        <div>
          <h3>Raw text</h3>
          <pre style={{ whiteSpace: "pre-wrap", background: "#f7f7f7", padding: 12, borderRadius: 8, maxHeight: 400, overflow: "auto" }}>
            {text}
          </pre>
        </div>
      )}
    </div>
  )
}

