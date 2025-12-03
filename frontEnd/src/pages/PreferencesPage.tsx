import React, { useState } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";

import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";

import { CSS } from "@dnd-kit/utilities";

import applogo from "../assets/dooleyHelpzAppLogo.png";
import mascot from "../assets/EHMascot.png";
import { useNavigate } from "react-router-dom";

/* ------------------------ Helper Types ------------------------- */
const DEGREE_TYPES = ["BS", "BA"] as const;
type DegreeType = (typeof DEGREE_TYPES)[number];

const YEARS = ["Freshman", "Sophomore", "Junior", "Senior"] as const;
type Year = (typeof YEARS)[number];

// Interests – no Robotics
const INTERESTS = ["AI/ML", "Software Engineering", "Data Science"] as const;
type Interests = (typeof INTERESTS)[number];

const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
] as const;
type Days = (typeof DAYS)[number];

const PRIORITY_KEYS = [
  "PROFESSOR_RATING",
  "TIME_PREFERENCE",
  "MAJOR_REQUIREMENTS",
  "GER_REQUIREMENTS",
  "INTERESTS",
] as const;
type PriorityKey = (typeof PRIORITY_KEYS)[number];

type TimeBlock = { day: Days; start: string; end: string };

type PreferencesPayload = {
  degreeType: DegreeType | "";
  year: Year | "";
  expectedGraduation: { term: string; year: string };
  preferredCredits: number | "";
  interests: Interests[];
  timeUnavailable: TimeBlock[];
  priorityOrder: PriorityKey[];
  earliestClass: string; // "07:00"
  latestClass: string; // "20:00"
};

/* ------------- Time slider helpers (7:00 → 20:00) ------------- */
/**
 * We represent time as an index:
 * 0 => 07:00
 * 1 => 07:15
 * ...
 * 52 => 20:00
 */
const EARLIEST_HOUR = 7; // 7:00
const LATEST_HOUR = 20; // 20:00 (8 PM)
const MINUTES_STEP = 15;

const TOTAL_STEPS =
  ((LATEST_HOUR - EARLIEST_HOUR) * 60) / MINUTES_STEP; // 13h * 60 / 15 = 52

// Normalized 0..52
const TIME_INDICES = Array.from({ length: TOTAL_STEPS + 1 }, (_, i) => i);

function indexToMinutes(idx: number): number {
  return idx * MINUTES_STEP;
}

function indexTo24hString(idx: number): string {
  const minutesFromStart = indexToMinutes(idx);
  const totalMinutes = EARLIEST_HOUR * 60 + minutesFromStart;
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  const hh = h.toString().padStart(2, "0");
  const mm = m.toString().padStart(2, "0");
  return `${hh}:${mm}`;
}

function formatLabel(idx: number): string {
  const minutesFromStart = indexToMinutes(idx);
  const totalMinutes = EARLIEST_HOUR * 60 + minutesFromStart;
  let h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  const ampm = h >= 12 ? "PM" : "AM";
  if (h === 0) h = 12;
  else if (h > 12) h -= 12;
  const mm = m.toString().padStart(2, "0");
  return `${h}:${mm} ${ampm}`;
}

/* ------------------------ Sortable Item ------------------------ */

function SortableItem({ id }: { id: string }) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const label = id
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/(^| )\w/g, (s) => s.toUpperCase());

  return (
    <li
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="flex justify-between items-center bg-white border border-zinc-200 rounded-xl px-3 py-2 shadow-sm cursor-grab hover:bg-paleGold/20"
    >
      <span className="text-sm text-emoryBlue">{label}</span>
      <span className="text-xs text-zinc-400">(drag)</span>
    </li>
  );
}

/* --------------------------- Page ------------------------------ */

export default function PreferencesPage() {
  const navigate = useNavigate();

  /* -------------------------- State ------------------------------ */
  const [degreeType, setDegreeType] = useState<DegreeType | "">("");
  const [year, setYear] = useState<Year | "">("");

  const [gradTerm, setGradTerm] = useState<"Spring" | "Fall" | "">("");
  const [gradYear, setGradYear] = useState<string>("");

  const [preferredCredits, setPreferredCredits] = useState<string>("");

  const [interestList, setInterestList] = useState<Interests[]>([]);

  const [tempDay, setTempDay] = useState<Days>("Monday");
  const [tempStart, setTempStart] = useState<string>("");
  const [tempEnd, setTempEnd] = useState<string>("");
  const [unavailable, setUnavailable] = useState<TimeBlock[]>([]);

  const [priorityOrder, setPriorityOrder] =
    useState<PriorityKey[]>([...PRIORITY_KEYS]);

  // Track unsaved changes
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Slider indices
  const [earliestIndex, setEarliestIndex] = useState<number>(0); // 7:00 AM
  const [latestIndex, setLatestIndex] = useState<number>(
    TIME_INDICES[TIME_INDICES.length - 1] // 20:00
  );

  /* ----------------------- Utility Functions --------------------- */

  function toggleInterest(i: Interests) {
    if (interestList.includes(i)) {
      setInterestList(interestList.filter((x) => x !== i));
    } else {
      setInterestList([...interestList, i]);
    }
    setHasUnsavedChanges(true);
  }

  function addBlock() {
    if (!tempStart || !tempEnd) return;
    if (tempStart >= tempEnd) return;

    setUnavailable([
      ...unavailable,
      {
        day: tempDay,
        start: tempStart,
        end: tempEnd,
      },
    ]);

    setTempStart("");
    setTempEnd("");
    setHasUnsavedChanges(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const n = preferredCredits === "" ? NaN : Number(preferredCredits);
    const min = year === "Senior" ? 1 : 12;

    if (!degreeType) return alert("Please select a degree type.");
    if (!year) return alert("Please select your year.");
    if (!gradTerm || !gradYear)
      return alert("Please set your expected graduation term and year.");
    if (isNaN(n) || n < min || n > 22)
      return alert(`Preferred credits must be between ${min} and 22.`);

    const payload: PreferencesPayload = {
      degreeType,
      year,
      expectedGraduation: { term: gradTerm, year: gradYear },
      preferredCredits: n,
      interests: interestList,
      timeUnavailable: unavailable,
      priorityOrder,
      earliestClass: indexTo24hString(earliestIndex),
      latestClass: indexTo24hString(latestIndex),
    };

    console.log("SUBMIT", payload);

    fetch("http://localhost:5001/api/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    setHasUnsavedChanges(false);
    alert("Preferences saved!");
  }

  /* --------------------------- Drag & Drop ------------------------- */

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = priorityOrder.indexOf(active.id as PriorityKey);
    const newIndex = priorityOrder.indexOf(over.id as PriorityKey);
    if (oldIndex === -1 || newIndex === -1) return;

    setPriorityOrder(arrayMove(priorityOrder, oldIndex, newIndex));
    setHasUnsavedChanges(true);
  }

  /* ----------------------------- JSX ------------------------------ */

  return (
    <div className="min-h-screen bg-white text-zinc-900">
      {/* Header */}
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

          {/* Dashboard button with unsaved-changes warning */}
          <button
            type="button"
            onClick={() => {
              if (hasUnsavedChanges) {
                const confirmed = window.confirm(
                  "Preferences have not been saved, would you still like to go back to Dashboard?"
                );
                if (!confirmed) return;
              }
              navigate("/dashboard");
            }}
            className="rounded-xl bg-emoryBlue px-3 py-1.5 text-xs font-semibold text-white hover:bg-emoryBlue/90"
          >
            Dashboard
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-6xl px-4 py-8">
        {/* Intro / Mascot */}
        <section className="mb-8 flex flex-col gap-4 rounded-2xl border border-zinc-200 bg-gradient-to-tr from-emoryBlue/5 via-white to-paleGold/20 p-6 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-emoryBlue md:text-3xl">
              Update Your Preferences
            </h1>
            <p className="mt-2 text-sm text-zinc-600 max-w-xl">
              These settings help DooleyHelpz recommend courses and build
              schedules that match your degree, workload, and daily life.
            </p>
          </div>
          <div className="flex justify-center md:justify-end">
            <img
              src={mascot}
              alt="DooleyHelpz Mascot"
              className="h-28 w-auto object-contain drop-shadow-sm"
            />
          </div>
        </section>

        {/* Form Card */}
        <form
          onSubmit={handleSubmit}
          className="space-y-8 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm md:p-8"
        >
          {/* Row 1: Degree + Year */}
          <section className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="font-semibold text-emoryBlue text-sm">
                Degree Type
              </label>
              <select
                value={degreeType}
                onChange={(e) => {
                  setDegreeType(e.target.value as DegreeType | "");
                  setHasUnsavedChanges(true);
                }}
                className="mt-1 w-full rounded-xl border border-zinc-300 p-2 text-sm focus:ring-2 focus:ring-emoryBlue"
              >
                <option value="">Select…</option>
                {DEGREE_TYPES.map((d) => (
                  <option key={d} value={d}>
                    {d === "BS" ? "Bachelor of Science" : "Bachelor of Arts"}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-semibold text-emoryBlue text-sm">
                Year
              </label>
              <select
                value={year}
                onChange={(e) => {
                  setYear(e.target.value as Year | "");
                  setHasUnsavedChanges(true);
                }}
                className="mt-1 w-full rounded-xl border border-zinc-300 p-2 text-sm focus:ring-2 focus:ring-emoryBlue"
              >
                <option value="">Select…</option>
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
          </section>

          {/* Row 2: Graduation + Credits */}
          <section className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="font-semibold text-emoryBlue text-sm">
                Expected Graduation
              </label>
              <div className="mt-2 flex gap-3">
                <select
                  value={gradTerm}
                  onChange={(e) => {
                    setGradTerm(e.target.value as "Spring" | "Fall" | "");
                    setHasUnsavedChanges(true);
                  }}
                  className="rounded-xl border border-zinc-300 p-2 text-sm focus:ring-2 focus:ring-emoryBlue"
                >
                  <option value="">Term…</option>
                  <option value="Spring">Spring</option>
                  <option value="Fall">Fall</option>
                </select>

                <input
                  type="number"
                  value={gradYear}
                  onChange={(e) => {
                    setGradYear(e.target.value);
                    setHasUnsavedChanges(true);
                  }}
                  placeholder="YYYY"
                  min="2025"
                  max="2035"
                  className="w-24 rounded-xl border border-zinc-300 p-2 text-sm focus:ring-2 focus:ring-emoryBlue"
                />
              </div>
            </div>

            <div>
              <label className="font-semibold text-emoryBlue text-sm">
                Preferred Credits
              </label>
              <input
                type="number"
                value={preferredCredits}
                onChange={(e) => {
                  setPreferredCredits(e.target.value);
                  setHasUnsavedChanges(true);
                }}
                placeholder={year === "Senior" ? "1–22" : "12–22"}
                min={year === "Senior" ? 1 : 12}
                max={22}
                step={1}
                className="mt-1 w-full rounded-xl border border-zinc-300 p-2 text-sm focus:ring-2 focus:ring-emoryBlue"
              />
              <p className="mt-1 text-xs text-zinc-500">
                Seniors can go lighter; everyone else usually needs at least 12
                credits.
              </p>
            </div>
          </section>

          {/* Interests */}
          <section>
            <label className="font-semibold text-emoryBlue text-sm">
              Interests
            </label>
            <p className="mt-1 text-xs text-zinc-500">
              We&apos;ll prefer classes that align with these topics when
              possible.
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {INTERESTS.map((x) => {
                const active = interestList.includes(x);
                return (
                  <button
                    key={x}
                    type="button"
                    onClick={() => toggleInterest(x)}
                    className={
                      "rounded-full border px-3 py-1 text-xs font-medium transition-colors " +
                      (active
                        ? "bg-emoryBlue text-white border-emoryBlue"
                        : "bg-white text-emoryBlue border-emoryBlue/40 hover:bg-paleGold/20")
                    }
                  >
                    {x}
                  </button>
                );
              })}
            </div>
          </section>

          {/* Earliest / Latest Class */}
          <section className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="font-semibold text-emoryBlue text-sm">
                Earliest Class You&apos;re Willing To Take
              </label>
              <p className="mt-1 text-xs text-zinc-500">
                We&apos;ll try not to schedule anything before this time.
              </p>
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span>7:00 AM</span>
                  <span>8:00 PM</span>
                </div>
                <input
                  type="range"
                  min={TIME_INDICES[0]}
                  max={TIME_INDICES[TIME_INDICES.length - 1]}
                  step={1}
                  value={earliestIndex}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    setEarliestIndex(next);
                    if (next > latestIndex) {
                      setLatestIndex(next);
                    }
                    setHasUnsavedChanges(true);
                  }}
                  className="mt-2 w-full"
                />
                <p className="mt-1 text-xs font-medium text-emoryBlue">
                  {formatLabel(earliestIndex)}
                </p>
              </div>
            </div>

            <div>
              <label className="font-semibold text-emoryBlue text-sm">
                Latest Class You&apos;re Willing To Take
              </label>
              <p className="mt-1 text-xs text-zinc-500">
                We&apos;ll avoid classes that end after this time.
              </p>
              <div className="mt-2">
                <div className="flex items-center justify-between text-xs text-zinc-500">
                  <span>7:00 AM</span>
                  <span>8:00 PM</span>
                </div>
                <input
                  type="range"
                  min={TIME_INDICES[0]}
                  max={TIME_INDICES[TIME_INDICES.length - 1]}
                  step={1}
                  value={latestIndex}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    setLatestIndex(next);
                    if (next < earliestIndex) {
                      setEarliestIndex(next);
                    }
                    setHasUnsavedChanges(true);
                  }}
                  className="mt-2 w-full"
                />
                <p className="mt-1 text-xs font-medium text-emoryBlue">
                  {formatLabel(latestIndex)}
                </p>
              </div>
            </div>
          </section>

          {/* Time Unavailable */}
          <section>
            <label className="font-semibold text-emoryBlue text-sm">
              Time Unavailable (Work, Clubs, etc.)
            </label>
            <p className="mt-1 text-xs text-zinc-500">
              Add blocks of time where classes should not be scheduled.
            </p>

            <div className="mt-2 flex flex-wrap items-center gap-2">
              <select
                value={tempDay}
                onChange={(e) =>
                  setTempDay(e.target.value as Days)
                }
                className="rounded-xl border border-zinc-300 p-2 text-xs"
              >
                {DAYS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>

              <input
                type="time"
                step={900}
                value={tempStart}
                onChange={(e) => setTempStart(e.target.value)}
                className="rounded-xl border border-zinc-300 p-2 text-xs"
              />

              <input
                type="time"
                step={900}
                value={tempEnd}
                onChange={(e) => setTempEnd(e.target.value)}
                className="rounded-xl border border-zinc-300 p-2 text-xs"
              />

              <button
                type="button"
                onClick={addBlock}
                className="rounded-xl bg-emoryBlue px-3 py-1 text-xs font-semibold text-white hover:bg-emoryBlue/90"
              >
                Add
              </button>
            </div>

            <ul className="mt-2 space-y-1 text-sm text-zinc-700">
              {unavailable.map((u, i) => (
                <li key={`${u.day}-${u.start}-${u.end}-${i}`}>
                  {u.day} {u.start}–{u.end}{" "}
                  <button
                    type="button"
                    className="text-rose-600 text-xs hover:underline"
                    onClick={() => {
                      setUnavailable(
                        unavailable.filter((_, idx) => idx !== i)
                      );
                      setHasUnsavedChanges(true);
                    }}
                  >
                    remove
                  </button>
                </li>
              ))}
              {unavailable.length === 0 && (
                <li className="text-xs text-zinc-500">
                  No blocked times added yet.
                </li>
              )}
            </ul>
          </section>

          {/* Priority Order – Drag & Drop */}
          <section>
            <label className="font-semibold text-emoryBlue text-sm">
              Order of Importance (drag to reorder)
            </label>
            <p className="mt-1 text-xs text-zinc-500">
              We&apos;ll use this order when choosing between classes.
            </p>

            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={onDragEnd}
            >
              <SortableContext
                items={priorityOrder}
                strategy={verticalListSortingStrategy}
              >
                <ol className="mt-2 space-y-2">
                  {priorityOrder.map((key) => (
                    <SortableItem key={key} id={key} />
                  ))}
                </ol>
              </SortableContext>
            </DndContext>
          </section>

          {/* Submit */}
          <button
            type="submit"
            className="mt-2 w-full rounded-xl bg-emoryBlue py-2 text-sm font-semibold text-white hover:bg-emoryBlue/90"
          >
            Save Preferences
          </button>
        </form>
      </main>
    </div>
  );
}