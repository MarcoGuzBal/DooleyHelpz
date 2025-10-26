// src/utils/parseCoursesOnly.ts
/**
 * Extracts all course codes (including transfer/AP ones) from transcript text.
 * Each course is stored as a single string like "CS170" or "ECON120".
 */
export function parseTranscript(rawText: string): string[] {
  if (!rawText) return [];

  // Flatten all lines into one clean string
  const text = rawText.replace(/\r/g, " ").replace(/\n/g, " ");

  // Regex: match DEPT + NUMBER (e.g., CS 170, ECON 112, MATH 221)
  const pattern = /\b([A-Z&]{2,6})\s+(\d{3,4}[A-Z]?)\b/g;

  const courses: string[] = []; // Stores Courses
  const seen = new Set<string>(); // Set

  let match: RegExpExecArray | null;
  while ((match = pattern.exec(text)) !== null) {
    const dept = match[1];
    const num = match[2];
    const code = `${dept}${num}`;

    // You can remove this duplicate check if you want repeats too
    if (!seen.has(code)) {
      seen.add(code);
      courses.push(code);
    }
  }

  return courses;
}

  
  
  



