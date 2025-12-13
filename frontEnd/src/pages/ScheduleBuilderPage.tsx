import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  CalendarDays, Download, RefreshCw, CheckCircle2, AlertCircle,
  ChevronLeft, ChevronRight, Star, Clock, BookOpen, GraduationCap,
  Plus, X, Search, List, ChevronDown, ChevronUp, Trash2, AlertTriangle,
  Info, Cpu, Sparkles,
} from "lucide-react";
import { auth } from "../firebase";
import { API_URL, api, enginePreference, type EngineType } from "../utils/api";
import applogo from "../assets/dooleyHelpzAppLogo.png";

type Course = {
  code: string;
  title: string;
  professor: string;
  credits: number | string;
  time: string;
  meeting?: { day: string; time: string; location: string }[];
  rmp?: { rating: number; num_ratings: number } | null;
  score?: number;
  ger: string | string[] | null;
  normalized_code: string;
  outside_preferred_time?: boolean;
  user_added?: boolean;
  hard_time_conflict?: boolean;
};

type Schedule = {
  root_course_code: string;
  total_score: number;
  courses: Course[];
  course_count: number;
  total_credits: number;
};

type CalendarBlock = {
  day: "Mon" | "Tue" | "Wed" | "Thu" | "Fri";
  course: string;
  title: string;
  professor: string;
  location: string;
  start: string;
  end: string;
  color: string;
  outside_preferred_time?: boolean;
  user_added?: boolean;
  hard_time_conflict?: boolean;
};

type TimeUnavailableBlock = {
  day: string;
  start: string;
  end: string;
};

const DAYS: CalendarBlock["day"][] = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const START_HOUR = 8;
const END_HOUR = 23;
const TOTAL_MINUTES = (END_HOUR - START_HOUR) * 60;

const COURSE_COLORS = [
  "bg-blue-100 border-blue-300 text-blue-800",
  "bg-emerald-100 border-emerald-300 text-emerald-800",
  "bg-amber-100 border-amber-300 text-amber-800",
  "bg-purple-100 border-purple-300 text-purple-800",
  "bg-rose-100 border-rose-300 text-rose-800",
  "bg-cyan-100 border-cyan-300 text-cyan-800",
  "bg-orange-100 border-orange-300 text-orange-800",
];

const MAJOR_MUST = new Set<string>([
  "MATH111", "MATH112", "MATH221",
  "CS170", "CS171", "CS224", "CS253",
  "CS255", "CS326", "CS350",
]);

const formatGer = (ger: string) => (ger === "MQR" ? "MAJOR" : ger);

function getCourseTags(course: Course): string[] {
  const rawGers = course.ger ? (Array.isArray(course.ger) ? course.ger : [course.ger]) : [];
  const tags = new Set<string>();
  rawGers.forEach((g) => tags.add(formatGer(g)));

  const normalizedCode = (course.normalized_code || course.code || "").toUpperCase().replace(/\s+/g, "");
  if (MAJOR_MUST.has(normalizedCode)) {
    tags.add("MAJOR");
  }

  return Array.from(tags);
}

const USER_ADDED_COLOR = "bg-gray-100/60 border-gray-400 border-dashed text-gray-700";
const HARD_CONFLICT_COLOR = "bg-red-100 border-red-400 text-red-800";

function parseTimeString(timeStr: string): { start: string; end: string } | null {
  if (!timeStr) return null;
  const normalized = timeStr.replace(/(?<![:\d])(\d{1,2})(am|pm)/gi, "$1:00$2");
  const match = normalized.match(/(\d{1,2}):(\d{2})\s*(am|pm)\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)/i);
  if (!match) return null;
  let startHour = parseInt(match[1]);
  const startMin = match[2];
  const startAmPm = match[3].toLowerCase();
  let endHour = parseInt(match[4]);
  const endMin = match[5];
  const endAmPm = match[6].toLowerCase();
  if (startAmPm === "pm" && startHour !== 12) startHour += 12;
  if (startAmPm === "am" && startHour === 12) startHour = 0;
  if (endAmPm === "pm" && endHour !== 12) endHour += 12;
  if (endAmPm === "am" && endHour === 12) endHour = 0;
  return { start: `${startHour.toString().padStart(2, "0")}:${startMin}`, end: `${endHour.toString().padStart(2, "0")}:${endMin}` };
}

// Improved day parsing to handle all formats correctly
function parseDays(dayStr: string): CalendarBlock["day"][] {
  if (!dayStr) return [];
  const days: CalendarBlock["day"][] = [];
  const cleaned = dayStr.replace(/\s/g, "");
  let i = 0;
  
  while (i < cleaned.length) {
    const remaining = cleaned.slice(i).toUpperCase();
    
    // Check for two-character codes first
    if (remaining.startsWith("TH")) {
      days.push("Thu");
      i += 2;
    } else if (remaining.startsWith("TU")) {
      days.push("Tue");
      i += 2;
    } else {
      // Single character codes
      const char = remaining[0];
      if (char === "M") days.push("Mon");
      else if (char === "T") days.push("Tue"); // Single T = Tuesday
      else if (char === "W") days.push("Wed");
      else if (char === "R") days.push("Thu"); // R = Thursday (alternative notation)
      else if (char === "F") days.push("Fri");
      i++;
    }
  }
  
  return [...new Set(days)]; // Remove duplicates
}

// Map short day names to full day names used in preferences
const DAY_MAP: Record<string, string> = {
  "Mon": "Monday",
  "Tue": "Tuesday", 
  "Wed": "Wednesday",
  "Thu": "Thursday",
  "Fri": "Friday",
  "Monday": "Monday",
  "Tuesday": "Tuesday",
  "Wednesday": "Wednesday",
  "Thursday": "Thursday",
  "Friday": "Friday",
};

// Reverse map for converting full names to short
const DAY_MAP_REVERSE: Record<string, string> = {
  "Monday": "Mon",
  "Tuesday": "Tue",
  "Wednesday": "Wed",
  "Thursday": "Thu",
  "Friday": "Fri",
};

function minutesFromStart(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return (h - START_HOUR) * 60 + m;
}

function timeToMinutes(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}

// Parse course time into blocks for overlap checking
function getCourseTimeBlocks(course: Course): Array<{ day: string; start: number; end: number }> {
  const blocks: Array<{ day: string; start: number; end: number }> = [];
  
  if (course.meeting && Array.isArray(course.meeting) && course.meeting.length > 0) {
    course.meeting.forEach((m) => {
      if (!m.day || !m.time) return;
      const days = parseDays(m.day);
      const times = parseTimeString(m.time);
      if (days.length && times) {
        const startMin = timeToMinutes(times.start);
        const endMin = timeToMinutes(times.end);
        days.forEach((day) => {
          blocks.push({ day, start: startMin, end: endMin });
        });
      }
    });
  } else if (course.time && course.time !== "TBA") {
    const firstSpaceIdx = course.time.indexOf(" ");
    if (firstSpaceIdx !== -1) {
      const dayPart = course.time.slice(0, firstSpaceIdx);
      const timePart = course.time.slice(firstSpaceIdx + 1);
      const days = parseDays(dayPart);
      const times = parseTimeString(timePart);
      if (days.length && times) {
        const startMin = timeToMinutes(times.start);
        const endMin = timeToMinutes(times.end);
        days.forEach((day) => {
          blocks.push({ day, start: startMin, end: endMin });
        });
      }
    }
  }
  
  return blocks;
}

// Check if two courses have overlapping times
function coursesOverlap(course1: Course, course2: Course): boolean {
  const blocks1 = getCourseTimeBlocks(course1);
  const blocks2 = getCourseTimeBlocks(course2);
  
  for (const b1 of blocks1) {
    for (const b2 of blocks2) {
      if (b1.day === b2.day) {
        if (b1.start < b2.end && b2.start < b1.end) {
          return true;
        }
      }
    }
  }
  
  return false;
}

function findOverlappingCourses(newCourse: Course, existingCourses: Course[]): Course[] {
  return existingCourses.filter(existing => coursesOverlap(newCourse, existing));
}

// Check if a course conflicts with time unavailable blocks
function checkHardTimeConflict(course: Course, timeUnavailable: TimeUnavailableBlock[]): boolean {
  if (!timeUnavailable || timeUnavailable.length === 0) return false;
  
  const courseBlocks = getCourseTimeBlocks(course);
  if (courseBlocks.length === 0) return false; // TBA courses don't conflict
  
  for (const courseBlock of courseBlocks) {
    const courseDayFull = DAY_MAP[courseBlock.day] || courseBlock.day;
    const courseDayShort = DAY_MAP_REVERSE[courseBlock.day] || courseBlock.day;
    
    for (const unavail of timeUnavailable) {
      const unavailDayFull = DAY_MAP[unavail.day] || unavail.day;
      const unavailDayShort = DAY_MAP_REVERSE[unavail.day] || unavail.day;
      
      // Check if same day (compare both full and short names)
      const sameDay = 
        courseDayFull === unavailDayFull ||
        courseDayFull === unavail.day ||
        courseBlock.day === unavailDayFull ||
        courseBlock.day === unavail.day ||
        courseDayShort === unavailDayShort;
      
      if (sameDay) {
        const unavailStart = timeToMinutes(unavail.start);
        const unavailEnd = timeToMinutes(unavail.end);
        
        // Overlap check: start1 < end2 AND start2 < end1
        if (courseBlock.start < unavailEnd && unavailStart < courseBlock.end) {
          console.log(`CONFLICT DETECTED: ${course.code} on ${courseBlock.day} (${courseBlock.start}-${courseBlock.end}) conflicts with unavailable ${unavail.day} (${unavailStart}-${unavailEnd})`);
          return true;
        }
      }
    }
  }
  
  return false;
}

function coursesToCalendarBlocks(courses: Course[]): CalendarBlock[] {
  const blocks: CalendarBlock[] = [];
  courses.forEach((course, idx) => {
    let color = course.user_added ? USER_ADDED_COLOR : COURSE_COLORS[idx % COURSE_COLORS.length];
    if (course.hard_time_conflict) {
      color = HARD_CONFLICT_COLOR;
    }
    if (course.meeting && Array.isArray(course.meeting) && course.meeting.length > 0) {
      course.meeting.forEach((m) => {
        if (!m.day || !m.time) return;
        const days = parseDays(m.day);
        const times = parseTimeString(m.time);
        if (days.length && times) {
          days.forEach((day) => {
            blocks.push({ 
              day, 
              course: course.code, 
              title: course.title, 
              professor: course.professor || "", 
              location: m.location || "", 
              start: times.start, 
              end: times.end, 
              color,
              outside_preferred_time: course.outside_preferred_time,
              user_added: course.user_added,
              hard_time_conflict: course.hard_time_conflict
            });
          });
        }
      });
    } else if (course.time && course.time !== "TBA") {
      const firstSpaceIdx = course.time.indexOf(" ");
      if (firstSpaceIdx === -1) return;
      const dayPart = course.time.slice(0, firstSpaceIdx);
      const timePart = course.time.slice(firstSpaceIdx + 1);
      const days = parseDays(dayPart);
      const times = parseTimeString(timePart);
      if (days.length && times) {
        days.forEach((day) => {
          blocks.push({ 
            day, 
            course: course.code, 
            title: course.title, 
            professor: course.professor || "", 
            location: "", 
            start: times.start, 
            end: times.end, 
            color,
            outside_preferred_time: course.outside_preferred_time,
            user_added: course.user_added,
            hard_time_conflict: course.hard_time_conflict
          });
        });
      }
    }
  });
  return blocks;
}

function formatTime12(time24: string): string {
  const [h, m] = time24.split(":").map(Number);
  const ampm = h >= 12 ? "pm" : "am";
  const h12 = h % 12 || 12;
  return `${h12}:${m.toString().padStart(2, "0")}${ampm}`;
}

function generateICS(courses: Course[], scheduleName: string): string {
  const lines: string[] = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DooleyHelpz//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH", `X-WR-CALNAME:${scheduleName}`];
  
  const semesterStart = new Date(2026, 0, 12);
  const semesterEnd = new Date(2026, 3, 24);
  
  const dayOffsets: Record<string, number> = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4 };
  
  const blocks = coursesToCalendarBlocks(courses);
  blocks.forEach((block, idx) => {
    const dayOffset = dayOffsets[block.day];
    if (dayOffset === undefined) return;
    
    const firstOccurrence = new Date(semesterStart);
    firstOccurrence.setDate(firstOccurrence.getDate() + dayOffset);
    
    const [startH, startM] = block.start.split(":").map(Number);
    const [endH, endM] = block.end.split(":").map(Number);
    
    const dtstart = new Date(firstOccurrence); 
    dtstart.setHours(startH, startM, 0, 0);
    
    const dtend = new Date(firstOccurrence); 
    dtend.setHours(endH, endM, 0, 0);
    
    const formatDateLocal = (d: Date) => `${d.getFullYear()}${(d.getMonth() + 1).toString().padStart(2, "0")}${d.getDate().toString().padStart(2, "0")}T${d.getHours().toString().padStart(2, "0")}${d.getMinutes().toString().padStart(2, "0")}00`;
    const formatDate = (d: Date) => d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
    
    const rruleDays: Record<string, string> = { Mon: "MO", Tue: "TU", Wed: "WE", Thu: "TH", Fri: "FR" };
    const rruleDay = rruleDays[block.day];
    
    lines.push(
      "BEGIN:VEVENT",
      `UID:${Date.now()}-${idx}-${Math.random().toString(36).substr(2, 9)}@dooleyhelpz`,
      `DTSTAMP:${formatDate(new Date())}`,
      `DTSTART;TZID=America/New_York:${formatDateLocal(dtstart)}`,
      `DTEND;TZID=America/New_York:${formatDateLocal(dtend)}`,
      `RRULE:FREQ=WEEKLY;BYDAY=${rruleDay};WKST=MO;UNTIL=${formatDate(semesterEnd)}`,
      `SUMMARY:${block.course} - ${block.title}`,
      `DESCRIPTION:Professor: ${block.professor || "TBA"}`,
      block.location ? `LOCATION:${block.location}` : "",
      "END:VEVENT"
    );
  });
  lines.push("END:VCALENDAR");
  return lines.filter(l => l).join("\r\n");
}

function downloadICS(courses: Course[], scheduleName: string) {
  const ics = generateICS(courses, scheduleName);
  const blob = new Blob([ics], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); 
  a.href = url; 
  a.download = `${scheduleName.replace(/\s+/g, "_")}.ics`;
  document.body.appendChild(a); 
  a.click(); 
  document.body.removeChild(a); 
  URL.revokeObjectURL(url);
}

function WeeklyCalendar({ blocks, timeUnavailable }: { blocks: CalendarBlock[]; timeUnavailable: TimeUnavailableBlock[] }) {
  const byDay: Record<CalendarBlock["day"], CalendarBlock[]> = { Mon: [], Tue: [], Wed: [], Thu: [], Fri: [] };
  blocks.forEach((b) => byDay[b.day].push(b));
  
  // Get unavailable blocks per day for display
  const unavailByDay: Record<CalendarBlock["day"], TimeUnavailableBlock[]> = { Mon: [], Tue: [], Wed: [], Thu: [], Fri: [] };
  timeUnavailable.forEach((u) => {
    const shortDay = DAY_MAP_REVERSE[u.day] || u.day;
    if (shortDay in unavailByDay) {
      unavailByDay[shortDay as CalendarBlock["day"]].push(u);
    }
  });
  
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="grid grid-cols-[3.5rem_repeat(5,1fr)] gap-1 text-xs">
        <div className="relative h-[520px]">
          {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, idx) => {
            const hour = START_HOUR + idx;
            const top = (idx / (END_HOUR - START_HOUR)) * 100;
            return <div key={hour} className="absolute left-0 -translate-y-1/2 text-[10px] text-zinc-400 font-medium" style={{ top: `${top}%` }}>{hour > 12 ? hour - 12 : hour}:00 {hour >= 12 ? "PM" : "AM"}</div>;
          })}
        </div>
        {DAYS.map((day) => (
          <div key={day} className="relative h-[520px] border-l border-zinc-100">
            <div className="sticky top-0 z-10 mb-1 bg-white pb-1 text-center text-xs font-semibold text-emoryBlue">{day}</div>
            {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, idx) => <div key={idx} className="absolute left-0 right-0 border-t border-dashed border-zinc-100" style={{ top: `${(idx / (END_HOUR - START_HOUR)) * 100}%` }} />)}
            
            {/* Render unavailable time blocks */}
            {unavailByDay[day].map((u, i) => {
              const startMin = timeToMinutes(u.start) - START_HOUR * 60;
              const endMin = timeToMinutes(u.end) - START_HOUR * 60;
              if (startMin < 0 || endMin < 0) return null;
              const top = (startMin / TOTAL_MINUTES) * 100;
              const height = ((endMin - startMin) / TOTAL_MINUTES) * 100;
              return (
                <div
                  key={`unavail-${day}-${i}`}
                  className="absolute left-0 right-0 bg-red-50/50 border-l-2 border-red-300"
                  style={{ top: `${Math.max(0, top)}%`, height: `${Math.min(height, 100 - top)}%` }}
                  title="Time unavailable"
                />
              );
            })}
            
            {byDay[day].map((block, i) => {
              const startMin = minutesFromStart(block.start);
              const endMin = minutesFromStart(block.end);
              const rawTop = (startMin / TOTAL_MINUTES) * 100;
              const rawHeight = ((endMin - startMin) / TOTAL_MINUTES) * 100;
              const top = Math.max(rawTop, 2);
              const height = Math.max(Math.min(rawHeight, 100 - top), 6);
              
              const hasTimeWarning = block.outside_preferred_time;
              const isUserAdded = block.user_added;
              const hasHardConflict = block.hard_time_conflict;
              
              return (
                <div 
                  key={`${block.course}-${i}`} 
                  className={`absolute left-0.5 right-0.5 overflow-hidden rounded-lg border px-1.5 py-1 shadow-sm cursor-pointer hover:shadow-md transition-shadow ${block.color} ${isUserAdded ? 'opacity-70' : ''} z-10`} 
                  style={{ top: `${top}%`, height: `${height}%`, minHeight: "2.5rem" }} 
                  title={`${block.course}: ${block.title}\n${block.professor || "TBA"}\n${formatTime12(block.start)}-${formatTime12(block.end)}${hasTimeWarning ? '\nOutside preferred time' : ''}${isUserAdded ? '\nUser added' : ''}${hasHardConflict ? '\n⚠️ CONFLICTS WITH YOUR UNAVAILABLE TIME' : ''}`}
                >
                  <div className="flex items-center gap-1">
                    <span className="font-semibold text-[11px] leading-tight truncate">{block.course}</span>
                    {hasHardConflict && <X className="h-3 w-3 text-red-600 flex-shrink-0" />}
                    {hasTimeWarning && !hasHardConflict && <AlertTriangle className="h-3 w-3 text-amber-600 flex-shrink-0" />}
                    {isUserAdded && <span className="text-[9px]">UA</span>}
                  </div>
                  <div className="text-[9px] opacity-70">{formatTime12(block.start)}-{formatTime12(block.end)}</div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function ScheduleOptionsDrawer({ schedules, selectedIdx, onSelect, isOpen, onToggle }: { schedules: Schedule[]; selectedIdx: number; onSelect: (idx: number) => void; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-zinc-200 shadow-lg">
      <button onClick={onToggle} className="w-full flex items-center justify-center gap-2 py-2 bg-zinc-50 hover:bg-zinc-100 transition-colors">
        <List className="h-4 w-4 text-zinc-600" />
        <span className="text-sm font-medium text-zinc-700">{isOpen ? "Hide" : "Show"} All {schedules.length} Schedule Options</span>
        {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
      </button>
      {isOpen && (
        <div className="max-h-64 overflow-y-auto p-4">
          <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-10 gap-3">
            {schedules.map((schedule, idx) => (
              <button key={idx} onClick={() => onSelect(idx)} className={`p-3 rounded-lg border-2 text-center transition-all ${idx === selectedIdx ? "border-emoryBlue bg-emoryBlue/5" : "border-zinc-200 hover:border-zinc-300 bg-white"}`}>
                <div className="text-lg font-bold text-emoryBlue">#{idx + 1}</div>
                <div className="text-xs text-zinc-500">{schedule.total_credits} cr</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CourseDetailRow({ course, onRemove, canRemove = true }: { course: Course; onRemove?: () => void; canRemove?: boolean }) {
  const gers = getCourseTags(course);
  const isUserAdded = course.user_added;
  const isOutsideTime = course.outside_preferred_time;
  const hasHardConflict = course.hard_time_conflict;
  
  return (
    <div className={`flex items-center justify-between rounded-lg border px-3 py-2 group ${hasHardConflict ? 'border-red-400 bg-red-50' : isUserAdded ? 'border-dashed border-gray-400 bg-gray-50/60' : 'border-zinc-100 bg-zinc-50'}`}>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-emoryBlue">{course.code}</span>
          {hasHardConflict && <span className="rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700 flex items-center gap-0.5"><X className="h-3 w-3" /> Time conflict!</span>}
          {isUserAdded && <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">User added</span>}
          {isOutsideTime && !hasHardConflict && <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 flex items-center gap-0.5"><AlertTriangle className="h-3 w-3" /> Outside preferences</span>}
          {gers.map((g) => <span key={g} className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">{g}</span>)}
        </div>
        <p className="text-sm text-zinc-600 truncate max-w-md">{course.title}</p>
        <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
          <span className="flex items-center gap-1"><GraduationCap className="h-3 w-3" />{course.professor || "TBA"}</span>
          <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{course.time || "TBA"}</span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right">
          <div className="text-sm font-medium text-zinc-700">{course.credits} cr</div>
          {course.rmp && course.rmp.rating > 0 && <div className="flex items-center gap-1 text-xs text-amber-600"><Star className="h-3 w-3 fill-amber-500" />{course.rmp.rating.toFixed(1)}</div>}
        </div>
        {canRemove && onRemove && <button onClick={onRemove} className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-rose-100 text-rose-600 transition-all" title="Remove course"><Trash2 className="h-4 w-4" /></button>}
      </div>
    </div>
  );
}

function AddCourseModal({ 
  isOpen, 
  onClose, 
  onAddCourse, 
  currentCourses,
  timeUnavailable
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  onAddCourse: (course: Course) => void; 
  currentCourses: Course[];
  timeUnavailable: TimeUnavailableBlock[];
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [overlapWarning, setOverlapWarning] = useState<{ course: any; overlaps: Course[]; isHardConflict: boolean } | null>(null);

  // Helper to check if a course section is already in the schedule
  // Returns true if EXACT SAME section (same code + same time + same professor)
  function isSameSection(searchCourse: any, existingCourse: Course): boolean {
    const searchCode = (searchCourse.code || "").toUpperCase().replace(/\s+/g, "");
    const existingCode = (existingCourse.code || "").toUpperCase().replace(/\s+/g, "");
    
    if (searchCode !== existingCode) return false;
    
    // Same code - check if same section (time + professor)
    const searchTime = (searchCourse.time || "").trim().toLowerCase();
    const existingTime = (existingCourse.time || "").trim().toLowerCase();
    const searchProf = (searchCourse.professor || "").trim().toLowerCase();
    const existingProf = (existingCourse.professor || "").trim().toLowerCase();
    
    // If both time and professor match, it's the same section
    return searchTime === existingTime && searchProf === existingProf;
  }

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    setSearching(true);
    setOverlapWarning(null);
    try {
      const res = await fetch(`${API_URL}/api/search-courses?q=${encodeURIComponent(searchQuery)}&limit=20`);
      const data = await res.json();
      if (data.success && data.courses) {
        // Filter out only EXACT SAME sections (same code + same time + same professor)
        // This allows adding different sections of the same course
        setSearchResults(data.courses.filter((searchCourse: any) => {
          // Check if this exact section is already in the schedule
          return !currentCourses.some(existing => isSameSection(searchCourse, existing));
        }));
      }
    } catch (err) { console.error("Search failed:", err); }
    finally { setSearching(false); }
  }

  function checkOverlapAndSelect(course: any) {
    const newCourse: Course = {
      code: course.code || "",
      title: course.title || "",
      professor: course.professor || "TBA",
      credits: course.credits || 3,
      time: course.time || "TBA",
      meeting: course.meeting || [],
      rmp: course.rmp || null,
      score: 50,
      ger: course.ger || null,
      normalized_code: (course.code || "").toUpperCase().replace(/\s+/g, ""),
    };
    
    const hasHardConflict = checkHardTimeConflict(newCourse, timeUnavailable);
    const overlappingCourses = findOverlappingCourses(newCourse, currentCourses);
    
    if (hasHardConflict || overlappingCourses.length > 0) {
      setOverlapWarning({ course, overlaps: overlappingCourses, isHardConflict: hasHardConflict });
    } else {
      handleConfirmAdd(course, false);
    }
  }

  function handleConfirmAdd(course: any, hasHardConflict: boolean) {
    const newCourse: Course = {
      code: course.code || "",
      title: course.title || "",
      professor: course.professor || "TBA",
      credits: course.credits || 3,
      time: course.time || "TBA",
      meeting: course.meeting || [],
      rmp: course.rmp || null,
      score: 50,
      ger: course.ger || null,
      normalized_code: (course.code || "").toUpperCase().replace(/\s+/g, ""),
      user_added: true,
      hard_time_conflict: hasHardConflict,
    };
    onAddCourse(newCourse);
    onClose();
    setSearchQuery("");
    setSearchResults([]);
    setOverlapWarning(null);
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] overflow-hidden">
        <div className="p-4 border-b border-zinc-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-emoryBlue">Add Course</h2>
          <button onClick={() => { onClose(); setOverlapWarning(null); }} className="p-1 hover:bg-zinc-100 rounded-lg"><X className="h-5 w-5" /></button>
        </div>
        
        {overlapWarning ? (
          <div className="p-4">
            <div className={`flex items-center gap-2 mb-3 ${overlapWarning.isHardConflict ? 'text-red-700' : 'text-amber-700'}`}>
              {overlapWarning.isHardConflict ? <X className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
              <span className="font-semibold">{overlapWarning.isHardConflict ? 'Conflicts With Your Unavailable Time!' : 'Time Conflict Detected'}</span>
            </div>
            
            {overlapWarning.isHardConflict && (
              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">
                  <strong>{overlapWarning.course.code}</strong> ({overlapWarning.course.time}) conflicts with your "Time Unavailable" settings. This course will be marked as having a hard conflict.
                </p>
              </div>
            )}
            
            {overlapWarning.overlaps.length > 0 && (
              <>
                <p className="text-sm text-zinc-600 mb-3">
                  <strong>{overlapWarning.course.code}</strong> overlaps with:
                </p>
                <ul className="space-y-1 mb-4">
                  {overlapWarning.overlaps.map((c, i) => (
                    <li key={i} className="text-sm text-zinc-700 bg-amber-50 rounded px-2 py-1">
                      • {c.code} ({c.time})
                    </li>
                  ))}
                </ul>
              </>
            )}
            
            <p className="text-sm text-zinc-500 mb-4">
              {overlapWarning.isHardConflict 
                ? "Adding this course will create a conflict with your blocked time. Are you sure?"
                : "Adding this course will create a scheduling conflict. Are you sure you want to add it anyway?"}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setOverlapWarning(null)}
                className="flex-1 px-4 py-2 border border-zinc-300 rounded-lg text-sm font-medium text-zinc-700 hover:bg-zinc-50"
              >
                Cancel
              </button>
              <button
                onClick={() => handleConfirmAdd(overlapWarning.course, overlapWarning.isHardConflict)}
                className={`flex-1 px-4 py-2 text-white rounded-lg text-sm font-medium ${overlapWarning.isHardConflict ? 'bg-red-500 hover:bg-red-600' : 'bg-amber-500 hover:bg-amber-600'}`}
              >
                Add Anyway
              </button>
            </div>
          </div>
        ) : (
          <div className="p-4">
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Search by course code (e.g., CS350) or title..."
                className="flex-1 rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emoryBlue"
              />
              <button onClick={handleSearch} disabled={searching} className="px-4 py-2 bg-emoryBlue text-white rounded-lg text-sm font-medium hover:bg-emoryBlue/90 disabled:opacity-50">
                <Search className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-80 overflow-y-auto space-y-2">
              {searching && <p className="text-sm text-zinc-500 text-center py-4">Searching...</p>}
              {!searching && searchResults.length === 0 && searchQuery && <p className="text-sm text-zinc-500 text-center py-4">No courses found. Try a department code like "CS" or "MATH".</p>}
              {searchResults.map((course, idx) => {
                const tempCourse: Course = {
                  code: course.code || "",
                  title: course.title || "",
                  professor: course.professor || "TBA",
                  credits: course.credits || 3,
                  time: course.time || "TBA",
                  meeting: course.meeting || [],
                  rmp: null,
                  score: 0,
                  ger: null,
                  normalized_code: (course.code || "").toUpperCase().replace(/\s+/g, ""),
                };
                const hasConflict = checkHardTimeConflict(tempCourse, timeUnavailable);
                
                // Check if same course code is already in schedule (different section)
                const sameCodeInSchedule = currentCourses.some(existing => 
                  (existing.code || "").toUpperCase().replace(/\s+/g, "") === 
                  (course.code || "").toUpperCase().replace(/\s+/g, "")
                );
                
                return (
                  <button
                    key={idx}
                    onClick={() => checkOverlapAndSelect(course)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${hasConflict ? 'border-red-300 hover:border-red-400 bg-red-50' : sameCodeInSchedule ? 'border-amber-300 hover:border-amber-400 bg-amber-50' : 'border-zinc-200 hover:border-emoryBlue hover:bg-emoryBlue/5'}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-emoryBlue">{course.code}</span>
                        {hasConflict && <span className="text-[10px] text-red-600 font-medium">⚠️ Time conflict</span>}
                        {sameCodeInSchedule && !hasConflict && <span className="text-[10px] text-amber-600 font-medium">Different section</span>}
                      </div>
                      <div className="text-xs text-zinc-500">{course.credits || 3} cr</div>
                    </div>
                    <div className="text-sm text-zinc-600 truncate">{course.title}</div>
                    <div className="text-xs text-zinc-400 mt-1">{course.time || "TBA"} • {course.professor || "TBA"}</div>
                  </button>
                );
              })}
            </div>
            <p className="mt-4 text-xs text-zinc-500 text-center">
              Search by department (e.g., "CS", "MATH") or full course code (e.g., "CS350"). You can add different sections of the same course.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// NEW: Regenerate reminder popup
function RegenerateReminderPopup({ isOpen, onClose, onRegenerate, addedCount, removedCount }: { 
  isOpen: boolean; 
  onClose: () => void;
  onRegenerate: () => void;
  addedCount: number;
  removedCount: number;
}) {
  if (!isOpen) return null;
  
  return (
    <div className="fixed bottom-24 right-4 z-40 bg-white rounded-xl shadow-lg border border-amber-200 p-4 max-w-sm animate-in slide-in-from-bottom-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 p-2 bg-amber-100 rounded-lg">
          <Info className="h-5 w-5 text-amber-600" />
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-zinc-800 text-sm">Schedule Modified</h4>
          <p className="text-xs text-zinc-600 mt-1">
            You've {addedCount > 0 ? `added ${addedCount} course${addedCount > 1 ? 's' : ''}` : ''}
            {addedCount > 0 && removedCount > 0 ? ' and ' : ''}
            {removedCount > 0 ? `removed ${removedCount} course${removedCount > 1 ? 's' : ''}` : ''}.
            Regenerate to see optimized schedules with your changes.
          </p>
          <div className="flex gap-2 mt-3">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium text-zinc-600 hover:bg-zinc-100 rounded-lg"
            >
              Later
            </button>
            <button
              onClick={() => { onRegenerate(); onClose(); }}
              className="px-3 py-1.5 text-xs font-medium text-white bg-emoryBlue hover:bg-emoryBlue/90 rounded-lg flex items-center gap-1"
            >
              <RefreshCw className="h-3 w-3" />
              Regenerate
            </button>
          </div>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-zinc-100 rounded">
          <X className="h-4 w-4 text-zinc-400" />
        </button>
      </div>
    </div>
  );
}

// NEW: Engine Toggle Component for Schedule Builder
function EngineToggle({
  selectedEngine,
  onToggle,
  engineStatus,
  disabled,
}: {
  selectedEngine: EngineType;
  onToggle: (engine: EngineType) => void;
  engineStatus: { fibheap: boolean; ml: boolean };
  disabled?: boolean;
}) {
  const fibOffline = engineStatus.fibheap === false;
  const mlOffline = engineStatus.ml === false;

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-emoryBlue">Recommendation Engine</p>
          <p className="text-[11px] text-zinc-600">
            FibHeap = use for grades. ML = Experimental, not for grade.
          </p>
        </div>
        <div className="flex rounded-xl border border-zinc-200 overflow-hidden shadow-sm">
        <button
          onClick={() => onToggle("fibheap")}
          disabled={disabled}
          className={`px-4 py-2 text-xs font-semibold transition-all flex flex-col items-start gap-0.5 min-w-[150px] ${
            selectedEngine === "fibheap"
              ? "bg-emoryBlue text-white"
              : "bg-white text-zinc-700 hover:bg-zinc-50"
          }`}
          title="Fibonacci Heap - stable option for grade-worthy plans"
        >
          <span className="flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5" />
            FibHeap
          </span>
          <span className="text-[10px] opacity-80">
            For grade / most stable {fibOffline ? "(reports offline)" : ""}
          </span>
        </button>
        <button
          onClick={() => onToggle("ml")}
          disabled={disabled}
          className={`px-4 py-2 text-xs font-semibold transition-all flex flex-col items-start gap-0.5 min-w-[150px] border-l border-zinc-200 ${
            selectedEngine === "ml"
              ? "bg-purple-600 text-white"
              : "bg-white text-zinc-700 hover:bg-zinc-50"
          }`}
          title="Machine Learning Model - Experimental"
        >
          <span className="flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5" />
            ML (Experimental)
          </span>
          <span className="text-[10px] opacity-80">
            Experimental - not for grade {mlOffline ? "(reports offline)" : ""}
          </span>
        </button>
      </div>
      </div>
      {(fibOffline || mlOffline) && (
        <p className="mt-2 text-[11px] text-amber-600">
          Engine status reports unavailable on server; selecting ML may fall back to FibHeap.
        </p>
      )}
    </div>
  );
}

function ScheduleCard({ schedule, index, isSelected, onSelect, hasHardConflicts }: { schedule: Schedule; index: number; isSelected: boolean; onSelect: () => void; hasHardConflicts: boolean }) {
  const gersInSchedule = new Set<string>();
  schedule.courses.forEach((c) => {
    getCourseTags(c).forEach((g) => gersInSchedule.add(g));
  });
  return (
    <div onClick={onSelect} className={`cursor-pointer rounded-xl border-2 p-4 transition-all hover:shadow-md ${hasHardConflicts ? 'border-red-300 bg-red-50' : isSelected ? "border-emoryBlue bg-emoryBlue/5 shadow-md" : "border-zinc-200 bg-white hover:border-zinc-300"}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-emoryBlue">Schedule {index + 1}</h3>
            {hasHardConflicts && <span className="text-[10px] text-red-600">⚠️</span>}
          </div>
          <p className="text-xs text-zinc-500">{schedule.course_count} courses • {schedule.total_credits} credits</p>
        </div>
      </div>
      <div className="space-y-1.5">{schedule.courses.slice(0, 5).map((course, i) => <div key={`${course.code}-${i}`} className={`flex items-center justify-between text-xs ${course.hard_time_conflict ? 'text-red-600' : ''}`}><span className="font-medium text-zinc-800 truncate max-w-[140px]">{course.code}</span><span className="text-zinc-500">{course.credits} cr</span></div>)}{schedule.courses.length > 5 && <p className="text-xs text-zinc-400 italic">+{schedule.courses.length - 5} more...</p>}</div>
      {gersInSchedule.size > 0 && <div className="mt-3 flex flex-wrap gap-1">{Array.from(gersInSchedule).map((ger) => <span key={ger} className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">{ger}</span>)}</div>}
      {isSelected && <div className="mt-3 flex items-center gap-1 text-xs text-emoryBlue"><CheckCircle2 className="h-3.5 w-3.5" />Selected</div>}
    </div>
  );
}

function recalculateSchedule(schedule: Schedule): Schedule {
  const totalCredits = schedule.courses.reduce((sum, c) => sum + (parseFloat(String(c.credits)) || 3), 0);
  const totalScore = schedule.courses.reduce((sum, c) => sum + (c.score || 0), 0);
  return {
    ...schedule,
    total_credits: totalCredits,
    total_score: totalScore,
    course_count: schedule.courses.length,
  };
}

export default function ScheduleBuilderPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generated, setGenerated] = useState(false);
  const [showOptionsDrawer, setShowOptionsDrawer] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  
  const [removedCourses, setRemovedCourses] = useState<Set<string>>(new Set());
  const [addedCourses, setAddedCourses] = useState<Map<string, Course>>(new Map());
  
  const [timeUnavailable, setTimeUnavailable] = useState<TimeUnavailableBlock[]>([]);
  const [allSchedulesHaveConflicts, setAllSchedulesHaveConflicts] = useState(false);
  
  // NEW: Track if user has pending modifications
  const [showRegenerateReminder, setShowRegenerateReminder] = useState(false);
  const [pendingModifications, setPendingModifications] = useState({ added: 0, removed: 0 });

  // NEW: Engine state
  const [selectedEngine, setSelectedEngine] = useState<EngineType>(enginePreference.get());
  const [engineStatus, setEngineStatus] = useState({ fibheap: true, ml: true });
  const [engineUsed, setEngineUsed] = useState<string | null>(null);

  const selectedSchedule = schedules[selectedIdx] || null;
  const calendarBlocks = selectedSchedule ? coursesToCalendarBlocks(selectedSchedule.courses) : [];
  const addedCourseCodes = Array.from(addedCourses.values())
    .map((c) => (c.code || c.normalized_code || "").toString().toUpperCase())
    .filter(Boolean);
  const removedCourseCodes = Array.from(removedCourses).map((c) => c.toUpperCase());

  // Fetch engine status
  const fetchEngineStatus = useCallback(async () => {
    try {
      const result = await api.getEngineStatus();
      if (result.success && result.data?.engines) {
        setEngineStatus({
          fibheap: result.data.engines.fibheap?.available ?? false,
          ml: result.data.engines.ml?.available ?? false,
        });
      }
    } catch (err) {
      console.error("Failed to fetch engine status:", err);
    }
  }, []);

  const fetchUserPreferences = useCallback(async () => {
    try {
      const uid = auth.currentUser?.uid;
      if (!uid) return;
      
      const result = await api.getUserData(uid);
      if (result.success && result.data?.preferences?.timeUnavailable) {
        console.log("Loaded time unavailable:", result.data.preferences.timeUnavailable);
        setTimeUnavailable(result.data.preferences.timeUnavailable);
      }
    } catch (err) {
      console.error("Failed to fetch preferences:", err);
    }
  }, []);

  useEffect(() => {
    fetchUserPreferences();
    fetchEngineStatus();
  }, [fetchUserPreferences, fetchEngineStatus]);

  // Handle engine toggle
  const handleEngineToggle = (engine: EngineType) => {
    setSelectedEngine(engine);
    enginePreference.set(engine);
  };

  const fetchSchedules = useCallback(async () => {
    setLoading(true); 
    setError(null);
    setAllSchedulesHaveConflicts(false);
    setShowRegenerateReminder(false);
    setPendingModifications({ added: 0, removed: 0 });
    
    try {
      const uid = auth.currentUser?.uid;
      if (!uid) throw new Error("Not signed in");
      
      await fetchUserPreferences();
      
      const lockedCourses = Array.from(addedCourses.entries()).map(([code], idx) => ({
        code,
        priority: idx + 1
      }));
      
      if (removedCourses.size > 0 || addedCourses.size > 0) {
        await fetch(`${API_URL}/api/preferences`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            uid,
            locked_courses: lockedCourses,
            removed_courses: Array.from(removedCourses)
          })
        });
      }
      
      // Use the selected engine
      console.log(`[INFO] Requesting schedules using ${selectedEngine} engine`);
      
      const res = await fetch(`${API_URL}/api/generate-schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          uid: uid, 
          num_recommendations: selectedEngine === 'ml' ? 1 : 10,
          engine_type: selectedEngine  // NEW: Pass engine type
        })
      });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.error || "Failed to generate schedules");
      
      // Track which engine was actually used
      setEngineUsed(data.engine_used || selectedEngine);
      
      const userDataRes = await api.getUserData(uid);
      const currentTimeUnavailable = userDataRes.success && userDataRes.data?.preferences?.timeUnavailable 
        ? userDataRes.data.preferences.timeUnavailable 
        : timeUnavailable;
      
      console.log("Checking schedules against time unavailable:", currentTimeUnavailable);
      
      // Frontend validation - check each schedule for hard time conflicts
      const schedulesWithMarkers = (data.schedules || []).map((schedule: Schedule) => {
        const coursesWithFlags = schedule.courses.map(course => {
          const hasHardConflict = checkHardTimeConflict(course, currentTimeUnavailable);
          if (hasHardConflict) {
            console.log(`Course ${course.code} (${course.time}) has hard conflict`);
          }
          return {
            ...course,
            user_added: addedCourses.has(course.normalized_code || course.code.toUpperCase().replace(/\s+/g, "")),
            hard_time_conflict: hasHardConflict
          };
        });
        return {
          ...schedule,
          courses: coursesWithFlags
        };
      });
      
      // Filter out schedules that have ANY hard conflicts
      const validSchedules = schedulesWithMarkers.filter((schedule: Schedule) => 
        !schedule.courses.some(course => course.hard_time_conflict)
      );
      
      const allHaveConflicts = schedulesWithMarkers.length > 0 && validSchedules.length === 0;
      
      if (validSchedules.length === 0) {
        setAllSchedulesHaveConflicts(allHaveConflicts);
        // Do not surface conflicted schedules; direct user to Preferences
        setSchedules([]);
        setError(
          allHaveConflicts
            ? "All generated schedules conflict with your unavailable times. Please adjust Preferences to continue."
            : "No schedules could be generated."
        );
        setSelectedIdx(0);
        setGenerated(true);
        return;
      } else {
        setSchedules(validSchedules);
        setSelectedIdx(0);
        setGenerated(true);
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong");
      setSchedules([]);
    }
    finally { setLoading(false); }
  }, [removedCourses, addedCourses, fetchUserPreferences, timeUnavailable, selectedEngine]);

  function handleRemoveCourse(courseCode: string) {
    if (!selectedSchedule) return;
    if (selectedSchedule.courses.length <= 1) {
      alert("Cannot remove the last course. A schedule must have at least one course.");
      return;
    }

    const confirmed = window.confirm(`Remove ${courseCode} from this schedule?\n\nThis course won't appear in regenerated schedules unless you add it back manually.`);
    if (!confirmed) return;

    const normalizedCode = courseCode.toUpperCase().replace(/\s+/g, "");
    
    setRemovedCourses(prev => new Set(prev).add(normalizedCode));
    
    setAddedCourses(prev => {
      const newMap = new Map(prev);
      newMap.delete(normalizedCode);
      return newMap;
    });

    const updatedCourses = selectedSchedule.courses.filter(c => 
      (c.normalized_code || c.code.toUpperCase().replace(/\s+/g, "")) !== normalizedCode
    );
    const updatedSchedule = recalculateSchedule({ ...selectedSchedule, courses: updatedCourses });

    const updatedSchedules = [...schedules];
    updatedSchedules[selectedIdx] = updatedSchedule;
    setSchedules(updatedSchedules);
    
    // Show regenerate reminder
    setPendingModifications(prev => ({ ...prev, removed: prev.removed + 1 }));
    setShowRegenerateReminder(true);
    
    const stillAllHaveConflicts = updatedSchedules.every(schedule => 
      schedule.courses.some(course => course.hard_time_conflict)
    );
    setAllSchedulesHaveConflicts(stillAllHaveConflicts);
  }

  // LOCAL add - NO auto-regenerate, just add locally and show reminder
  function handleAddCourse(newCourse: Course) {
    if (!selectedSchedule) return;

    const normalizedCode = newCourse.normalized_code || newCourse.code.toUpperCase().replace(/\s+/g, "");
    
    const exists = selectedSchedule.courses.some(
      c => (c.normalized_code || c.code.toUpperCase().replace(/\s+/g, "")) === normalizedCode
    );
    if (exists) {
      alert(`${newCourse.code} is already in this schedule.`);
      return;
    }

    setAddedCourses(prev => new Map(prev).set(normalizedCode, newCourse));
    
    setRemovedCourses(prev => {
      const newSet = new Set(prev);
      newSet.delete(normalizedCode);
      return newSet;
    });

    const updatedCourses = [...selectedSchedule.courses, newCourse];
    const updatedSchedule = recalculateSchedule({ ...selectedSchedule, courses: updatedCourses });

    const updatedSchedules = [...schedules];
    updatedSchedules[selectedIdx] = updatedSchedule;
    setSchedules(updatedSchedules);
    
    // Show regenerate reminder popup
    setPendingModifications(prev => ({ ...prev, added: prev.added + 1 }));
    setShowRegenerateReminder(true);
    
    if (newCourse.hard_time_conflict) {
      setAllSchedulesHaveConflicts(updatedSchedules.every(schedule => 
        schedule.courses.some(course => course.hard_time_conflict)
      ));
    }
  }

  async function handleSaveSchedule() {
    if (!schedules.length) return;
    
    const hasConflicts = selectedSchedule?.courses.some(c => c.hard_time_conflict);
    if (hasConflicts) {
      const confirmed = window.confirm("This schedule has courses that conflict with your unavailable times. Are you sure you want to save it?");
      if (!confirmed) return;
    }

    try {
      const uid = auth.currentUser?.uid;
      if (!uid) throw new Error("Not signed in");

      const res = await api.saveSchedules(uid, schedules, selectedIdx);

      if (res.success) {
        alert("Schedules saved successfully!");
      } else {
        alert("Failed to save: " + (res.error || "Unknown error"));
      }
    } catch (err) {
      console.error("Failed to save:", err);
      alert("Failed to save. Please try again.");
    }
  }

  useEffect(() => {
    fetchSchedules();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleExportICS() {
    if (!selectedSchedule) return;
    
    const hasConflicts = selectedSchedule.courses.some(c => c.hard_time_conflict);
    if (hasConflicts) {
      const confirmed = window.confirm("This schedule has courses that conflict with your unavailable times. Are you sure you want to export it?");
      if (!confirmed) return;
    }
    
    downloadICS(selectedSchedule.courses, `DooleyHelpz_Schedule_${selectedIdx + 1}`);
  }

  const selectedHasConflicts = selectedSchedule?.courses.some(c => c.hard_time_conflict) || false;

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 pb-20">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-Gold">
              <img src={applogo} alt="DooleyHelpz" className="h-6 w-6 object-contain" />
            </div>
            <span className="text-lg font-semibold text-emoryBlue">DooleyHelpz</span>
          </Link>
          <Link to="/dashboard" className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100">
            <ChevronLeft className="h-4 w-4" />Dashboard
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="mb-4">
          <EngineToggle
            selectedEngine={selectedEngine}
            onToggle={handleEngineToggle}
            engineStatus={engineStatus}
            disabled={loading}
          />
        </div>

        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-emoryBlue flex items-center gap-2">
              <CalendarDays className="h-7 w-7" />Schedule Builder
            </h1>
            <p className="text-sm text-zinc-600 mt-1">
              Optimized schedules based on your transcript and preferences
              {engineUsed && (
                <span className={`ml-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                  engineUsed === 'ml' ? 'bg-purple-100 text-purple-700' : 'bg-emoryBlue/10 text-emoryBlue'
                }`}>
                  {engineUsed === 'ml' ? <Sparkles className="h-3 w-3" /> : <Cpu className="h-3 w-3" />}
                  {engineUsed === 'ml' ? 'ML Model' : 'FibHeap'}
                </span>
              )}
            </p>
            {(removedCourses.size > 0 || addedCourses.size > 0) && (
              <div className="relative inline-block group mt-1 text-xs text-amber-600">
                <span>
                  {removedCourses.size > 0 && `${removedCourses.size} course(s) excluded`}
                  {removedCourses.size > 0 && addedCourses.size > 0 && " • "}
                  {addedCourses.size > 0 && `${addedCourses.size} course(s) boosted`}
                </span>
                <div className="pointer-events-none absolute left-0 mt-1 hidden w-72 rounded-lg border border-amber-200 bg-white p-3 text-[11px] text-zinc-700 shadow-lg group-hover:block z-20">
                  {removedCourseCodes.length > 0 && (
                    <div className="mb-2">
                      <p className="font-semibold text-amber-700">Excluded</p>
                      <p className="mt-1 break-words">
                        {removedCourseCodes.join(", ")}
                      </p>
                    </div>
                  )}
                  {addedCourseCodes.length > 0 && (
                    <div>
                      <p className="font-semibold text-emerald-700">Boosted</p>
                      <p className="mt-1 break-words">
                        {addedCourseCodes.join(", ")}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Show time unavailable summary */}
            {timeUnavailable.length > 0 && (
              <div className="mt-1 text-xs text-zinc-500">
                Time blocked: {timeUnavailable.map(t => `${t.day} ${t.start}-${t.end}`).join(", ")}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={fetchSchedules} disabled={loading} className="flex items-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />Regenerate
            </button>
            {selectedSchedule && (
              <>
                <button onClick={() => setShowAddModal(true)} className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-100">
                  <Plus className="h-4 w-4" />Add Course
                </button>
                <button onClick={handleSaveSchedule} className="flex items-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50">
                  <CheckCircle2 className="h-4 w-4" />Save
                </button>
                <button onClick={handleExportICS} className="flex items-center gap-2 rounded-xl bg-emoryBlue px-4 py-2 text-sm font-semibold text-white hover:bg-emoryBlue/90">
                  <Download className="h-4 w-4" />Export
                </button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
            <AlertCircle className="h-5 w-5" /><span>{error}</span>
          </div>
        )}
        
        {allSchedulesHaveConflicts && !loading && (
          <div className="mb-6 rounded-lg border-2 border-red-300 bg-red-50 px-4 py-4">
            <div className="flex items-start gap-3">
              <X className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-800">All schedules have time conflicts</h3>
                <p className="mt-1 text-sm text-red-700">
                  All generated schedules contain courses that conflict with your "Time Unavailable" settings. 
                  Please consider:
                </p>
                <ul className="mt-2 text-sm text-red-700 list-disc list-inside space-y-1">
                  <li>Reducing your blocked time slots in <Link to="/preferences" className="underline font-medium">Preferences</Link></li>
                  <li>Adjusting your required courses or credit hours</li>
                  <li>Manually removing conflicting courses from the schedules below</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <RefreshCw className="h-10 w-10 animate-spin text-emoryBlue" />
            <p className="mt-4 text-zinc-600">
              Generating your schedules using {selectedEngine === 'ml' ? 'ML Model' : 'FibHeap'}...
            </p>
          </div>
        )}

        {!loading && generated && schedules.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <BookOpen className="h-12 w-12 text-zinc-300" />
            <h2 className="mt-4 text-lg font-semibold text-zinc-700">Schedule not possible with current settings</h2>
            <p className="mt-2 text-sm text-zinc-500 max-w-md">We couldn't build any options. Try loosening time availability or preferences, then regenerate.</p>
            <div className="mt-4 flex gap-3">
              <Link to="/droptranscript" className="rounded-lg bg-emoryBlue px-4 py-2 text-sm font-medium text-white hover:bg-emoryBlue/90">Upload Transcript</Link>
              <Link to="/preferences" className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50">Set Preferences</Link>
            </div>
          </div>
        )}

        {!loading && schedules.length > 0 && (
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide">{schedules.length} Schedule Options</h2>
              <div className="space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto pr-2">
                {schedules.map((schedule, idx) => {
                  const hasConflicts = schedule.courses.some(c => c.hard_time_conflict);
                  return (
                    <ScheduleCard 
                      key={idx} 
                      schedule={schedule} 
                      index={idx} 
                      isSelected={idx === selectedIdx} 
                      onSelect={() => setSelectedIdx(idx)} 
                      hasHardConflicts={hasConflicts}
                    />
                  );
                })}
              </div>
            </div>

            {selectedSchedule && (
              <div className="space-y-6">
                {selectedHasConflicts && (
                  <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-3">
                    <div className="flex items-center gap-2 text-red-700">
                      <X className="h-5 w-5" />
                      <span className="font-medium">This schedule has time conflicts with your unavailable blocks</span>
                    </div>
                    <p className="mt-1 text-sm text-red-600">
                      Remove the conflicting courses (marked in red) or adjust your preferences.
                    </p>
                  </div>
                )}
                
                <div>
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-emoryBlue">Weekly View</h2>
                    <div className="flex items-center gap-2">
                      <button onClick={() => setSelectedIdx(Math.max(0, selectedIdx - 1))} disabled={selectedIdx === 0} className="rounded-lg p-1.5 hover:bg-zinc-100 disabled:opacity-30">
                        <ChevronLeft className="h-5 w-5" />
                      </button>
                      <span className="text-sm text-zinc-600">{selectedIdx + 1} / {schedules.length}</span>
                      <button onClick={() => setSelectedIdx(Math.min(schedules.length - 1, selectedIdx + 1))} disabled={selectedIdx === schedules.length - 1} className="rounded-lg p-1.5 hover:bg-zinc-100 disabled:opacity-30">
                        <ChevronRight className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                  <WeeklyCalendar blocks={calendarBlocks} timeUnavailable={timeUnavailable} />
                  
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-500">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded border-dashed border border-gray-400 bg-gray-100/60"></div>
                      <span>User added</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3 text-amber-600" />
                      <span>Outside preferences (your preferences and internal preferences)</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded border border-red-400 bg-red-100"></div>
                      <span>Time conflict (hard)</span>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-emoryBlue">Courses ({selectedSchedule.courses.length})</h2>
                    <p className="text-xs text-zinc-500">Hover to remove</p>
                  </div>
                  <div className="space-y-2">
                    {selectedSchedule.courses.map((course, idx) => (
                      <CourseDetailRow
                        key={`${course.code}-${idx}`}
                        course={course}
                        onRemove={() => handleRemoveCourse(course.code)}
                        canRemove={selectedSchedule.courses.length > 1}
                      />
                    ))}
                  </div>
                  <div className="mt-4 rounded-lg bg-emoryBlue/5 border border-emoryBlue/20 p-4">
                    <div className="grid grid-cols-2 gap-4 text-center">
                      <div>
                        <p className="text-2xl font-bold text-emoryBlue">{selectedSchedule.total_credits}</p>
                        <p className="text-xs text-zinc-600">Credits</p>
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-emoryBlue">{selectedSchedule.courses.length}</p>
                        <p className="text-xs text-zinc-600">Courses</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {schedules.length > 0 && (
        <ScheduleOptionsDrawer
          schedules={schedules}
          selectedIdx={selectedIdx}
          onSelect={setSelectedIdx}
          isOpen={showOptionsDrawer}
          onToggle={() => setShowOptionsDrawer(!showOptionsDrawer)}
        />
      )}

      <AddCourseModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAddCourse={handleAddCourse}
        currentCourses={selectedSchedule?.courses || []}
        timeUnavailable={timeUnavailable}
      />
      
      {/* Regenerate reminder popup */}
      <RegenerateReminderPopup
        isOpen={showRegenerateReminder}
        onClose={() => setShowRegenerateReminder(false)}
        onRegenerate={fetchSchedules}
        addedCount={pendingModifications.added}
        removedCount={pendingModifications.removed}
      />
    </div>
  );
}
