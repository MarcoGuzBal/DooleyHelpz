import { useState } from 'react';
/* ------------------------ Helper Types ------------------------- */
const DEGREE_TYPES = ["BS", "BA"] as const;  
type DegreeType = typeof DEGREE_TYPES[number];

const YEARS = ["Freshman", "Sophomore", "Junior", "Senior"] as const;
type Year = typeof YEARS[number];

const INTERESTS = ["AI/ML", "Software Engineering", "Robotics", "Data Science"] as const;
type Interests = typeof INTERESTS[number]

const DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"] as const;
type Days = typeof DAYS[number]

const PRIORITY_KEYS = [
  "PROFESSOR_RATING",
  "TIME_PREFERENCE",
  "MAJOR_REQUIREMENTS",
  "GER_REQUIREMENTS",
  "INTERESTS"
] as const;

type PriorityKey = typeof PRIORITY_KEYS[number]

type TimeBlock = { day: Days; start: string; end: string };

type PreferencesPayload = {
  degreeType: DegreeType | "";
  //major: string; // you can restrict later if you have a list
  year: Year | "";
  expectedGraduation: { month: string; year: string };
  preferredCredits: number | ""; // store as string while typing; coerce on submit
  interests: Interests[];
  timeUnavailable: TimeBlock[];
  priorityOrder: PriorityKey[];
};

export default function PreferencesPage() {

  /* -------------------------- State ------------------------------ */
  const [degreeType, setDegreeType] = useState<DegreeType | "">("");
  const [year, setYear] = useState<Year | "">("");

  // Grad Info
  const [gradMonth, setGradMonth] = useState<string>("");
  const [gradYear, setGradYear] = useState<string>("");
  const [preferredCredits, setPreferredCredits] = useState<string>("");
  const [interestList, setInterestList] = useState<Interests[]>([]);

  // Time Unavailable
  const [tempDay, setTempDay] = useState<Days>("Monday");
  const [tempStart, setTempStart] = useState<string>("");
  const [tempEnd, setTempEnd] = useState<string>("");
  const [unavailable, setUnavailable] = useState<TimeBlock[]>([]);

  // Priority
  const [priorityOrder, setPriorityOrder] = useState<PriorityKey[]>([...PRIORITY_KEYS]);

  /* ----------------------- Utility Functions --------------------- */
  function toggleInterest(x: Interests){
    if (interestList.includes(x)) setInterestList(interestList.filter(i => i!==x));
    else setInterestList(interestList.concat(x));
  }

  function addBlock(){
    if (!tempStart || !tempEnd) return;
    if (tempStart >= tempEnd) return; // start before end
    setUnavailable(unavailable.concat([{day: tempDay, start: tempStart, end: tempEnd}]));
    setTempStart(""); setTempEnd("");
  }

  function move(i: number, dir: number) {
    const j = i + dir;
    if (j < 0 || j >= priorityOrder.length) return;
    const copy = priorityOrder.slice();
    const x = copy[i]; copy[i] = copy[j]; copy[j] = x;
    setPriorityOrder(copy);
  }

  function titleCaseFromKey(k: string) {
    return k
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(/(^| )(\w)/g, s => s.toUpperCase());
  }
  
  function handleSubmit(e: React.FormEvent){
    e.preventDefault(); 

    const n = preferredCredits === "" ? NaN : Number(preferredCredits);
    const min = year === "Senior" ? 1 : 12;

    if (!degreeType) return alert("Please select a degree type");
    if (!year) return alert("Please select your year");
    if (!gradMonth || !gradYear) return alert("Please set your expected graduation date");
    if (isNaN(n) || n < min || n > 22) return alert(`Credits must be between ${min} and 22`);

    const payload = {
      degreeType,
      year,
      expectedGraduation: { month: gradMonth, year: gradYear },
      preferredCredits: n,
      interests: interestList,
      timeUnavailable: unavailable,
      priorityOrder,
    };

    console.log("SUBMIT", payload);
    alert("Saved! Check console for JSON output.");

    // send to backend
    fetch("http://localhost:5001/api/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  /* --------------------------- JSX ------------------------------- */
  return (
    <form onSubmit={handleSubmit} className="space-y-5 max-w-xl mx-auto p-6 bg-white border rounded-lg">
      {/* Degree Type */}
      <div className="flex flex-col">
        <label className="font-medium mb-1">Degree Type</label>
        <select
          value={degreeType}
          onChange={(e) => setDegreeType(e.target.value as DegreeType | "")}
          className="border border-gray-300 rounded p-2 focus:outline-none focus:ring focus:ring-blue-200"
        >
          <option value="">Select…</option>
          {DEGREE_TYPES.map(d => (
            <option key={d} value={d}>
              {d === "BS" ? "Bachelor of Science" : "Bachelor of Arts"}
            </option>
          ))}
        </select>
      </div>

      {/* Year */}
      <div className="flex flex-col">
        <label className="font-medium mb-1">Year</label>
        <select
          value={year}
          onChange={(e) => setYear(e.target.value as Year | "")}
          className="border border-gray-300 rounded p-2"
        >
          <option value="">Select…</option>
          {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>

      {/* Graduation */}
      <fieldset className="border border-gray-200 rounded p-3">
        <legend className="font-semibold">Expected Graduation</legend>
        <div className="flex flex-wrap items-center gap-3">
          <label className="font-medium">Month</label>
          <select
            value={gradMonth}
            onChange={(e)=>setGradMonth(e.target.value)}
            className="border border-gray-300 rounded p-2 w-24"
          >
            <option value="">MM</option>
            {["01","02","03","04","05","06","07","08","09","10","11","12"].map(m =>
              <option key={m} value={m}>{m}</option>
            )}
          </select>

          <label className="font-medium">Year</label>
          <input
            type="number"
            value={gradYear}
            onChange={(e)=>setGradYear(e.target.value)}
            placeholder="YYYY"
            min="2025"
            max="2035"
            className="border border-gray-300 rounded p-2 w-28"
          />
        </div>
      </fieldset>

      {/* Credits */}
      <div className="flex flex-col">
        <label className="font-medium mb-1">Preferred Credits</label>
        <input
          type="number"
          value={preferredCredits}
          onChange={(e)=>setPreferredCredits(e.target.value)}
          placeholder={year === "Senior" ? "1–22" : "12–22"}
          min={year === "Senior" ? 1 : 12}
          max={22}
          step={1}
          className="border border-gray-300 rounded p-2"
        />
      </div>

      {/* Interests */}
      <fieldset className="border border-gray-200 rounded p-3">
        <legend className="font-semibold">Interests</legend>
        <div className="flex flex-col space-y-1 mt-1">
          {INTERESTS.map(x => (
            <label key={x} className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={interestList.includes(x)}
                onChange={()=>toggleInterest(x)}
              />
              <span>{x}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Time Unavailable */}
      <fieldset className="border border-gray-200 rounded p-3">
        <legend className="font-semibold">Time Unavailable</legend>
        <div className="flex items-center gap-2 mb-2">
          <select
            value={tempDay}
            onChange={(e)=>setTempDay(e.target.value as Days)}
            className="border border-gray-300 rounded p-2"
          >
            {DAYS.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
          <input
            type="time"
            value={tempStart}
            onChange={(e)=>setTempStart(e.target.value)}
            className="border border-gray-300 rounded p-2"
          />
          <input
            type="time"
            value={tempEnd}
            onChange={(e)=>setTempEnd(e.target.value)}
            className="border border-gray-300 rounded p-2"
          />
          <button type="button" onClick={addBlock} className="bg-blue-600 text-white rounded px-3 py-1">
            Add
          </button>
        </div>
        <ul className="list-disc pl-6">
          {unavailable.map((u,i)=>(
            <li key={`${u.day}-${u.start}-${u.end}`} className="flex items-center gap-2">
              <span>{u.day} {u.start}–{u.end}</span>
              <button
                type="button"
                onClick={()=>setUnavailable(unavailable.filter((_,k)=>k!==i))}
                className="text-red-600 hover:underline"
              >
                remove
              </button>
            </li>
          ))}
        </ul>
      </fieldset>

      {/* Ranking (↑/↓) */}
      <fieldset className="border border-gray-200 rounded p-3">
        <legend className="font-semibold">Order of Importance (1 = most important)</legend>
        <ol className="list-decimal pl-6 space-y-2">
          {priorityOrder.map((key, i) => (
            <li key={key} className="flex items-center gap-2">
              <span className="grow">{titleCaseFromKey(key)}</span>
              <button
                type="button"
                onClick={() => move(i,-1)}
                disabled={i===0}
                className="px-2 py-1 border rounded disabled:opacity-40"
              >
                ↑
              </button>
              <button
                type="button"
                onClick={() => move(i, 1)}
                disabled={i===priorityOrder.length-1}
                className="px-2 py-1 border rounded disabled:opacity-40"
              >
                ↓
              </button>
            </li>
          ))}
        </ol>
      </fieldset>

      <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 rounded">
        Save
      </button>

      {/* JSON Preview */}
      {/* <div>
        <h3 className="font-semibold mt-2">Live JSON Preview</h3>
        <pre className="bg-gray-100 text-sm p-3 rounded overflow-auto">
          {JSON.stringify(
            {
              degreeType,
              year,
              expectedGraduation: { month: gradMonth, year: gradYear },
              preferredCredits,
              interests: interestList,
              timeUnavailable: unavailable,
              priorityOrder,
            },
            null,
            2
          )}
        </pre>
      </div> */}
    </form>
  );
}

