export type ParseResult = {
  incoming_transfer_courses: string[]; // from "Transfer Credits" → "... as DEPT NUM[SUF] ... T"
  incoming_test_courses: string[];     // from "Test Credits" → "... as DEPT NUM[SUF] ... T"
  emory_courses: string[];             // from "Beginning of Academic Record", filtered by grade
};

export function parseTranscript(rawText: string): ParseResult {
  if (!rawText) {
    return {
      incoming_transfer_courses: [],
      incoming_test_courses: [],
      emory_courses: [],
    };
  }

  // --- Normalize ---
  const text = String(rawText)
    .replace(/\r/g, " ")
    .replace(/\n/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const lower = text.toLowerCase();

  // --- Anchor positions (case-insensitive) ---
  const transferIdx  = lower.indexOf("transfer credits");
  const testIdx      = lower.indexOf("test credits");
  const academicIdx  = lower.indexOf("beginning of academic record");

  // Helper: slice a section that starts at `start` and ends at the nearest subsequent anchor
  function sliceSection(start: number): string {
    if (start < 0) return "";
    const ends: number[] = [];
    if (transferIdx >= 0 && transferIdx > start) ends.push(transferIdx);
    if (testIdx >= 0 && testIdx > start) ends.push(testIdx);
    if (academicIdx >= 0 && academicIdx > start) ends.push(academicIdx);
    const end = ends.length ? Math.min(...ends) : text.length;
    return text.slice(start, end);
  }

  const transferSection = sliceSection(transferIdx); // only Transfer block
  const testSection     = sliceSection(testIdx);     // only Test block
  const academicSection = academicIdx >= 0 ? text.slice(academicIdx) : "";

  // --- Patterns ---
  // Course code: DEPT + number + optional suffix (e.g., QTM 999XFR, CHEM 150L, SPAN 302W, MATH 112Z)
  const codeRe = /\b([A-Z&]{2,6})\s+(\d{3,4})([A-Z]{0,3})\b/g;

  // Accept only likely course numbers (filters out MAC 2022 / MIC 2022, etc.)
  function isLikelyCourse(dept: string, numStr: string, suf: string): boolean {
    const n = parseInt(numStr, 10);
    // 3-digit standard undergrad, allow 100–699
    if (numStr.length === 3) {
      if (n === 999) return suf === "XFR"; // special case: 999XFR only
      return n >= 100 && n <= 699;
    }
    // reject 4-digit numbers (years) by default
    return false;
  }

  // Does "as" appear right before this code occurrence?
  function hasAsBefore(hay: string, codeStartIdx: number): boolean {
    const windowStart = Math.max(0, codeStartIdx - 40);
    const snippet = hay.slice(windowStart, codeStartIdx).toLowerCase();
    // tolerate extra spaces
    return /\bas\s*$/.test(snippet.trimEnd()) || snippet.includes(" as ");
  }

  // Academic grade tokens
  const gradeTokenRe = /\b(W|S|U|F|[A-D][+-]?)\b/;
  function isFailOrWithdraw(grade: string): boolean {
    const g = grade.toUpperCase();
    if (g === "W" || g === "U" || g === "F") return true;
    if (g === "D" || g === "D+" || g === "D-") return true; // below C-
    return false;
  }

  // Extract destination codes from an "incoming" section (Transfer or Test)
  function extractIncoming(section: string): string[] {
    if (!section) return [];
    const out = new Set<string>();
    let m: RegExpExecArray | null;
    while ((m = codeRe.exec(section)) !== null) {
      const dept = m[1];
      const num  = m[2];
      const suf  = m[3] || "";
      if (!isLikelyCourse(dept, num, suf)) continue;

      const code = `${dept}${num}${suf}`;
      const codeStart = m.index;

      // Destination codes usually satisfy:
      //  (a) immediately follows "as", or
      //  (b) followed soon by a standalone 'T' (transfer notation)
      const afterAs = hasAsBefore(section, codeStart);

      const lookaheadStart = codeRe.lastIndex;
      const lookaheadEnd = Math.min(lookaheadStart + 120, section.length);
      const windowText = section.slice(lookaheadStart, lookaheadEnd);
      const hasT = /\bT\b/.test(windowText);

      if (afterAs || hasT) out.add(code);
    }
    return Array.from(out);
  }

  // Extract Emory courses from the academic section with grade filtering
  function extractEmory(section: string): string[] {
    if (!section) return [];
    const out = new Set<string>();
    let m: RegExpExecArray | null;
    while ((m = codeRe.exec(section)) !== null) {
      const dept = m[1];
      const num  = m[2];
      const suf  = m[3] || "";
      if (!isLikelyCourse(dept, num, suf)) continue;

      const code = `${dept}${num}${suf}`;
      const lookaheadStart = codeRe.lastIndex;
      const lookaheadEnd = Math.min(lookaheadStart + 120, section.length);
      const windowText = section.slice(lookaheadStart, lookaheadEnd);
      const gradeMatch = windowText.match(gradeTokenRe);

      if (gradeMatch) {
        const g = gradeMatch[1];
        if (!isFailOrWithdraw(g)) out.add(code);
      } else {
        // In-progress (no grade token yet) → include
        out.add(code);
      }
    }
    return Array.from(out);
  }

  const incoming_transfer_courses = extractIncoming(transferSection);
  const incoming_test_courses     = extractIncoming(testSection);

  const incomingAllSet = new Set<string>([
    ...incoming_transfer_courses,
    ...incoming_test_courses,
  ]);

  let emory_courses = extractEmory(academicSection)
    .filter((c) => !incomingAllSet.has(c)); // defensive de-dupe vs incoming

  return {
    incoming_transfer_courses,
    incoming_test_courses,
    emory_courses,
  };
}


