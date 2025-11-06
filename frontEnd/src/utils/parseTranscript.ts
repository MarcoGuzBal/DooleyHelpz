// frontEnd/utils/parseTranscript.ts
// Returns: course (e.g., "CS 171"), name (title), and optional inProgress.
// Failed (F*) and withdrawn (W*) courses are filtered out.

export type ParsedCourse = {
  course: string; // "DEPT NUM", e.g. "CS 171"
  name: string;
  inProgress?: boolean;
};

export type ParseResult = { courses: ParsedCourse[]; unparsed: string[] };

export function parseTranscript(rawText: string): ParseResult {
  const normalizeSpaces = (s: string) => (s || "").replace(/\s+/g, " ").trim();
  const stripCourseTopic = (s: string) => s.replace(/\s+Course\s+Topic:.*$/i, "").trim();

  // Detect grade internally so we can drop F/W
  const gradeRe = /(?:[A-F][+\-]?|P|S|U|I|W|T|NR|IP)/;
  const summaryLike =
    /(Attempted|Earned|GPA|Units|Points|Term\s+GPA|Totals|Transfer\s+Totals|Combined|Cum\s+GPA|Program:|Plan:|Major\b|Beginning of Academic Record|End of Advising Document)/i;
  const isTransferish = (s: string) => /Incoming\s+Course|Transferred\s+to\s+Term/i.test(s);

  const lines = (rawText || "")
    .replace(/\r/g, "\n")
    .split(/\n/)
    .map((l) => l.trim())
    .filter(Boolean);

  const flatOne = normalizeSpaces(lines.join(" "));

  const registrar: ParsedCourse[] = [];
  const tableOnly: ParsedCourse[] = [];
  const unparsed: string[] = [];

  // Split into course-like chunks: DEPT NUM ...
  const chunks = flatOne
    .split(/(?=(?:\b[A-Z&]{2,6}\s+\d{3,4}[A-Z]?)(?:\s|$))/g)
    .map((s) => s.trim())
    .filter(Boolean);

  // Rows that CONTAIN a grade: DEPT NUM Title ... att earn GRADE pts [Course Topic...]
  const withGrade = new RegExp(
    String.raw`^(?<dept>[A-Z&]{2,6})\s+(?<num>\d{3,4}[A-Z]?)\s+(?<title>.+?)\s+` +
      String.raw`(?<att>\d+(?:\.\d+)?)\s+(?<earn>\d+(?:\.\d+)?)\s+` +
      String.raw`(?<grade>${gradeRe.source})\s+(?<pts>\d+(?:\.\d+)?)` +
      String.raw`(?:\s+Course\s+Topic:.*)?$`
  );

  // Planned / in-progress rows (no grade), often end with points=0.000
  const plannedLine = new RegExp(
    String.raw`^(?<dept>[A-Z&]{2,6})\s+(?<num>\d{3,4}[A-Z]?)\s+(?<title>.+?)\s+` +
      String.raw`(?<att>\d+(?:\.\d+)?)\s+(?<earn>\d+(?:\.\d+)?)\s+0\.000$`
  );

  for (const rawChunk of chunks) {
    if (summaryLike.test(rawChunk)) continue;
    if (!/^[A-Z&]{2,6}\s+\d{3,4}[A-Z]?/.test(rawChunk)) continue;
    if (isTransferish(rawChunk)) continue;

    const c = stripCourseTopic(rawChunk);

    // Try grade row
    let m = c.match(withGrade);
    if (m?.groups) {
      const grade = (m.groups["grade"] || "").toUpperCase();
      // Drop failed or withdrawn
      if (grade.startsWith("F") || grade.startsWith("W")) continue;

      registrar.push({
        course: `${m.groups["dept"]} ${m.groups["num"]}`,
        name: normalizeSpaces(m.groups["title"] || ""),
      });
      continue;
    }

    // Try planned/in-progress
    m = c.match(plannedLine);
    if (m?.groups) {
      registrar.push({
        course: `${m.groups["dept"]} ${m.groups["num"]}`,
        name: normalizeSpaces(m.groups["title"] || ""),
        inProgress: true,
      });
      continue;
    }

    // Fallback: simple table-like "DEPT NUM Title [Grade]"
    const simple =
      c.match(
        new RegExp(
          String.raw`^(?<dept>[A-Z&]{2,6})\s+(?<num>\d{3,4}[A-Z]?)\s+(?<title>.+?)(?:\s+(?<grade>${gradeRe.source}))?$`
        )
      ) ?? null;

    if (simple?.groups) {
      const g = (simple.groups["grade"] || "").toUpperCase();
      if (g.startsWith("F") || g.startsWith("W")) continue;

      tableOnly.push({
        course: `${simple.groups["dept"]} ${simple.groups["num"]}`,
        name: normalizeSpaces(simple.groups["title"] || ""),
      });
    } else {
      unparsed.push(c);
    }
  }

  // Deduplicate by course + normalized title + inProgress
  const seen = new Set<string>();
  const merged: ParsedCourse[] = [];
  const keyOf = (c: ParsedCourse) =>
    `${c.course}|${c.name.toLowerCase()}|${c.inProgress ? "1" : "0"}`;

  for (const c of [...registrar, ...tableOnly]) {
    const k = keyOf(c);
    if (!seen.has(k)) {
      seen.add(k);
      merged.push(c);
    }
  }

  return { courses: merged, unparsed };
}
