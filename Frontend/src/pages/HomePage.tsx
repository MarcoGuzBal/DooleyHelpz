import React from "react";
import { motion } from "framer-motion";
import { CalendarDays, GraduationCap, Sparkles, Wand2, Clock, CheckCircle2 } from "lucide-react";

// Simple mock schedule data to demonstrate layout only
const mockWeek = [
  { day: "Mon", blocks: [{ time: "9:00–10:15", course: "CS 201", color: "bg-indigo-100 text-indigo-800" }, { time: "1:30–2:45", course: "BIO 212", color: "bg-emerald-100 text-emerald-800" }] },
  { day: "Tue", blocks: [{ time: "11:00–12:15", course: "MATH 231", color: "bg-rose-100 text-rose-800" }] },
  { day: "Wed", blocks: [{ time: "9:00–10:15", course: "CS 201", color: "bg-indigo-100 text-indigo-800" }, { time: "3:00–4:15", course: "HUM 101", color: "bg-amber-100 text-amber-800" }] },
  { day: "Thu", blocks: [{ time: "11:00–12:15", course: "MATH 231", color: "bg-rose-100 text-rose-800" }, { time: "2:00–3:15", course: "CHEM 110", color: "bg-sky-100 text-sky-800" }] },
  { day: "Fri", blocks: [{ time: "10:00–11:50", course: "LAB – CHEM", color: "bg-sky-100 text-sky-800" }] },
];

const Feature = ({ icon: Icon, title, desc }: { icon: any; title: string; desc: string }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-50px" }}
    transition={{ duration: 0.4 }}
    className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm hover:shadow-md"
  >
    <div className="flex items-center gap-3">
      <div className="rounded-xl bg-zinc-100 p-2">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-base font-semibold">{title}</h3>
    </div>
    <p className="mt-3 text-sm text-zinc-600">{desc}</p>
  </motion.div>
);

const Pill = ({ children }: { children: React.ReactNode }) => (
  <span className="inline-flex items-center gap-1 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs text-zinc-700 shadow-sm">
    <CheckCircle2 className="h-3.5 w-3.5" />
    {children}
  </span>
);

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white via-zinc-50 to-white">
      {/* Nav */}
      <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/70 backdrop-blur">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <GraduationCap className="h-4 w-4" />
            </div>
            <span className="text-lg font-semibold">DooleyHelpz</span>
          </div>
          <div className="hidden items-center gap-6 text-sm text-zinc-700 md:flex">
            <a href="#features" className="hover:text-black">Features</a>
            <a href="#preview" className="hover:text-black">Preview</a>
            <a href="#faq" className="hover:text-black">FAQ</a>
            <a href="#cta" className="rounded-xl bg-black px-3 py-1.5 font-medium text-white hover:bg-zinc-800">Get Started</a>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-4 pb-10 pt-12 md:pt-16">
        <div className="grid items-center gap-10 md:grid-cols-2">
          <div>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <div className="mb-4 flex flex-wrap gap-2">
                <Pill>Smart, conflict‑free schedules</Pill>
                <Pill>Personalized course recs</Pill>
                <Pill>Degree progress aware</Pill>
              </div>
              <h1 className="text-3xl font-bold leading-tight md:text-5xl">
                Plan every semester <span className="text-indigo-600">without the chaos</span>
              </h1>
              <p className="mt-4 max-w-prose text-zinc-600">
                Dooley Devs helps students pick the right courses and auto‑build a timetable around classes, jobs, and life. Get
                recommendations that fit prerequisites, preferences, and degree requirements—then generate a schedule that just works.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <a
                  href="#cta"
                  className="group inline-flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500"
                >
                  <Sparkles className="mr-2 h-4 w-4" /> Start planning
                </a>
                <a
                  href="#preview"
                  className="inline-flex items-center justify-center rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-800 hover:bg-zinc-50"
                >
                  <Wand2 className="mr-2 h-4 w-4" /> See a sample schedule
                </a>
              </div>
              <p className="mt-3 text-xs text-zinc-500">No credit card. No spam. Just better semesters.</p>
            </motion.div>
          </div>

          {/* Right hero card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.05 }}
            className="rounded-3xl border border-zinc-200 bg-white p-5 shadow-lg"
          >
            <div className="flex items-center gap-2 border-b border-zinc-200 pb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-600 text-white">
                <CalendarDays className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-semibold">Auto‑Schedule Builder</h3>
                <p className="text-xs text-zinc-500">Blocks work, clubs, and study time around classes.</p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-5 gap-3 text-xs">
              {mockWeek.map((d) => (
                <div key={d.day} className="">
                  <div className="mb-2 text-center font-medium text-zinc-700">{d.day}</div>
                  <div className="space-y-2">
                    {d.blocks.map((b, i) => (
                      <div key={i} className={`rounded-xl ${b.color} px-2 py-2 shadow-sm`}>
                        <div className="font-semibold">{b.course}</div>
                        <div className="text-[11px] opacity-80">{b.time}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="mx-auto max-w-6xl px-4 py-12">
        <div className="mb-8">
          <h2 className="text-2xl font-semibold md:text-3xl">What DooleyHelpz does for you</h2>
          <p className="mt-2 max-w-prose text-zinc-600">Designed for students who juggle classes, work, clubs, research, and life.</p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <Feature icon={Sparkles} title="Smart recommendations" desc="Ranked course suggestions that respect prerequisites and your degree map." />
          <Feature icon={Clock} title="Conflict‑free builder" desc="Instant schedules that avoid class overlaps and honor your busy blocks." />
          <Feature icon={GraduationCap} title="Progress aware" desc="Keeps you on track for graduation and flags requirement gaps early." />
          <Feature icon={Wand2} title="What‑if scenarios" desc="Try alternative loads, sections, or instructors in one click." />
        </div>
      </section>

      {/* Preview */}
      <section id="preview" className="mx-auto max-w-6xl px-4 pb-12">
        <div className="rounded-3xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold">Recommended this term</h3>
              <p className="text-sm text-zinc-600">A tiny preview of what recommendations could look like.</p>
            </div>
            <div className="flex gap-2">
              <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs">Preference: mornings</span>
              <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs">Max credits: 16</span>
            </div>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[{ code: "CS 201", name: "Data Structures", meta: "MW 9:00–10:15 • Prof. Lee" }, { code: "MATH 231", name: "Discrete Math", meta: "TR 11:00–12:15 • Prof. Shah" }, { code: "BIO 212", name: "Molecular Biology", meta: "MW 1:30–2:45 • Prof. Chen" }].map((c) => (
              <motion.div key={c.code} whileHover={{ y: -2 }} className="rounded-2xl border border-zinc-200 p-4">
                <div className="flex items-center gap-2">
                  <div className="rounded-lg bg-zinc-100 px-2 py-1 text-xs font-semibold">{c.code}</div>
                  <div className="text-sm font-medium">{c.name}</div>
                </div>
                <p className="mt-2 text-xs text-zinc-600">{c.meta}</p>
                <div className="mt-3 flex gap-2 text-[11px] text-zinc-600">
                  <span className="rounded-full bg-emerald-50 px-2 py-1">fits prereqs</span>
                  <span className="rounded-full bg-indigo-50 px-2 py-1">on track</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section id="cta" className="mx-auto max-w-6xl px-4 pb-16">
        <div className="rounded-3xl border border-zinc-200 bg-gradient-to-tr from-indigo-50 via-white to-emerald-50 p-8 text-center shadow-sm">
          <h3 className="text-2xl font-semibold">Ready to plan a calmer semester?</h3>
          <p className="mx-auto mt-2 max-w-2xl text-zinc-600">
            Create your profile, set preferences, and let Dooley Devs recommend the best‑fit courses. Then generate a conflict‑free schedule around your life.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <a className="rounded-xl bg-black px-4 py-2.5 text-sm font-semibold text-white hover:bg-zinc-800" href="#">
              Sign up free
            </a>
            <a className="rounded-xl border border-zinc-300 bg-white px-4 py-2.5 text-sm font-semibold hover:bg-zinc-50" href="#">
              Continue as guest
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-zinc-600 md:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <GraduationCap className="h-3.5 w-3.5" />
            </div>
            <span>DooleyHelpz</span>
          </div>
          <div className="flex gap-4">
            <a href="#features" className="hover:text-black">Features</a>
            <a href="#preview" className="hover:text-black">Preview</a>
            <a href="#cta" className="hover:text-black">Start</a>
          </div>
          <div className="text-xs">© {new Date().getFullYear()} DooleyHelpz</div>
        </div>
      </footer>
    </div>
  )
}
