// src/utils/parseTranscript.ts
export type ParsedCourse = {
    dept: string | null;
    number: string;
    name: string;
    grade: string;       // "A", "A-", "S", "IN", etc.
    inProgress?: boolean;
  };
  
  export type ParseResult = { courses: ParsedCourse[]; unparsed: string[] };
  
  export function parseTranscript(rawText: string): ParseResult {
    const normalizeSpaces = (s: string) => (s || "").replace(/\s+/g, " ").trim();
    const stripCourseTopic = (s: string) => s.replace(/\s+Course\s+Topic:.*$/i, "").trim();
  
    const gradeRe = /(?:[A-F][+\-]?|P|S|U|I|W|T|NR|IP)/;
    const summaryLike =
      /(Attempted|Earned|GPA|Units|Points|Term\s+GPA|Totals|Transfer\s+Totals|Combined|Cum\s+GPA|Program:|Plan:|Major\b|Beginning of Academic Record|End of Advising Document)/i;
    const isTransferish = (s: string) => /Incoming\s+Course|Transferred\s+to\s+Term/i.test(s);
  
    const lines = (rawText || "").replace(/\r/g, "\n").split(/\n/).map(l => l.trim()).filter(Boolean);
    const flatOne = normalizeSpaces(lines.join(" "));
  
    const registrar: ParsedCourse[] = [];
    const tableOnly: ParsedCourse[] = [];
    const unparsed: string[] = [];
  
    // ---------- A) Registrar chunks (authoritative) ----------
    // ✅ FIX A: require a word boundary before dept so we don't split inside BUS/ECON/etc.
    const chunks = flatOne
      .split(/(?=(?:\b[A-Z&]{2,6}\s+\d{3,4}[A-Z]?)(?:\s|$))/g)
      .map(s => s.trim())
      .filter(Boolean);
  
    // with grade: DEPT NUM Title ... attempted earned GRADE points [Course Topic: ...]
    const withGrade = new RegExp(
      String.raw`^(?<dept>[A-Z&]{2,6})\s+(?<num>\d{3,4}[A-Z]?)\s+(?<title>.+?)\s+` +
      String.raw`(?<att>\d+(?:\.\d+)?)\s+(?<earn>\d+(?:\.\d+)?)\s+` +
      String.raw`(?<grade>${gradeRe.source})\s+(?<pts>\d+(?:\.\d+)?)` +
      String.raw`(?:\s+Course\s+Topic:.*)?$`
    );
  
    // ✅ FIX B: planned rows (no grade), end with points=0.000 (attempted can be 0.500/3.000/etc.)
    const plannedLine = new RegExp(
      String.raw`^(?<dept>[A-Z&]{2,6})\s+(?<num>\d{3,4}[A-Z]?)\s+(?<title>.+?)\s+` +
      String.raw`(?<att>\d+(?:\.\d+)?)\s+(?<earn>\d+(?:\.\d+)?)\s+0\.000$`
    );
  
    for (const rawChunk of chunks) {
      if (summaryLike.test(rawChunk)) continue;
      if (!/^[A-Z&]{2,6}\s+\d{3,4}[A-Z]?/.test(rawChunk)) continue;
      if (isTransferish(rawChunk)) continue; // ignore transfer/AP
  
      const c = stripCourseTopic(rawChunk);
  
      let m = c.match(withGrade);
      if (m?.groups) {
        registrar.push({
          dept: m.groups["dept"]!,
          number: m.groups["num"]!,
          name: normalizeSpaces(m.groups["title"] || ""),
          grade: m.groups["grade"]!,
        });
        continue;
      }
  
      // ✅ Always try planned match if no grade match
      m = c.match(plannedLine);
      if (m?.groups) {
        registrar.push({
          dept: m.groups["dept"]!,
          number: m.groups["num"]!,
          name: normalizeSpaces(m.groups["title"] || ""),
          grade: "IN",
          inProgress: true,
        });
        continue;
      }
  
      unparsed.push(c);
    }
  
    // ---------- B) Simple table (fallback) ----------
    let inSimple = false;
    for (const line of lines) {
      if (/^number\s+course\s+grade$/i.test(line)) { inSimple = true; continue; }
      if (inSimple) {
        if (!line || /^[A-Z]{2,}\b/.test(line)) { inSimple = false; continue; }
        const m =
          line.match(new RegExp(String.raw`^(?<num>\d{3,4}[A-Z]?)\s+(?<title>.+?)\s+(?<grade>${gradeRe.source}|IN)$`))
          || (() => {
               const parts = line.split(/\s+/);
               if (parts.length >= 3) {
                 const g = parts[parts.length - 1];
                 if (new RegExp(`^(?:${gradeRe.source}|IN)$`).test(g)) {
                   const num = parts[0];
                   const title = parts.slice(1, -1).join(" ");
                   if (/^\d{3,4}[A-Z]?$/.test(num)) return { groups: { num, title, grade: g } } as any;
                 }
               }
               return null;
             })();
  
        if (m?.groups) {
          tableOnly.push({
            dept: null,
            number: m.groups["num"]!,
            name: (m.groups["title"] || "").trim(),
            grade: m.groups["grade"]!,
          });
        } else {
          unparsed.push(line);
        }
      }
    }
  
    // ---------- C) Prefer registrar rows; add table rows only if new ----------
    const normTitle = (s: string) => normalizeSpaces(s).toLowerCase();
    const keyOf = (c: ParsedCourse) => `${c.dept ?? ""}|${c.number}|${normTitle(c.name)}|${c.grade}|${c.inProgress ? "1" : "0"}`;
  
    const seen = new Set<string>();
    const merged: ParsedCourse[] = [];
    for (const c of registrar) { const k = keyOf(c); if (!seen.has(k)) { seen.add(k); merged.push(c); } }
    for (const c of tableOnly) { const k = keyOf(c); if (!seen.has(k)) { seen.add(k); merged.push(c); } }
  
    return { courses: merged, unparsed };
  }
  
  
  
  



