// src/utils/parseTranscript.ts

export type ParseResult = {
  incoming_transfer_courses: string[]; // from "Transfer Credits" → "... as DEPT NUM[SUF] ... T"
  incoming_test_courses: string[];     // from "Test Credits" → "... as DEPT NUM[SUF] ... T"
  emory_courses: string[];             // from "Beginning of Academic Record", filtered by grade
  spring_2026_courses: string[];       // planned / Spring 2026 courses (optional)
};

export function parseTranscript(rawText: string): ParseResult {
  if (!rawText) {
    return {
      incoming_transfer_courses: [],
      incoming_test_courses: [],
      emory_courses: [],
      spring_2026_courses: [],
    };
  }

  // --- Normalize ---
  const text = String(rawText)
    .replace(/\r/g, " ")
    .replace(/\n/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const lower = text.toLowerCase();

  // --- Anchor positions (case-insensitive) in full text ---
  const transferIdx   = lower.indexOf("transfer credits");
  const testIdx       = lower.indexOf("test credits");
  const academicIdx   = lower.indexOf("beginning of academic record");
  const spring2026Idx = lower.indexOf("spring 2026");

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

  const transferSection = sliceSection(transferIdx);
  const testSection     = sliceSection(testIdx);

  // Academic record section (everything from the "Beginning of Academic Record" anchor)
  const academicSection = academicIdx >= 0 ? text.slice(academicIdx) : "";

  // Now split academicSection into:
  //   - academicPreSpring: everything before "Spring 2026"
  //   - spring2026Section: starting at "Spring 2026"
  let academicPreSpring = academicSection;
  let spring2026Section = "";

  if (
    academicIdx >= 0 &&
    spring2026Idx >= 0 &&
    spring2026Idx > academicIdx
  ) {
    const offset = spring2026Idx - academicIdx; // position of "Spring 2026" inside academicSection
    academicPreSpring = academicSection.slice(0, offset);
    spring2026Section = academicSection.slice(offset);
  } else if (spring2026Idx >= 0) {
    // Found spring 2026 but no "Beginning of Academic Record" anchor — take from global
   spring2026Section = text.slice(spring2026Idx);
  }

  // --- Patterns ---
  // Course code: DEPT + number + optional suffix (e.g., QTM 999XFR, CHEM 150L, SPAN 302W, MATH 112Z)
  const codeRe = /\b([A-Z&]{2,6})\s+(\d{3,4})([A-Z]{0,3})\b/g;

  // Accept only likely course numbers (filters out years)
  function isLikelyCourse(_dept: string, numStr: string, suf: string): boolean {
    const n = parseInt(numStr, 10);
    if (numStr.length === 3) {
      if (n === 999) return suf === "XFR"; // allow 999XFR
      return n >= 100 && n <= 699;
    }
    // reject 4-digit numbers (years etc.) by default
    return false;
  }

  // Does "as" appear right before this code occurrence?
  function hasAsBefore(hay: string, codeStartIdx: number): boolean {
    const windowStart = Math.max(0, codeStartIdx - 40);
    const snippet = hay.slice(windowStart, codeStartIdx).toLowerCase();
    return /\bas\s*$/.test(snippet.trimEnd()) || snippet.includes(" as ");
  }

  // Academic grade tokens
  const gradeTokenRe = /\b(W|S|U|F|[A-D][+-]?)\b/;
  function isFailOrWithdraw(grade: string): boolean {
    const g = grade.toUpperCase();
    if (g === "W" || g === "U" || g === "F") return true;
    if (g === "D" || g === "D+" || g === "D-") return true;
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

      const afterAs = hasAsBefore(section, codeStart);

      const lookaheadStart = codeRe.lastIndex;
      const lookaheadEnd = Math.min(lookaheadStart + 120, section.length);
      const windowText = section.slice(lookaheadStart, lookaheadEnd);
      const hasT = /\bT\b/.test(windowText);

      if (afterAs || hasT) out.add(code);
    }
    return Array.from(out);
  }

  // Extract Emory courses from the *pre-Spring-2026* academic section with grade filtering
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

  // Extract all likely course codes starting at/after "Spring 2026"
  function extractSpring2026(section: string): string[] {
    if (!section) return [];
    const out = new Set<string>();
    // use a fresh RegExp to avoid shared lastIndex state from other extractors
    const re = new RegExp(codeRe.source, codeRe.flags);
    let m: RegExpExecArray | null;
    while ((m = re.exec(section)) !== null) {
      const dept = m[1];
      const num  = m[2];
      const suf  = m[3] || "";
      if (!isLikelyCourse(dept, num, suf)) continue;
      const code = `${dept}${num}${suf}`;
      out.add(code);
    }
    return Array.from(out);
  }

  const incoming_transfer_courses = extractIncoming(transferSection);
  const incoming_test_courses     = extractIncoming(testSection);

  const incomingAllSet = new Set<string>([
    ...incoming_transfer_courses,
    ...incoming_test_courses,
  ]);

  // Emory courses = academic record BEFORE Spring 2026
  let emory_courses = extractEmory(academicPreSpring)
    .filter((c) => !incomingAllSet.has(c)); // defensive de-dupe vs incoming

  // No specific extraction implemented yet for Spring 2026 planned courses;
  // provide an empty array so callers can safely reference the property.
  const spring_2026_courses: string[] = extractSpring2026(spring2026Section);

  return {
    incoming_transfer_courses,
    incoming_test_courses,
    emory_courses,
    spring_2026_courses,
  };
}



