import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  CalendarDays,
  GraduationCap,
  ClipboardList,
  FileText,
  Settings2,
  PlusCircle,
  Info,
} from "lucide-react";

import applogo from "../assets/dooleyHelpzAppLogo.png";
import mascot from "../assets/EHMascot.png";

/** ====== Types you might wire up to real data later ====== */
type ParsedCourse = {
  course: string; // "CS 171"
  name: string;
  inProgress?: boolean;
};

type ScheduleBlock = {
  day: "Mon" | "Tue" | "Wed" | "Thu" | "Fri";
  start: string; // "09:00" 24h
  end: string;   // "10:15"
  label: string; // "CS 171"
  note?: string; // "Woodruff 101"
};

type DashboardProps = {
  userName?: string;
  major?: "CS-BA" | "CS-BS" | null;
  classesTaken?: ParsedCourse[];  // parsed courses you've saved (from Transcript)
  creditsTaken?: number | null;   // optional; if missing we'll show "—"
  schedule?: ScheduleBlock[];     // latest schedule to preview
};

/** ====== Emory CS requirements (placeholder shells) ====== */
const CS_REQUIREMENTS = {
  "CS-BA": [
    { title: "Foundations", items: ["CS 170 / 171", "CS 224 / 253", "Discrete Math", "Data Structures"] },
    { title: "Systems / Theory", items: ["Algorithms", "Systems or Architecture"] },
    { title: "Electives", items: ["Upper-level CS elective 1", "Upper-level CS elective 2"] },
    { title: "Allied / Gen-Ed", items: ["Math/Stats as required by program", "Gen-Ed as applicable"] },
  ],
  "CS-BS": [
    { title: "Foundations", items: ["CS 170 / 171", "CS 224 / 253", "Discrete Math", "Data Structures"] },
    { title: "Core", items: ["Algorithms", "Systems", "Theory", "Architecture"] },
    { title: "Advanced Electives", items: ["Upper-level CS elective 1", "Upper-level CS elective 2", "Upper-level CS elective 3"] },
    { title: "Math/Science", items: ["Calc sequence", "Probability/Statistics", "Science requirements"] },
  ],
} as const;

/** Group schedule by day for preview grid */
const DAYS: ScheduleBlock["day"][] = ["Mon", "Tue", "Wed", "Thu", "Fri"];
function groupByDay(blocks: ScheduleBlock[] = []) {
  const map: Record<ScheduleBlock["day"], ScheduleBlock[]> = {
    Mon: [], Tue: [], Wed: [], Thu: [], Fri: [],
  };
  blocks.forEach((b) => map[b.day].push(b));
  for (const d of DAYS) map[d].sort((a, b) => a.start.localeCompare(b.start));
  return map;
}

/** Example schedule to display before user creates one */
const sampleSchedule: ScheduleBlock[] = [
  { day: "Mon", start: "09:00", end: "10:15", label: "CS 171", note: "Intro to CS" },
  { day: "Mon", start: "13:00", end: "14:15", label: "MATH 210", note: "Multivariable" },
  { day: "Tue", start: "11:30", end: "12:45", label: "CS 224", note: "Discrete Structures" },
  { day: "Wed", start: "09:00", end: "10:15", label: "CS 171", note: "Lecture" },
  { day: "Wed", start: "15:00", end: "16:15", label: "HUM 101", note: "Core" },
  { day: "Thu", start: "11:30", end: "12:45", label: "CS 224", note: "Lecture" },
  { day: "Fri", start: "10:00", end: "11:50", label: "CHEM 110 Lab", note: "Lab" },
];

/** A tidy schedule preview (compact grid) */
function SchedulePreview({ schedule }: { schedule?: ScheduleBlock[] }) {
  const data = (schedule && schedule.length > 0) ? schedule : sampleSchedule;
  const byDay = groupByDay(data);

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4">
      <div className="grid grid-cols-5 gap-3 text-xs">
        {DAYS.map((day) => (
          <div key={day}>
            <div className="mb-2 text-center font-medium text-emoryBlue">{day}</div>
            <div className="space-y-2">
              {byDay[day].length === 0 ? (
                <div className="rounded-xl border border-dashed border-zinc-200 px-2 py-3 text-center text-zinc-400">
                  —
                </div>
              ) : (
                byDay[day].map((b, i) => (
                  <div key={`${day}-${i}`} className="rounded-xl bg-emoryBlue/5 px-2 py-2 shadow-sm">
                    <div className="font-semibold text-emoryBlue">{b.label}</div>
                    <div className="text-[11px] text-zinc-600">
                      {b.start}–{b.end}{b.note ? ` • ${b.note}` : ""}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
      {(!schedule || schedule.length === 0) && (
        <p className="mt-3 flex items-center gap-2 text-xs text-zinc-500">
          <Info className="h-3.5 w-3.5" /> Showing an example schedule until you create one.
        </p>
      )}
    </div>
  );
}

/** Requirement chips (visual placeholders for now) */
function RequirementList({
  plan,
  taken,
}: {
  plan: typeof CS_REQUIREMENTS["CS-BA"] | typeof CS_REQUIREMENTS["CS-BS"];
  taken: ParsedCourse[];
}) {
  const hasCourse = (frag: string) =>
    taken.some((c) => c.course.toLowerCase().includes(frag.toLowerCase()));

  return (
    <div className="space-y-4">
      {plan.map((section, idx) => (
        <div key={idx} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="mb-2 flex items-center gap-2">
            <GraduationCap className="h-4 w-4 text-emoryBlue" />
            <h4 className="text-sm font-semibold text-emoryBlue">{section.title}</h4>
          </div>
          <ul className="grid gap-2 sm:grid-cols-2">
            {section.items.map((it, i) => {
              const done = hasCourse(it);
              return (
                <li
                  key={i}
                  className={`rounded-lg px-3 py-2 text-sm ${
                    done ? "bg-paleGold text-emoryBlue" : "bg-zinc-50 text-zinc-700 border border-zinc-200"
                  }`}
                  title={done ? "Looks satisfied from your course history" : "Not detected yet"}
                >
                  {it}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
      <p className="text-xs text-zinc-500">
        Note: Replace these with official Emory CS requirements when you wire real data.
      </p>
    </div>
  );
}

/** ====== MAIN DASHBOARD PAGE ====== */
export default function Dashboard({
  userName = "user",
  major = null,
  classesTaken = [],
  creditsTaken = null,
  schedule = [],
}: DashboardProps) {
  const hasHistory = classesTaken.length > 0;

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      {/* Top bar */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-Gold">
            <img src={applogo} alt="DooleyHelpz" className="h-6 w-6 object-contain" />
          </div>
          <span className="text-lg font-semibold text-emoryBlue">DooleyHelpz</span>
        </div>

        <div className="hidden gap-2 md:flex">
          <Link
            to="/profile"
            className="inline-flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-emoryBlue hover:bg-paleGold/40"
          >
            <Settings2 className="h-4 w-4" />
            Update Preferences
          </Link>
          {/* Updated: route to /transcript */}
          <Link
            to="/transcript"
            className="inline-flex items-center gap-2 rounded-xl bg-lighterBlue px-3 py-1.5 text-sm font-semibold text-white hover:bg-emoryBlue/90"
          >
            <FileText className="h-4 w-4" />
            Update Transcript
          </Link>
        </div>
      </header>

      {/* Hero / Welcome */}
      <section className="mx-auto max-w-6xl px-4">
        <div className="grid items-center gap-6 rounded-3xl border border-zinc-200 bg-gradient-to-tr from-emoryBlue/5 via-white to-paleGold/20 p-6 md:grid-cols-3">
          <div className="md:col-span-2">
            <motion.h1
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="text-2xl font-bold text-emoryBlue md:text-3xl"
            >
              Welcome {userName},
            </motion.h1>
            <p className="mt-2 text-zinc-600">
              Your hub for progress, requirements, and schedules. Update your profile or transcript anytime.
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <Link
                to="/profile"
                className="inline-flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-emoryBlue hover:bg-paleGold/40"
              >
                <Settings2 className="h-4 w-4" />
                Update your preferences
              </Link>
              {/* Updated: route to /transcript */}
              <Link
                to="/transcript"
                className="inline-flex items-center gap-2 rounded-xl bg-lighterBlue px-3 py-1.5 text-sm font-semibold text-white hover:bg-emoryBlue/90"
              >
                <FileText className="h-4 w-4" />
                Update your transcript
              </Link>
            </div>
          </div>

          <div className="flex justify-center md:justify-end">
            <img
              src={mascot}
              alt="DooleyHelpz Mascot"
              className="h-36 w-auto object-contain drop-shadow-sm"
            />
          </div>
        </div>
      </section>

      {/* KPIs row (kept simple) */}
      <section className="mx-auto grid max-w-6xl grid-cols-1 gap-4 px-4 py-6 sm:grid-cols-2 lg:grid-cols-4">
       
        <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-emoryBlue">
            <GraduationCap className="h-4 w-4" />
            <span className="text-sm font-semibold">Major</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-emoryBlue">
            {major ? (major === "CS-BA" ? "Computer Science BA" : "Computer Science BS") : "Not set"}
          </div>
          {!major && (
            <p className="mt-1 text-xs text-zinc-500">
              Add a major in your <Link to="/profile" className="text-emoryBlue underline">profile</Link>.
            </p>
          )}
        </div>

        

        <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-emoryBlue">
            <PlusCircle className="h-4 w-4" />
            <span className="text-sm font-semibold">Build schedule</span>
          </div>
          <div className="mt-2">
            <Link
              to="/schedule-builder"
              className="inline-flex items-center gap-2 rounded-xl bg-emoryBlue px-3 py-1.5 text-sm font-semibold text-white hover:bg-emoryBlue/90"
            >
              Go to Schedule Builder
            </Link>
          </div>
        </div>
      </section>

      {/* Two-column: Requirements + Schedule */}
      <section className="mx-auto grid max-w-6xl grid-cols-1 gap-6 px-4 pb-10 lg:grid-cols-2">
        {/* Major Requirements */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-emoryBlue">Major requirements</h2>
            {!major && (
              <Link to="/profile" className="text-sm font-medium text-emoryBlue hover:text-Gold">
                Add a major →
              </Link>
            )}
          </div>

          {major ? (
            <RequirementList plan={CS_REQUIREMENTS[major]} taken={classesTaken} />
          ) : (
            <div className="rounded-2xl border border-zinc-200 bg-white p-6 text-sm text-zinc-600">
              No major on file. Go to{" "}
              <Link to="/profile" className="text-emoryBlue underline">
                Update your preferences
              </Link>{" "}
              and select Computer Science BA or BS to see tailored requirements here.
            </div>
          )}
        </div>

        {/* Schedule Preview + CTA */}
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-emoryBlue">Most current schedule</h2>
            <Link
              to="/schedule-builder"
              className="inline-flex items-center gap-2 rounded-xl bg-emoryBlue px-3 py-1.5 text-sm font-semibold text-white hover:bg-emoryBlue/90"
            >
              <PlusCircle className="h-4 w-4 text-Gold" />
              Go to Schedule Builder
            </Link>
          </div>

          <SchedulePreview schedule={schedule} />
        </div>
      </section>

      {/* Classes Taken section — with Credits note inside */}
      <section className="mx-auto max-w-6xl px-4 pb-12">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-emoryBlue">Classes taken</h2>
          {/* Updated: route to /transcript */}
          <Link to="/transcript" className="text-sm font-medium text-emoryBlue hover:text-Gold">
            Update transcript →
          </Link>
        </div>

        <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
          {/* credits note inside the same card */}
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm text-zinc-600">
              Parsed from your uploaded transcript.
            </p>
            <p className="text-xs text-zinc-500">
              Credits taken: <span className="font-semibold text-emoryBlue">{creditsTaken ?? "—"}</span>
            </p>
          </div>

          {hasHistory ? (
            <div className="overflow-x-auto rounded-xl border border-zinc-100">
              <table className="min-w-full text-sm">
                <thead className="bg-zinc-100 text-zinc-700">
                  <tr>
                    <th className="px-4 py-2 text-left">Course</th>
                    <th className="px-4 py-2 text-left">Title</th>
                    <th className="px-4 py-2 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {classesTaken.map((c, i) => (
                    <tr key={i} className="border-t border-zinc-100 hover:bg-paleGold/10">
                      <td className="px-4 py-2">{c.course}</td>
                      <td className="px-4 py-2">{c.name}</td>
                      <td className="px-4 py-2">
                        {c.inProgress ? (
                          <span className="rounded bg-paleGold px-2 py-0.5 text-xs text-emoryBlue">
                            In progress
                          </span>
                        ) : (
                          <span className="text-xs text-zinc-600">Completed</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-zinc-300 bg-zinc-50 p-5 text-sm text-zinc-600">
              No Class History Given Yet — upload a transcript to populate this list.{" "}
              <Link to="/transcript" className="text-emoryBlue underline">Go to Transcript</Link>
            </div>
          )}
        </div>x
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-6 text-center text-sm text-zinc-600">
          © {new Date().getFullYear()} DooleyHelpz — Dashboard
        </div>
      </footer>
    </div>
  );
}
