import { useNavigate } from "react-router-dom";
import applogo from "../assets/dooleyHelpzAppLogo.png";
import mascot from "../assets/EHMascot.png";

export default function SustainibilityPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-susGreen text-DarkGreen">
      {/* Header */}
      <header
        className="border-b bg-susGreen"
        style={{ borderColor: "#002000" }} // DarkGreen border line
      >
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/80">
              <img
                src={applogo}
                alt="DooleyHelpz"
                className="h-6 w-6 object-contain"
              />
            </div>
            <span className="text-lg font-semibold text-DarkGreen">
              DooleyHelpz
            </span>
          </div>

          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded-full border border-white/70 bg-white/90 px-3 py-1 text-xs font-semibold text-DarkGreen shadow-sm hover:bg-susGreen/90 hover:text-white transition-colors"
          >
            Back to Homepage
          </button>
        </div>
      </header>

      {/* Main */}
      <main className="mx-auto max-w-6xl px-4 py-8">
        {/* Hero / Intro */}
        <section className="mb-8 flex flex-col gap-4 rounded-2xl border border-white/40 bg-white/80 p-6 md:flex-row md:items-center md:justify-between shadow-sm">
          <div>
            <div className="inline-flex items-center rounded-full bg-white/70 px-3 py-1 text-xs font-medium text-DarkGreen opacity-90">
              🌱 Sustainability at DooleyHelpz
            </div>
            <h1 className="mt-3 text-2xl font-bold text-DarkGreen md:text-3xl">
              A Greener Way to Plan Your Degree
            </h1>
            <p className="mt-2 text-sm text-DarkGreen opacity-90 max-w-xl">
              We care about helping you graduate <em>and</em> helping the
              planet survive your degree plan. Here&apos;s how DooleyHelpz
              stays mindful about compute, cost, and creativity.
            </p>
          </div>
          <div className="flex justify-center md:justify-end " >
            <img
              src={mascot}
              alt="DooleyHelpz Mascot"
              className="h-40 w-auto object-contain drop-shadow-sm "
            />
          </div>
        </section>

        {/* What We Do */}
        <section className="mb-8 rounded-2xl border border-white/40 bg-white p-6 shadow-sm md:p-8">
          <h2 className="text-lg font-semibold text-DarkGreen">
            What We Do To Be Sustainable
          </h2>
          <p className="mt-2 text-sm text-DarkGreen opacity-90">
            We&apos;re not single-handedly reversing climate change, but we try
            to make thoughtful choices in how we design and run DooleyHelpz:
          </p>

          <ul className="mt-4 space-y-3 text-sm text-DarkGreen opacity-90 list-disc list-inside">
            <li>
              <span className="font-semibold text-DarkGreen">
                Efficient computing:
              </span>{" "}
              we design our tools to be lightweight, caching results where
              possible so we don&apos;t recompute the same schedule 500 times.
            </li>
            <li>
              <span className="font-semibold text-DarkGreen">
                Thoughtful AI usage:
              </span>{" "}
              we reserve heavier AI calls for moments when it actually adds
              value, instead of blasting a giant model at every tiny button
              click.
            </li>
            <li>
              <span className="font-semibold text-DarkGreen">
                Less clutter, less waste:
              </span>{" "}
              fewer unnecessary pages and popups means less noise for you and
              fewer wasted resources on our side.
            </li>
          </ul>
        </section>

        {/* Decreased AI Use + Advisor Joke */}
        <section className="mb-8 grid gap-6 md:grid-cols-2">
          <article className="rounded-2xl border border-white/40 bg-white/95 p-6 shadow-sm">
            <h3 className="text-base font-semibold text-DarkGreen">
              Decreased AI Use (But Still Smart)
            </h3>
            <p className="mt-2 text-sm text-DarkGreen opacity-90">
              AI is powerful, but it&apos;s also compute-heavy. Instead of
              running huge models for everything, we:
            </p>
            <ul className="mt-3 space-y-2 text-sm text-DarkGreen opacity-90 list-disc list-inside">
              <li>Reuse previous results when possible.</li>
              <li>
                Run more intensive AI only when you&apos;re asking for actual
                scheduling or reasoning help.
              </li>
              <li>
                Use simpler logic for small things (you don&apos;t need a giant
                model to toggle &quot;I like morning classes&quot;).
              </li>
            </ul>
            <p className="mt-3 text-xs text-DarkGreen opacity-80">
              TL;DR: more brains where it matters, fewer wasted GPU cycles where
              it doesn&apos;t.
            </p>
          </article>

          <article className="rounded-2xl border border-white/40 bg-white/95 p-6 shadow-sm">
            <h3 className="text-base font-semibold text-DarkGreen">
              Saving Money by Cutting Advisor Workforce* 😉
            </h3>
            <p className="mt-2 text-sm text-DarkGreen opacity-90">
              We&apos;re joking… mostly. DooleyHelpz can handle a lot of the
              repetitive stuff that human advisors get buried under:
            </p>
            <ul className="mt-3 space-y-2 text-sm text-DarkGreen opacity-90 list-disc list-inside">
              <li>Checking degree requirements for the 47th time.</li>
              <li>Explaining what &quot;GER&quot; means… again.</li>
              <li>Comparing three different schedule versions endlessly.</li>
            </ul>
            <p className="mt-3 text-xs text-DarkGreen opacity-80">
              *Real advisors are still precious and very much alive. We&apos;re
              here to support them, not replace them — by freeing up time for
              the nuanced, human parts of advising.
            </p>
          </article>
        </section>

        {/* No AI Art */}
        <section className="mb-4 rounded-2xl border border-white/40 bg-white p-6 shadow-sm md:p-8">
          <h2 className="text-lg font-semibold text-DarkGreen">
            No AI Art Policy 🎨 
          </h2>
          <p className="mt-2 text-sm text-DarkGreen opacity-90">
            For visuals, we keep things simple and intentional:
          </p>

          <ul className="mt-4 space-y-3 text-sm text-DarkGreen opacity-90 list-disc list-inside">
            <li>
              <span className="font-semibold text-DarkGreen">
                No AI-generated art:
              </span>{" "}
              we avoid flooding the world with more synthetic images just
              because we can.
            </li>
            <li>
              <span className="font-semibold text-DarkGreen">
                Handmade or curated:
              </span>{" "}
              we prefer original icons, simple shapes, or carefully chosen
              assets instead of using AI art that steals from human artists.
            </li>
          </ul>

          <p className="mt-4 text-xs text-DarkGreen opacity-80">
            Does our mascot sometimes look like they were drawn at 3am during
            midterms? Yes. Is that part of the charm? Also yes.
          </p>
        </section>
      </main>
    </div>
  );
}