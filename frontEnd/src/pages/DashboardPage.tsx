import { useNavigate } from "react-router-dom";
import { auth } from "../firebase";

import applogo from "../assets/dooleyHelpzAppLogo.png";
import mascot from "../assets/EHMascot.png";

/** For now, just course codes like "CS 253" */
type RecommendedClass = string;

type ScheduleMeeting = {
  day: "Mon" | "Tue" | "Wed" | "Thu" | "Fri";
  course: string;   // e.g. "CS 253"
  section: string;  // e.g. "Sec 1"
  start: string;    // "08:00" (24h)
  end: string;      // "09:15"
};

/** Example data placeholders – replace with backend later */
const exampleRecommended: RecommendedClass[] = [
  "CS 253",
  "CS 224",
  "MATH 221",
  "QTM 100",
  "CHEM 150",
  "CS 334",
  "CS 326",
  "MATH 250",
  "CS 255",
  "CS 370",
];

// Example schedule, Mon–Fri, 08:00–19:00 window
const exampleSchedule: ScheduleMeeting[] = [
  { day: "Mon", course: "CS 253", section: "Sec 1", start: "09:00", end: "10:15" },
  { day: "Mon", course: "MATH 221", section: "Sec 2", start: "13:00", end: "14:15" },
  { day: "Tue", course: "CS 224", section: "Sec 1", start: "11:30", end: "12:45" },
  { day: "Wed", course: "CS 253", section: "Sec 1", start: "09:00", end: "10:15" },
  { day: "Wed", course: "QTM 100", section: "Sec 3", start: "15:00", end: "16:15" },
  { day: "Thu", course: "CS 224", section: "Sec 1", start: "11:30", end: "12:45" },
  { day: "Fri", course: "CHEM 150", section: "Lab A", start: "10:00", end: "12:00" },
];

const DAYS: ScheduleMeeting["day"][] = ["Mon", "Tue", "Wed", "Thu", "Fri"];
const START_HOUR = 8;
const END_HOUR = 19;
const TOTAL_MINUTES = (END_HOUR - START_HOUR) * 60;

function minutesFromStart(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return (h - START_HOUR) * 60 + m;
}

function SchedulePreview({
  meetings,
  isExample,
}: {
  meetings: ScheduleMeeting[];
  isExample: boolean;
}) {
  // group by day
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
        {isExample && (
          <p className="text-xs text-zinc-500">
            Showing an example schedule until you build one.
          </p>
        )}
      </div>

      <div className="grid grid-cols-[3rem_repeat(5,1fr)] gap-2 text-xs">
        {/* Time labels (left) */}
        <div className="relative h-[440px]">
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

        {/* Day columns */}
        {DAYS.map((day) => (
          <div key={day} className="relative h-[440px] border-l border-zinc-100">
            <div className="mb-1 text-center text-[11px] font-semibold text-emoryBlue">
              {day}
            </div>
            {/* horizontal grid lines */}
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

            {/* course blocks */}
            {byDay[day].map((m, i) => {
              const startMin = minutesFromStart(m.start);
              const endMin = minutesFromStart(m.end);
              const top = (startMin / TOTAL_MINUTES) * 100;
              const height = ((endMin - startMin) / TOTAL_MINUTES) * 100;

              return (
                <div
                  key={`${m.course}-${m.section}-${i}`}
                  className="absolute left-1 right-1 overflow-hidden rounded-lg border border-emoryBlue/30 bg-emoryBlue/10 px-1.5 py-1 text-[10px] shadow-sm"
                  style={{ top: `${top}%`, height: `${height}%` }}
                >
                  <div className="font-semibold text-emoryBlue leading-tight">
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

  // Replace these with real backend data later
  const recommendedFromBackend: RecommendedClass[] = []
  const latestScheduleFromBackend: ScheduleMeeting[] = [] 

  const recommended =
    recommendedFromBackend && recommendedFromBackend.length
      ? recommendedFromBackend
      : exampleRecommended;
  const isExampleRecommendations =
    !recommendedFromBackend || !recommendedFromBackend.length;

  const schedule =
    latestScheduleFromBackend && latestScheduleFromBackend.length
      ? latestScheduleFromBackend
      : exampleSchedule;
  const isExampleSchedule =
    !latestScheduleFromBackend || !latestScheduleFromBackend.length;

  const handleLogout = async () => {
    await auth.signOut();
    navigate("/"); // go back to HomePage.tsx
  };

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      {/* Header (not sticky) */}
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
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
          </div>

          <div className="flex items-center gap-3">
            {user && (
              <span className="hidden text-xs text-zinc-600 sm:inline">
                {user.email}
              </span>
            )}
            <button
              onClick={handleLogout}
              className="rounded-xl bg-emoryBlue px-3 py-1.5 text-xs font-semibold text-white hover:bg-emoryBlue/90"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-6xl px-4 pb-12 pt-6">
        {/* Welcome / intro */}
        <section className="mb-8 grid items-center gap-6 rounded-3xl border border-zinc-200 bg-linear-to-tr from-emoryBlue/5 via-white to-paleGold/20 p-6 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <div>
            <h1 className="text-2xl font-bold text-emoryBlue md:text-3xl">
              Welcome, {user?.email || "Guest"}!
            </h1>
            <p className="mt-2 text-sm text-zinc-600">
              This dashboard pulls together your transcript, preferences, and
              schedules so you can plan calmer semesters. Start by uploading a
              transcript or updating your preferences.
            </p>
          </div>
          <div className="flex justify-center md:justify-end">
            <img
              src={mascot}
              alt="DooleyHelpz Mascot"
              className="h-32 w-auto object-contain drop-shadow-sm"
            />
          </div>
        </section>

        {/* Three main action boxes */}
        <section className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {/* Update Transcript */}
          <div className="flex flex-col justify-between rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div>
              <h2 className="text-sm font-semibold text-emoryBlue">
                Update Transcript
              </h2>
              <p className="mt-1 text-xs text-zinc-600">
                Upload your latest Emory transcript PDF so we can track classes taken.
              </p>
            </div>
            <button
              onClick={() => navigate("/droptranscript")}
              className="mt-3 rounded-xl bg-emoryBlue px-3 py-1.5 text-xs font-semibold text-white hover:bg-emoryBlue/90"
            >
              Go to Transcript Upload
            </button>
          </div>

          {/* Preferences */}
          <div className="flex flex-col justify-between rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div>
              <h2 className="text-sm font-semibold text-emoryBlue">
                Preferences
              </h2>
              <p className="mt-1 text-xs text-zinc-600">
                Set your major, workload, and time constraints for smarter suggestions.
              </p>
            </div>
            <button
              onClick={() => navigate("/preferences")}
              className="mt-3 rounded-xl bg-emoryBlue px-3 py-1.5 text-xs font-semibold text-white hover:bg-emoryBlue/90"
            >
              Go to Preferences
            </button>
          </div>

          {/* Schedule Builder - NOW WORKING */}
          <div className="flex flex-col justify-between rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div>
              <h2 className="text-sm font-semibold text-emoryBlue">
                Schedule Builder
              </h2>
              <p className="mt-1 text-xs text-zinc-600">
                Generate AI-powered schedules and export to your calendar.
              </p>
            </div>
            <button
              onClick={() => navigate("/schedule-builder")}
              className="mt-3 rounded-xl bg-Gold px-3 py-1.5 text-xs font-semibold text-emoryBlue hover:bg-Gold/90"
            >
              Build Schedule
            </button>
          </div>
        </section>

        {/* Bottom two-column section */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Left: Eligible / Recommended classes */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-emoryBlue">
                Eligible & Recommended Classes
              </h2>
              {isExampleRecommendations && (
                <span className="text-xs text-zinc-500">
                  Example shown — upload a transcript to personalize.
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-2 text-sm">
              {recommended.map((code, i) => (
                <span
                  key={`${code}-${i}`}
                  className="rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1 text-xs font-medium text-emoryBlue hover:bg-paleGold/20"
                >
                  {code}
                </span>
              ))}
            </div>
          </div>

          {/* Right: Schedule preview */}
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-emoryBlue">
                Most Recently Built Schedule
              </h2>
              {isExampleSchedule && (
                <span className="text-xs text-zinc-500">
                  Example schedule — you haven&apos;t built one yet.
                </span>
              )}
            </div>
            <SchedulePreview meetings={schedule} isExample={isExampleSchedule} />
          </div>
        </section>
      </main>
    </div>
  );
}