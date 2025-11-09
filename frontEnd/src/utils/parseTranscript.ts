export type ParseResult = {
  incoming_courses: string[]; // transfer/test/AP bucket (includes "as XYZ" destination codes)
  emory_courses: string[];    // all other Emory term courses
};

export function parseTranscript(rawText: string): ParseResult {
  if (!rawText) return { incoming_courses: [], emory_courses: [] };

  // Normalize whitespace
  const text = String(rawText).replace(/\r/g, " ").replace(/\n/g, " ").replace(/\s+/g, " ").trim();
  const lower = text.toLowerCase();

  // Find section boundaries
  const transferStart = lower.indexOf("transfer credits");
  const academicStart = lower.indexOf("beginning of academic record");

  // Slice sections
  const transferSection =
    transferStart !== -1 && academicStart !== -1 && academicStart > transferStart
      ? text.slice(transferStart, academicStart)
      : transferStart !== -1
      ? text.slice(transferStart)
      : "";

  const academicSection =
    academicStart !== -1 ? text.slice(academicStart) : (transferStart !== -1 ? text.slice(0, transferStart) : text);

  // --- Code extractor: e.g., CS 170, MATH 221A, QTM 999XFR, CHEM 150L
  // Dept: 2–6 A-Z or '&'
  // Num: 3–4 digits
  // Suffix: 0–3 trailing A-Z (to cover 150L / 999XFR / 390A)
  const codeRe = /\b([A-Z&]{2,6})\s+(\d{3,4})([A-Z]{0,3})\b/g;

  function grabCodes(section: string): string[] {
    const seen = new Set<string>();
    const out: string[] = [];
    let m: RegExpExecArray | null;
    while ((m = codeRe.exec(section)) !== null) {
      const dept = m[1];
      const num = m[2];
      const suf = m[3] || "";
      const code = `${dept}${num}${suf}`;
      if (!seen.has(code)) {
        seen.add(code);
        out.push(code);
      }
    }
    return out;
  }

  const incoming_courses = grabCodes(transferSection);
  const emoryAll = grabCodes(academicSection);

  // Defensive filtering: remove any codes that were already counted as incoming_courses
  // (rare, but helps if the transcript echoes transfer lines later)
  const incomingSet = new Set(incoming_courses);
  const emory_courses = emoryAll.filter((c) => !incomingSet.has(c));

  return { incoming_courses, emory_courses };
}



  
  
  



