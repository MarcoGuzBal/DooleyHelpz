export type ParseResult = {
  incoming_courses: string[];
  emory_courses: string[];
};

export function parseTranscript(rawText: string): ParseResult {
  if (!rawText) return { incoming_courses: [], emory_courses: [] };

  // ---- Normalize whitespace ----
  const text = String(rawText)
    .replace(/\r/g, " ")
    .replace(/\n/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  const lower = text.toLowerCase();

  // ---- Section anchors (case-insensitive) ----
  const transferStart = lower.indexOf("transfer credits");
  const testStart = lower.indexOf("test credits");
  const academicStart = lower.indexOf("beginning of academic record");

  // Earliest start among Transfer/Test (if either exists)
  const starts: number[] = [];
  if (transferStart >= 0) starts.push(transferStart);
  if (testStart >= 0) starts.push(testStart);
  const incomingStart = starts.length ? Math.min(...starts) : -1;

  // Region that contains Transfer + Test credits (everything before Academic)
  const incomingRegion =
    incomingStart !== -1
      ? (academicStart !== -1 ? text.slice(incomingStart, academicStart) : text.slice(incomingStart))
      : ""; // none found

  // Region that contains the academic record
  const academicRegion =
    academicStart !== -1
      ? text.slice(academicStart)
      : // if Academic not found, be conservative: nothing is "Emory"
        "";

  // ---- Patterns ----
  // Course code: DEPT + number + optional suffix (e.g., QTM 999XFR, CHEM 150L, SPAN 302W, MATH 112Z)
  const codeRe = /\b([A-Z&]{2,6})\s+(\d{3,4})([A-Z]{0,3})\b/g;

  // Look-behind helper: does " as " appear shortly before this code?
  function hasAsBefore(hay: string, codeStartIdx: number): boolean {
    const windowStart = Math.max(0, codeStartIdx - 40);
    const snippet = hay.slice(windowStart, codeStartIdx).toLowerCase();
    // require word-boundary-ish " as "
    return /\bas\s*$/.test(snippet.trimEnd()) || snippet.includes(" as ");
  }

  // Grade tokens in academic region
  const gradeTokenRe = /\b(W|S|U|F|[A-D][+-]?)\b/; // captures A, A-, ..., D-, F, S, U, W

  function isFailOrWithdraw(grade: string): boolean {
    const g = grade.toUpperCase();
    if (g === "W" || g === "U" || g === "F") return true;
    if (g === "D" || g === "D+" || g === "D-") return true;
    return false;
  }

  // ---- INCOMING extraction (from Transfer + Test region) ----
  // Keep codes that either:
  //  (a) appear right after an "as" phrase, OR
  //  (b) have a nearby standalone "T" within ~120 chars after the code (transfer notation)
  const incomingSet = new Set<string>();
  if (incomingRegion) {
    let m: RegExpExecArray | null;
    while ((m = codeRe.exec(incomingRegion)) !== null) {
      const dept = m[1];
      const num = m[2];
      const suf = m[3] || "";
      const code = `${dept}${num}${suf}`;
      const codeStart = m.index;

      // (a) check "as" just before the code
      const isAfterAs = hasAsBefore(incomingRegion, codeStart);

      // (b) check for ' T ' soon after the code (transfer credit marker)
      const lookaheadStart = codeRe.lastIndex;
      const lookaheadEnd = Math.min(lookaheadStart + 120, incomingRegion.length);
      const windowText = incomingRegion.slice(lookaheadStart, lookaheadEnd);
      const hasT = /\bT\b/.test(windowText); // standalone T

      if (isAfterAs || hasT) {
        incomingSet.add(code);
      }
    }
  }

  // ---- EMORY extraction (from Academic region) ----
  const emorySet = new Set<string>();
  if (academicRegion) {
    let m: RegExpExecArray | null;
    while ((m = codeRe.exec(academicRegion)) !== null) {
      const dept = m[1];
      const num = m[2];
      const suf = m[3] || "";
      const code = `${dept}${num}${suf}`;

      // Look ahead for a grade token near the course entry
      const lookaheadStart = codeRe.lastIndex;
      const lookaheadEnd = Math.min(lookaheadStart + 120, academicRegion.length);
      const windowText = academicRegion.slice(lookaheadStart, lookaheadEnd);
      const gradeMatch = windowText.match(gradeTokenRe);

      if (gradeMatch) {
        const g = gradeMatch[1];
        if (!isFailOrWithdraw(g)) {
          emorySet.add(code);
        }
      } else {
        // No grade token → in-progress → include
        emorySet.add(code);
      }
    }
  }

  // Remove any code that also appears as incoming (defensive)
  for (const c of incomingSet) emorySet.delete(c);

  return {
    incoming_courses: Array.from(incomingSet),
    emory_courses: Array.from(emorySet),
  };
}

