import { useNavigate, Link } from "react-router-dom";
import { useState, useEffect, useCallback } from "react";
import { auth } from "../firebase";
import { api } from "../utils/api";

import applogo from "../assets/dooleyHelpzAppLogo.png";
import mascot from "../assets/EHMascot.png";

type ScheduleMeeting = {
  day: "Mon" | "Tue" | "Wed" | "Thu" | "Fri";
  course: string;
  section: string;
  start: string;
  end: string;
  colorClass?: string;
};

// Dummy/Example data - shown when user hasn't uploaded anything yet
const DUMMY_COURSES: string[] = [
  "CS 253", "CS 224", "MATH 221", "QTM 100", "CHEM 150",
  "CS 334", "CS 326", "MATH 250", "CS 255", "CS 370",
];

const DUMMY_SCHEDULE: ScheduleMeeting[] = [
  { day: "Mon", course: "CS 253", section: "Sec 1", start: "09:00", end: "10:15" },
  { day: "Mon", course: "MATH 221", section: "Sec 2", start: "13:00", end: "14:15" },
  { day: "Tue", course: "CS 224", section: "Sec 1", start: "11:30", end: "12:45" },
  { day: "Wed", course: "CS 253", section: "Sec 1", start: "09:00", end: "10:15" },
  { day: "Wed", course: "QTM 100", section: "Sec 3", start: "15:00", end: "16:15" },
  { day: "Thu", course: "CS 224", section: "Sec 1", start: "11:30", end: "12:45" },
  { day: "Fri", course: "CHEM 150", section: "Lab A", start: "10:00", end: "12:00" },
];

// MUST match ScheduleBuilderPage COURSE_COLORS so colors are identical
const COURSE_COLORS = [
  "bg-blue-100 border-blue-300 text-blue-800",
  "bg-emerald-100 border-emerald-300 text-emerald-800",
  "bg-amber-100 border-amber-300 text-amber-800",
  "bg-purple-100 border-purple-300 text-purple-800",
  "bg-rose-100 border-rose-300 text-rose-800",
  "bg-cyan-100 border-cyan-300 text-cyan-800",
  "bg-orange-100 border-orange-300 text-orange-800",
];

const DAYS: ScheduleMeeting["day"][] = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const START_HOUR = 8;
const END_HOUR = 21;
const TOTAL_MINUTES = (END_HOUR - START_HOUR) * 60;
const HOUR_HEIGHT_PX = 40;
const CALENDAR_HEIGHT = (END_HOUR - START_HOUR) * HOUR_HEIGHT_PX;

function minutesFromStart(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return (h - START_HOUR) * 60 + m;
}

// now accepts an optional colorClass so we can match ScheduleBuilder colors
function parseTimeToMeetings(
  course: string,
  timeStr: string,
  colorClass?: string
): ScheduleMeeting[] {
  if (!timeStr) return [];
  const meetings: ScheduleMeeting[] = [];
  const firstSpaceIdx = timeStr.indexOf(" ");
  if (firstSpaceIdx === -1) return [];

  const dayPart = timeStr.slice(0, firstSpaceIdx);
  const timePart = timeStr.slice(firstSpaceIdx + 1);

  const days: ScheduleMeeting["day"][] = [];
  let i = 0;
  while (i < dayPart.length) {
    const twoChar = dayPart.slice(i, i + 2);
    if (twoChar === "Th") {
      days.push("Thu");
      i += 2;
    } else if (twoChar === "Tu") {
      days.push("Tue");
      i += 2;
    } else {
      const char = dayPart[i];
      if (char === "M") days.push("Mon");
      else if (char === "T") days.push("Tue");
      else if (char === "W") days.push("Wed");
      else if (char === "F") days.push("Fri");
      i++;
    }
  }

  const normalized = timePart.replace(
    /(?<![:\d])(\d{1,2})(am|pm)/gi,
    "$1:00$2"
  );
  const match = normalized.match(
    /(\d{1,2}):(\d{2})\s*(am|pm)\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)/i
  );
  if (!match) return [];

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

  const start = `${startHour.toString().padStart(2, "0")}:${startMin}`;
  const end = `${endHour.toString().padStart(2, "0")}:${endMin}`;

  days.forEach((day) => {
    meetings.push({
      day,
      course,
      section: "Sec 1",
      start,
      end,
      colorClass,
    });
  });

  return meetings;
}

function SchedulePreview({
  meetings,
  isExample,
}: {
  meetings: ScheduleMeeting[];
  isExample: boolean;
}) {
  const byDay: Record<ScheduleMeeting["day"], ScheduleMeeting[]> = {
    Mon: [],
    Tue: [],
    Wed: [],
    Thu: [],
    Fri: [],
  };
  meetings.forEach((m) => byDay[m.day].push(m));

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-emoryBlue">Weekly view</h3>
      </div>
      <div className="grid grid-cols-[3rem_repeat(5,1fr)] gap-2 text-xs">
        <div className="relative" style={{ height: CALENDAR_HEIGHT }}>
          {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, idx) => {
            const hour = START_HOUR + idx;
            const top = (idx / (END_HOUR - START_HOUR)) * 100;
            return (
              <div
                key={hour}
                className="absolute left-0 -translate-y-1/2 text-[10px] text-zinc-400"
                style={{ top: `${top}%` }}
              >
                {hour.toString().padStart(2, "0")}:00
              </div>
            );
          })}
        </div>
        {DAYS.map((day) => (
          <div
            key={day}
            className="relative border-l border-zinc-100"
            style={{ height: CALENDAR_HEIGHT }}
          >
            <div className="mb-1 text-center text-[11px] font-semibold text-emoryBlue">
              {day}
            </div>
            {Array.from({ length: END_HOUR - START_HOUR + 1 }).map(
              (_, idx) => {
                const top = (idx / (END_HOUR - START_HOUR)) * 100;
                return (
                  <div
                    key={idx}
                    className="absolute left-0 right-0 border-t border-dashed border-zinc-100"
                    style={{ top: `${top}%` }}
                  />
                );
              }
            )}
            {byDay[day].map((m, i) => {
              const startMin = minutesFromStart(m.start);
              const endMin = minutesFromStart(m.end);
              const top = (startMin / TOTAL_MINUTES) * 100;
              const height = ((endMin - startMin) / TOTAL_MINUTES) * 100;

              const colorClasses = isExample
                ? "border-zinc-300 bg-zinc-100"
                : m.colorClass || "border-emoryBlue/30 bg-emoryBlue/10";

              return (
                <div
                  key={`${m.course}-${m.section}-${i}`}
                  className={`absolute left-1 right-1 overflow-hidden rounded-lg border px-1.5 py-1 text-[10px] shadow-sm ${colorClasses}`}
                  style={{ top: `${top}%`, height: `${height}%` }}
                >
                  <div
                    className={`font-semibold leading-tight ${
                      isExample ? "text-zinc-600" : "text-emoryBlue"
                    }`}
                  >
                    {m.course} – {m.section}
                  </div>
                  <div className="mt-0.5 text-[9px] text-zinc-700">
                    {m.start}–{m.end}
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

export default function DashboardPage() {
  const user = auth.currentUser;
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [userCourses, setUserCourses] = useState<string[]>([]);
  // now an array of schedules (up to 10)
  const [savedSchedules, setSavedSchedules] = useState<any[]>([]);
  const [selectedScheduleIdx, setSelectedScheduleIdx] = useState(0);
  const [scheduleSelectorOpen, setScheduleSelectorOpen] = useState(false);

  const [hasTranscript, setHasTranscript] = useState(false);
  const [hasPreferences, setHasPreferences] = useState(false);
  // Only show error for actual network/server errors, not for "no data yet"
  const [networkError, setNetworkError] = useState<string | null>(null);

  const fetchUserData = useCallback(async () => {
    setLoading(true);
    setNetworkError(null);

    try {
      const uid = auth.currentUser?.uid; if (!uid) throw new Error("Not signed in");

      const result = await api.getUserData(uid);
      console.log("Dashboard: API result:", result);

      if (result.success && result.data) {
        const data = result.data;

        setHasTranscript(data.has_courses === true);
        setHasPreferences(data.has_preferences === true);

        // Extract courses from transcript data
        if (data.courses) {
          const allCourses: string[] = [];
          const courseData = data.courses;

          if (Array.isArray(courseData.incoming_transfer_courses)) {
            allCourses.push(...courseData.incoming_transfer_courses);
          }
          if (Array.isArray(courseData.incoming_test_courses)) {
            allCourses.push(...courseData.incoming_test_courses);
          }
          if (Array.isArray(courseData.emory_courses)) {
            allCourses.push(...courseData.emory_courses);
          }
          if (Array.isArray(courseData.spring_2026_courses)) {
            allCourses.push(...courseData.spring_2026_courses);
          }

          setUserCourses(allCourses);
        } else {
          setUserCourses([]);
        }

        // Saved schedules:
        // - preferred shape: data.saved_schedule.schedules: Schedule[]
        // - backward compatible: data.saved_schedule.schedule: Schedule
        if (data.has_saved_schedule && data.saved_schedule) {
          const saved = data.saved_schedule;
          let schedulesArray: any[] = [];

          if (Array.isArray(saved.schedules) && saved.schedules.length > 0) {
            schedulesArray = saved.schedules;
          } else if (
            saved.schedule &&
            Array.isArray(saved.schedule.courses)
          ) {
            schedulesArray = [saved.schedule];
          }

          setSavedSchedules(schedulesArray);
          setSelectedScheduleIdx(0);
          setScheduleSelectorOpen(false);
        } else {
          setSavedSchedules([]);
          setSelectedScheduleIdx(0);
          setScheduleSelectorOpen(false);
        }

        setNetworkError(null);
      } else if (result.error) {
        console.error("Dashboard: API error:", result.error);
        setNetworkError(result.error);
      }
    } catch (err) {
      console.error("Dashboard: Network error:", err);
      setNetworkError(
        err instanceof Error ? err.message : "Could not connect to server"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch data on mount
  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);

  // Re-fetch when window gains focus (user might have just uploaded transcript or saved schedules)
  useEffect(() => {
    const handleFocus = () => {
      console.log("Dashboard: Window focused, re-fetching data...");
      fetchUserData();
    };

    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [fetchUserData]);

  const selectedSchedule = savedSchedules[selectedScheduleIdx];

  // Convert selected saved schedule to meetings format with same colors as ScheduleBuilder
  const scheduleFromBackend: ScheduleMeeting[] = selectedSchedule?.courses
    ? selectedSchedule.courses.flatMap((course: any, idx: number) => {
        const colorClass =
          COURSE_COLORS[idx % COURSE_COLORS.length] || COURSE_COLORS[0];
        return parseTimeToMeetings(
          course.code || course.normalized_code,
          course.time,
          colorClass
        );
      })
    : [];

  // Example schedule with the same color palette used in ScheduleBuilder
  const exampleColorMap = new Map<string, string>();
  const exampleSchedule: ScheduleMeeting[] = DUMMY_SCHEDULE.map((m) => {
    if (!exampleColorMap.has(m.course)) {
      const color =
        COURSE_COLORS[exampleColorMap.size % COURSE_COLORS.length] ||
        COURSE_COLORS[0];
      exampleColorMap.set(m.course, color);
    }
    return {
      ...m,
      colorClass: exampleColorMap.get(m.course),
    };
  });

  // Determine what to display
  const hasRealCourses = userCourses.length > 0;
  const hasRealSchedule =
    savedSchedules.length > 0 && scheduleFromBackend.length > 0;

  const displayCourses = hasRealCourses ? userCourses : DUMMY_COURSES;
  const displaySchedule = hasRealSchedule ? scheduleFromBackend : exampleSchedule;

  const handleLogout = async () => {
    await auth.signOut();
    navigate("/");
  };

  // Manual refresh button handler
  const handleRefresh = () => {
    fetchUserData();
  };

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-Gold">
              <img
                src={applogo}
                alt="DooleyHelpz"
                className="h-6 w-6 object-contain"
              />
            </div>
            <span className="text-lg font-semibold text-emoryBlue">
              DooleyHelpz
            </span>
          </Link>
          <div className="flex items-center gap-3">
            {user && (
              <span className="hidden text-xs text-zinc-600 sm:inline">
                {user.email}
              </span>
            )}
            <button
              onClick={handleRefresh}
              className="rounded-xl border border-zinc-300 px-3 py-1.5 text-xs font-semibold text-zinc-600 hover:bg-zinc-50"
              title="Refresh data"
            >
              ↻ Refresh
            </button>
            <button
              onClick={handleLogout}
              className="rounded-xl bg-emoryBlue px-3 py-1.5 text-xs font-semibold text-white hover:bg-emoryBlue/90"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-12 pt-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-zinc-500">Loading your data...</div>
          </div>
        ) : (
          <>
            {/* Only show error for actual network/server errors */}
            {networkError && (
              <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
                <p className="text-sm text-rose-700">
                  <strong>Connection error:</strong> {networkError}
                </p>
                <p className="mt-1 text-xs text-rose-600">
                  Check your internet connection or try again later.
                </p>
                <button
                  onClick={handleRefresh}
                  className="mt-2 rounded bg-rose-100 px-3 py-1 text-xs font-medium text-rose-700 hover:bg-rose-200"
                >
                  Try Again
                </button>
              </div>
            )}

            {/* Welcome Section */}
            <section className="mb-8 grid items-center gap-6 rounded-3xl border border-zinc-200 bg-linear-to-tr from-emoryBlue/5 via-white to-amber-50 p-6 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <div>
                <h1 className="text-2xl font-bold text-emoryBlue md:text-3xl">
                  Welcome, {user?.email?.split("@")[0] || "Guest"}!
                </h1>
                <p className="mt-2 text-sm text-zinc-600">
                  This dashboard pulls together your transcript, preferences,
                  and schedules so you can plan calmer semesters.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                      hasTranscript
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {hasTranscript
                      ? "✓ Transcript uploaded"
                      : "⚠ No transcript"}
                  </span>
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                      hasPreferences
                        ? "bg-green-100 text-green-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {hasPreferences
                      ? "✓ Preferences set"
                      : "⚠ No preferences"}
                  </span>
                  {hasRealSchedule && (
                    <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                      ✓ Schedule saved
                    </span>
                  )}
                </div>
              </div>
              <div className="flex justify-center md:justify-end">
                <img
                  src={mascot}
                  alt="DooleyHelpz Mascot"
                  className="h-32 w-auto object-contain drop-shadow-sm"
                />
              </div>
            </section>

            {/* Action Cards */}
            <section className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="flex flex-col justify-between rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                <div>
                  <h2 className="text-sm font-semibold text-emoryBlue">
                    Update Transcript
                  </h2>
                  <p className="mt-1 text-xs text-zinc-600">
                    Upload your latest Emory transcript PDF.
                  </p>
                  {hasTranscript && (
                    <p className="mt-2 text-xs text-green-600">
                      ✓ {userCourses.length} courses loaded
                    </p>
                  )}
                </div>
                <button
                  onClick={() => navigate("/droptranscript")}
                  className="mt-3 rounded-xl bg-emoryBlue px-3 py-1.5 text-xs font-semibold text-white hover:bg-emoryBlue/90"
                >
                  {hasTranscript ? "Update Transcript" : "Upload Transcript"}
                </button>
              </div>

              <div className="flex flex-col justify-between rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                <div>
                  <h2 className="text-sm font-semibold text-emoryBlue">
                    Preferences
                  </h2>
                  <p className="mt-1 text-xs text-zinc-600">
                    Set your major, workload, and time constraints.
                  </p>
                  {hasPreferences && (
                    <p className="mt-2 text-xs text-green-600">
                      ✓ Preferences saved
                    </p>
                  )}
                </div>
                <button
                  onClick={() => navigate("/preferences")}
                  className="mt-3 rounded-xl bg-emoryBlue px-3 py-1.5 text-xs font-semibold text-white hover:bg-emoryBlue/90"
                >
                  {hasPreferences ? "Update Preferences" : "Set Preferences"}
                </button>
              </div>

              <div className="flex flex-col justify-between rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                <div>
                  <h2 className="text-sm font-semibold text-emoryBlue">
                    Schedule Builder
                  </h2>
                  <p className="mt-1 text-xs text-zinc-600">
                    Generate AI-powered schedules.
                  </p>
                  <p className="mt-2 text-[11px] text-zinc-500">
                    Choose your recommendation engine (FibHeap or ML) inside Schedule Builder before generating.
                  </p>
                  {(!hasTranscript || !hasPreferences) && (
                    <p className="mt-2 text-xs text-amber-600">
                      ⚠{" "}
                      {!hasTranscript && !hasPreferences
                        ? "Upload transcript & set preferences first"
                        : !hasTranscript
                        ? "Upload transcript first"
                        : "Set preferences first"}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => navigate("/schedule-builder")}
                  disabled={!hasTranscript || !hasPreferences}
                  className={`mt-3 rounded-xl px-3 py-1.5 text-xs font-semibold transition-colors ${
                    hasTranscript && hasPreferences
                      ? "bg-Gold text-emoryBlue hover:bg-Gold/90"
                      : "bg-zinc-200 text-zinc-500 cursor-not-allowed"
                  }`}
                >
                  Build Schedule
                </button>
              </div>
            </section>

            {/* Data Display Section */}
            <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Courses Card */}
              <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-emoryBlue">
                    {hasRealCourses
                      ? "Your Completed Courses"
                      : "Example Courses"}
                  </h2>
                  {!hasRealCourses && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                      Example
                    </span>
                  )}
                </div>
                {!hasRealCourses && (
                  <p className="mb-3 text-xs text-zinc-500">
                    Upload your transcript to see your actual courses here.
                  </p>
                )}
                <div className="flex flex-wrap gap-2 text-sm max-h-64 overflow-y-auto">
                  {displayCourses.map((code, i) => (
                    <span
                      key={`${code}-${i}`}
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${
                        hasRealCourses
                          ? "border-zinc-200 bg-zinc-50 text-emoryBlue hover:bg-emoryBlue/5"
                          : "border-zinc-200 bg-zinc-100 text-zinc-500"
                      }`}
                    >
                      {code}
                    </span>
                  ))}
                </div>
                {hasRealCourses && (
                  <p className="mt-3 text-xs text-zinc-500">
                    {userCourses.length} courses from your transcript
                  </p>
                )}
              </div>

              {/* Schedule Card */}
              <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-emoryBlue">
                    {hasRealSchedule
                      ? "Your Saved Schedule"
                      : "Example Schedule"}
                  </h2>
                  <div className="flex items-center gap-2">
                    {!hasRealSchedule && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                        Example
                      </span>
                    )}
                    {hasRealSchedule && savedSchedules.length > 1 && (
                      <div className="relative">
                        <button
                          onClick={() =>
                            setScheduleSelectorOpen((open) => !open)
                          }
                          className="flex items-center gap-1 rounded-full border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-[11px] text-zinc-600 hover:bg-zinc-100"
                        >
                          <span>
                            Schedule {selectedScheduleIdx + 1} of{" "}
                            {savedSchedules.length}
                          </span>
                          <span className="text-[10px]">
                            {scheduleSelectorOpen ? "▲" : "▼"}
                          </span>
                        </button>
                        {scheduleSelectorOpen && (
                          <div className="absolute right-0 z-10 mt-1 w-56 rounded-lg border border-zinc-200 bg-white shadow-lg">
                            {savedSchedules.map((sched: any, idx: number) => {
                              const totalCredits =
                                typeof sched.total_credits === "number"
                                  ? sched.total_credits
                                  : Array.isArray(sched.courses)
                                  ? sched.courses.reduce(
                                      (sum: number, c: any) =>
                                        sum +
                                        (parseFloat(String(c.credits)) || 3),
                                      0
                                    )
                                  : 0;
                              return (
                                <button
                                  key={idx}
                                  onClick={() => {
                                    setSelectedScheduleIdx(idx);
                                    setScheduleSelectorOpen(false);
                                  }}
                                  className={`flex w-full items-center justify-between px-3 py-2 text-xs hover:bg-zinc-50 ${
                                    idx === selectedScheduleIdx
                                      ? "bg-emoryBlue/5 text-emoryBlue"
                                      : "text-zinc-700"
                                  }`}
                                >
                                  <span className="font-medium">
                                    Schedule {idx + 1}
                                  </span>
                                  <span className="text-[10px] text-zinc-500">
                                    {totalCredits} cr
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                {!hasRealSchedule && (
                  <p className="mb-3 text-xs text-zinc-500">
                    Build and save a schedule to see it here.
                  </p>
                )}
                <SchedulePreview
                  meetings={displaySchedule}
                  isExample={!hasRealSchedule}
                />
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
