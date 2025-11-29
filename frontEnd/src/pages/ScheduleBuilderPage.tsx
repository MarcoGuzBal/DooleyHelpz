// src/pages/ScheduleBuilderPage.tsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  CalendarDays,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Star,
  Clock,
  BookOpen,
  GraduationCap,
} from "lucide-react";
import { getOrCreateSharedId } from "../utils/anonID";

import applogo from "../assets/dooleyHelpzAppLogo.png";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5001";

// Types
type Course = {
  code: string;
  title: string;
  professor: string;
  credits: number | string;
  time: string;
  meeting?: { day: string; time: string; location: string }[];
  rmp?: { rating: number; num_ratings: number } | null;
  score: number;
  ger: string | string[] | null;
  normalized_code: string;
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
};

// Constants
const DAYS: CalendarBlock["day"][] = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const START_HOUR = 8;
const END_HOUR = 21;
const TOTAL_MINUTES = (END_HOUR - START_HOUR) * 60;

// Color palette for courses
const COURSE_COLORS = [
  "bg-blue-100 border-blue-300 text-blue-800",
  "bg-emerald-100 border-emerald-300 text-emerald-800",
  "bg-amber-100 border-amber-300 text-amber-800",
  "bg-purple-100 border-purple-300 text-purple-800",
  "bg-rose-100 border-rose-300 text-rose-800",
  "bg-cyan-100 border-cyan-300 text-cyan-800",
  "bg-orange-100 border-orange-300 text-orange-800",
];

// FIXED: Parse time string - handles "10am", "4pm", "10:30am", etc.
function parseTimeString(timeStr: string): { start: string; end: string } | null {
  if (!timeStr) return null;

  // Normalize: add :00 only to times WITHOUT minutes (e.g., "10am" -> "10:00am")
  // Use negative lookbehind to avoid matching "15pm" in "5:15pm"
  const normalized = timeStr.replace(/(?<![:\d])(\d{1,2})(am|pm)/gi, "$1:00$2");

  // Match patterns like "9:00am-10:15am" or "1:30pm-2:45pm"
  const match = normalized.match(/(\d{1,2}):(\d{2})\s*(am|pm)\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)/i);
  if (!match) return null;

  let startHour = parseInt(match[1]);
  const startMin = match[2];
  const startAmPm = match[3].toLowerCase();

  let endHour = parseInt(match[4]);
  const endMin = match[5];
  const endAmPm = match[6].toLowerCase();

  // Convert to 24h
  if (startAmPm === "pm" && startHour !== 12) startHour += 12;
  if (startAmPm === "am" && startHour === 12) startHour = 0;
  if (endAmPm === "pm" && endHour !== 12) endHour += 12;
  if (endAmPm === "am" && endHour === 12) endHour = 0;

  return {
    start: `${startHour.toString().padStart(2, "0")}:${startMin}`,
    end: `${endHour.toString().padStart(2, "0")}:${endMin}`,
  };
}

// FIXED: Parse days from string like "MW", "TTh", "MWF", "T"
function parseDays(dayStr: string): CalendarBlock["day"][] {
  if (!dayStr) return [];

  const days: CalendarBlock["day"][] = [];
  const cleaned = dayStr.replace(/\s/g, "");
  let i = 0;

  while (i < cleaned.length) {
    const twoChar = cleaned.slice(i, i + 2);
    if (twoChar === "Th") {
      days.push("Thu");
      i += 2;
    } else if (twoChar === "Tu") {
      days.push("Tue");
      i += 2;
    } else {
      const char = cleaned[i];
      if (char === "M") days.push("Mon");
      else if (char === "T") days.push("Tue");
      else if (char === "W") days.push("Wed");
      else if (char === "F") days.push("Fri");
      i++;
    }
  }

  return days;
}

function minutesFromStart(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return (h - START_HOUR) * 60 + m;
}

// FIXED: Better course to calendar block conversion
function coursesToCalendarBlocks(courses: Course[]): CalendarBlock[] {
  const blocks: CalendarBlock[] = [];

  courses.forEach((course, idx) => {
    const color = COURSE_COLORS[idx % COURSE_COLORS.length];

    // Try meeting array first (has location)
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
            });
          });
        }
      });
    } else if (course.time) {
      // Parse from combined time string like "TTh 8:30am-9:45am"
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
          });
        });
      }
    }
  });

  return blocks;
}

// Format 24h time to 12h
function formatTime12(time24: string): string {
  const [h, m] = time24.split(":").map(Number);
  const ampm = h >= 12 ? "pm" : "am";
  const h12 = h % 12 || 12;
  return `${h12}:${m.toString().padStart(2, "0")}${ampm}`;
}

// ICS Export
function generateICS(courses: Course[], scheduleName: string): string {
  const lines: string[] = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//DooleyHelpz//Schedule Builder//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${scheduleName}`,
  ];

  const semesterStart = new Date("2026-01-12");
  const semesterEnd = new Date("2026-04-24");
  const dayOffsets: Record<string, number> = { Mon: 0, Tue: 1, Wed: 2, Thu: 3, Fri: 4 };

  const blocks = coursesToCalendarBlocks(courses);

  blocks.forEach((block, idx) => {
    const dayOffset = dayOffsets[block.day] || 0;
    const firstOccurrence = new Date(semesterStart);
    firstOccurrence.setDate(firstOccurrence.getDate() + dayOffset);

    const [startH, startM] = block.start.split(":").map(Number);
    const [endH, endM] = block.end.split(":").map(Number);

    const dtstart = new Date(firstOccurrence);
    dtstart.setHours(startH, startM, 0, 0);
    const dtend = new Date(firstOccurrence);
    dtend.setHours(endH, endM, 0, 0);

    const formatDateLocal = (d: Date) => {
      const year = d.getFullYear();
      const month = (d.getMonth() + 1).toString().padStart(2, "0");
      const day = d.getDate().toString().padStart(2, "0");
      const hours = d.getHours().toString().padStart(2, "0");
      const mins = d.getMinutes().toString().padStart(2, "0");
      return `${year}${month}${day}T${hours}${mins}00`;
    };

    const formatDate = (d: Date) => d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
    const untilDate = new Date(semesterEnd);
    const rruleDay = ["MO", "TU", "WE", "TH", "FR"][dayOffset];

    lines.push("BEGIN:VEVENT");
    lines.push(`UID:${Date.now()}-${idx}@dooleyhelpz`);
    lines.push(`DTSTAMP:${formatDate(new Date())}`);
    lines.push(`DTSTART;TZID=America/New_York:${formatDateLocal(dtstart)}`);
    lines.push(`DTEND;TZID=America/New_York:${formatDateLocal(dtend)}`);
    lines.push(`RRULE:FREQ=WEEKLY;BYDAY=${rruleDay};UNTIL=${formatDate(untilDate)}`);
    lines.push(`SUMMARY:${block.course} - ${block.title}`);
    lines.push(`DESCRIPTION:Professor: ${block.professor || "TBA"}`);
    if (block.location) lines.push(`LOCATION:${block.location}`);
    lines.push("END:VEVENT");
  });

  lines.push("END:VCALENDAR");
  return lines.join("\r\n");
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

// Calendar Component
function WeeklyCalendar({ blocks }: { blocks: CalendarBlock[] }) {
  const byDay: Record<CalendarBlock["day"], CalendarBlock[]> = {
    Mon: [], Tue: [], Wed: [], Thu: [], Fri: [],
  };
  blocks.forEach((b) => byDay[b.day].push(b));

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="grid grid-cols-[3.5rem_repeat(5,1fr)] gap-1 text-xs">
        {/* Time labels */}
        <div className="relative h-[520px]">
          {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, idx) => {
            const hour = START_HOUR + idx;
            const top = (idx / (END_HOUR - START_HOUR)) * 100;
            return (
              <div
                key={hour}
                className="absolute left-0 -translate-y-1/2 text-[10px] text-zinc-400 font-medium"
                style={{ top: `${top}%` }}
              >
                {hour > 12 ? hour - 12 : hour}:00 {hour >= 12 ? "PM" : "AM"}
              </div>
            );
          })}
        </div>

        {/* Day columns */}
        {DAYS.map((day) => (
          <div key={day} className="relative h-[520px] border-l border-zinc-100">
            <div className="sticky top-0 z-10 mb-1 bg-white pb-1 text-center text-xs font-semibold text-emoryBlue">
              {day}
            </div>
            {/* Grid lines */}
            {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, idx) => {
              const top = (idx / (END_HOUR - START_HOUR)) * 100;
              return (
                <div
                  key={idx}
                  className="absolute left-0 right-0 border-t border-dashed border-zinc-100"
                  style={{ top: `${top}%` }}
                />
              );
            })}

            {/* Course blocks */}
            {byDay[day].map((block, i) => {
              const startMin = minutesFromStart(block.start);
              const endMin = minutesFromStart(block.end);
              const top = (startMin / TOTAL_MINUTES) * 100;
              const height = ((endMin - startMin) / TOTAL_MINUTES) * 100;

              return (
                <div
                  key={`${block.course}-${i}`}
                  className={`absolute left-0.5 right-0.5 overflow-hidden rounded-lg border px-1.5 py-1 shadow-sm cursor-pointer hover:shadow-md transition-shadow ${block.color}`}
                  style={{ top: `${top}%`, height: `${height}%`, minHeight: "2.5rem" }}
                  title={`${block.course}: ${block.title}\n${block.professor || "TBA"}\n${block.location || ""}\n${formatTime12(block.start)}-${formatTime12(block.end)}`}
                >
                  <div className="font-semibold text-[11px] leading-tight truncate">
                    {block.course}
                  </div>
                  {block.location && block.location !== "TBA" && block.location !== "TBD" && (
                    <div className="text-[9px] opacity-80 truncate">{block.location}</div>
                  )}
                  <div className="text-[9px] opacity-70">
                    {formatTime12(block.start)}-{formatTime12(block.end)}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

// Schedule Card Component
function ScheduleCard({
  schedule,
  index,
  isSelected,
  onSelect,
}: {
  schedule: Schedule;
  index: number;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const gersInSchedule = new Set<string>();
  schedule.courses.forEach((c) => {
    if (c.ger) {
      const gers = Array.isArray(c.ger) ? c.ger : [c.ger];
      gers.forEach((g) => gersInSchedule.add(g));
    }
  });

  return (
    <div
      onClick={onSelect}
      className={`cursor-pointer rounded-xl border-2 p-4 transition-all hover:shadow-md ${
        isSelected
          ? "border-emoryBlue bg-emoryBlue/5 shadow-md"
          : "border-zinc-200 bg-white hover:border-zinc-300"
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-emoryBlue">Schedule {index + 1}</h3>
          <p className="text-xs text-zinc-500">
            {schedule.course_count} courses • {schedule.total_credits} credits
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5">
          <Star className="h-3 w-3 text-amber-600" />
          <span className="text-xs font-medium text-amber-700">
            {schedule.total_score.toFixed(0)}
          </span>
        </div>
      </div>

      <div className="space-y-1.5">
        {schedule.courses.slice(0, 5).map((course, i) => (
          <div key={`${course.code}-${i}`} className="flex items-center justify-between text-xs">
            <span className="font-medium text-zinc-800 truncate max-w-[140px]">{course.code}</span>
            <span className="text-zinc-500">{course.credits} cr</span>
          </div>
        ))}
        {schedule.courses.length > 5 && (
          <p className="text-xs text-zinc-400 italic">+{schedule.courses.length - 5} more...</p>
        )}
      </div>

      {gersInSchedule.size > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {Array.from(gersInSchedule).map((ger) => (
            <span key={ger} className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
              {ger}
            </span>
          ))}
        </div>
      )}

      {isSelected && (
        <div className="mt-3 flex items-center gap-1 text-xs text-emoryBlue">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Selected
        </div>
      )}
    </div>
  );
}

// Course Detail Row
function CourseDetailRow({ course }: { course: Course }) {
  const gers = course.ger ? (Array.isArray(course.ger) ? course.ger : [course.ger]) : [];

  return (
    <div className="flex items-center justify-between rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2">
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-emoryBlue">{course.code}</span>
          {gers.map((g) => (
            <span key={g} className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
              {g}
            </span>
          ))}
        </div>
        <p className="text-sm text-zinc-600 truncate max-w-md">{course.title}</p>
        <div className="flex items-center gap-3 mt-1 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <GraduationCap className="h-3 w-3" />
            {course.professor || "TBA"}
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {course.time || "TBA"}
          </span>
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm font-medium text-zinc-700">{course.credits} cr</div>
        {course.rmp && course.rmp.rating > 0 && (
          <div className="flex items-center gap-1 text-xs text-amber-600">
            <Star className="h-3 w-3 fill-amber-500" />
            {course.rmp.rating.toFixed(1)}
          </div>
        )}
      </div>
    </div>
  );
}

// Main Component
export default function ScheduleBuilderPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generated, setGenerated] = useState(false);

  const selectedSchedule = schedules[selectedIdx] || null;
  const calendarBlocks = selectedSchedule ? coursesToCalendarBlocks(selectedSchedule.courses) : [];

  async function fetchSchedules() {
    setLoading(true);
    setError(null);

    try {
      const sharedId = getOrCreateSharedId();
      const res = await fetch(`${API_URL}/api/generate-schedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ shared_id: sharedId, num_recommendations: 10 }),
      });

      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.error || "Failed to generate schedules");

      setSchedules(data.schedules || []);
      setSelectedIdx(0);
      setGenerated(true);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSchedules();
  }, []);

  function handleExportICS() {
    if (!selectedSchedule) return;
    downloadICS(selectedSchedule.courses, `DooleyHelpz_Schedule_${selectedIdx + 1}`);
  }

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900">
      {/* Header */}
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <Link to="/dashboard" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-Gold">
              <img src={applogo} alt="DooleyHelpz" className="h-6 w-6 object-contain" />
            </div>
            <span className="text-lg font-semibold text-emoryBlue">DooleyHelpz</span>
          </Link>
          <Link to="/dashboard" className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100">
            <ChevronLeft className="h-4 w-4" />
            Dashboard
          </Link>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-7xl px-4 py-6">
        {/* Title */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-emoryBlue flex items-center gap-2">
              <CalendarDays className="h-7 w-7" />
              Schedule Builder
            </h1>
            <p className="text-sm text-zinc-600 mt-1">
              Optimized schedule options based on your transcript and preferences
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchSchedules}
              disabled={loading}
              className="flex items-center gap-2 rounded-xl border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Regenerate
            </button>
            {selectedSchedule && (
              <button
                onClick={handleExportICS}
                className="flex items-center gap-2 rounded-xl bg-emoryBlue px-4 py-2 text-sm font-semibold text-white hover:bg-emoryBlue/90"
              >
                <Download className="h-4 w-4" />
                Export to Calendar
              </button>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
            <AlertCircle className="h-5 w-5" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <RefreshCw className="h-10 w-10 animate-spin text-emoryBlue" />
            <p className="mt-4 text-zinc-600">Generating your schedules...</p>
            <p className="text-sm text-zinc-400">Analyzing prerequisites, GERs, and time conflicts</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && generated && schedules.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <BookOpen className="h-12 w-12 text-zinc-300" />
            <h2 className="mt-4 text-lg font-semibold text-zinc-700">No schedules generated</h2>
            <p className="mt-2 text-sm text-zinc-500 max-w-md">
              Make sure you've uploaded your transcript and set your preferences.
            </p>
            <div className="mt-4 flex gap-3">
              <Link to="/droptranscript" className="rounded-lg bg-emoryBlue px-4 py-2 text-sm font-medium text-white hover:bg-emoryBlue/90">
                Upload Transcript
              </Link>
              <Link to="/preferences" className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50">
                Set Preferences
              </Link>
            </div>
          </div>
        )}

        {/* Main Content */}
        {!loading && schedules.length > 0 && (
          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            {/* Schedule List */}
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-zinc-700 uppercase tracking-wide">
                {schedules.length} Schedule Options
              </h2>
              <div className="space-y-3 max-h-[calc(100vh-280px)] overflow-y-auto pr-2">
                {schedules.map((schedule, idx) => (
                  <ScheduleCard
                    key={idx}
                    schedule={schedule}
                    index={idx}
                    isSelected={idx === selectedIdx}
                    onSelect={() => setSelectedIdx(idx)}
                  />
                ))}
              </div>
            </div>

            {/* Selected Schedule */}
            {selectedSchedule && (
              <div className="space-y-6">
                {/* Calendar */}
                <div>
                  <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-emoryBlue">Weekly View</h2>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSelectedIdx(Math.max(0, selectedIdx - 1))}
                        disabled={selectedIdx === 0}
                        className="rounded-lg p-1.5 hover:bg-zinc-100 disabled:opacity-30"
                      >
                        <ChevronLeft className="h-5 w-5" />
                      </button>
                      <span className="text-sm text-zinc-600">{selectedIdx + 1} / {schedules.length}</span>
                      <button
                        onClick={() => setSelectedIdx(Math.min(schedules.length - 1, selectedIdx + 1))}
                        disabled={selectedIdx === schedules.length - 1}
                        className="rounded-lg p-1.5 hover:bg-zinc-100 disabled:opacity-30"
                      >
                        <ChevronRight className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                  <WeeklyCalendar blocks={calendarBlocks} />
                </div>

                {/* Course List */}
                <div>
                  <h2 className="mb-3 text-lg font-semibold text-emoryBlue">
                    Courses ({selectedSchedule.courses.length})
                  </h2>
                  <div className="space-y-2">
                    {selectedSchedule.courses.map((course, idx) => (
                      <CourseDetailRow key={`${course.code}-${idx}`} course={course} />
                    ))}
                  </div>

                  {/* Summary */}
                  <div className="mt-4 rounded-lg bg-emoryBlue/5 border border-emoryBlue/20 p-4">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <p className="text-2xl font-bold text-emoryBlue">{selectedSchedule.total_credits}</p>
                        <p className="text-xs text-zinc-600">Total Credits</p>
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-emoryBlue">{selectedSchedule.courses.length}</p>
                        <p className="text-xs text-zinc-600">Courses</p>
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-amber-600">{selectedSchedule.total_score.toFixed(0)}</p>
                        <p className="text-xs text-zinc-600">Match Score</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}