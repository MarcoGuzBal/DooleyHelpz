import React from 'react'
import { useState } from 'react';

export default function PreferencesPage() {

  const [degreeType, setDegreeType] = useState("");
  const [year, setYear] = useState("");
  const [gradMonth, setGradMonth] = useState("");
  const [gradYear, setGradYear] = useState("");
  const [preferredCredits, setPreferredCredits] = useState("");
  const [interestList, setInterestList] = useState([]);
  const [tempDay, setTempDay] = useState("Monday");
  const [tempStart, setTempStart] = useState("");
  const [tempEnd, setTempEnd] = useState("");
  const [unavailable, setUnavailable] = useState([]);

  const interests = ["AI/ML", "Software Engineering", "Robotics", "Data Science"]
  const days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];


  function toggleInterest(x){
    if (interestList.includes(x)) setInterestList(interestList.filter(i => i!==x));
    else setInterestList(interestList.concat(x));
  }

  function addBlock(){
    if (!tempStart || !tempEnd) return;
    if (tempStart >= tempEnd) return; // start before end
    setUnavailable(unavailable.concat({day: tempDay, start: tempStart, end: tempEnd}));
    setTempStart(""); setTempEnd("");
  }

  function handleSubmit(){
    return null
  }

  return (

    <form onSubmit={handleSubmit} className='space-y-5'>
      {/* Degree Type Drop Down*/}
      <div className="flex flex-col">
          <label className="font-medium mb-1">Degree Type:</label>
          <select
            value={degreeType}
            onChange={(e) => setDegreeType(e.target.value)}
            className="border border-gray-300 rounded p-2 focus:outline-none focus:ring focus:ring-blue-200">
            <option value="">Select…</option>
            <option value="BS">Bachelor of Science</option>
            <option value="BA">Bachelor of Arts</option>
          </select>
      </div>

      {/* Fit Majors in here? */}

      {/* Degree Year Drop Down*/}
      <div className="flex flex-col">
        <label>
            Year:
            <select value={year} onChange={(e) => setYear(e.target.value)}
            className="border border-gray-300 rounded p-2">
            <option value="">Select…</option>
            <option value="Freshman">Freshman</option>
            <option value="Sophomore">Sophomore</option>
            <option value="Junior">Junior</option>
            <option value="Senior">Senior</option>
            </select>
        </label>
      </div>
      
      {/* Graduation Month Selection*/}
      <div className='flex flex-wrap items-center gap-3'>
        <label>
            Graduation Month
            <select value={gradMonth} 
            onChange={(e)=>setGradMonth(e.target.value)}>
            
                <option value="">MM</option>
                {["01","02","03","04","05","06","07","08","09","10","11","12"].map(m =>
                <option key={m} value={m}>{m}</option>
                )}
            </select>
        </label>

        <label>
            Graduation Year
            <input
                type="number"
                value={gradYear}
                onChange={(e)=>setGradYear(e.target.value)}
                placeholder="YYYY"
                min="2025"
                max="2035"
            />
        </label>
      </div>

      <label>
        Preferred Number of Credits 
        <input
          type="number"
          value={preferredCredits}
          onChange={(e)=>setPreferredCredits(e.target.value)}
          placeholder="12–22"
          min={year === "Senior" ? 1 : 12}
          max="22"
          step="1"
        />
      </label>

      {interests.map(x => (
        <label key={x}>
          <input 
            type="checkbox"
            checked={interestList.includes(x)}
            onChange={()=>toggleInterest(x)}
          />
        </label>
      ))}

      <select value={tempDay} onChange={(e)=>setTempDay(e.target.value)}>
        {days.map(d=><option key={d} value={d}>{d}</option>)}
      </select>
      <input type="time" value={tempStart} onChange={(e)=>setTempStart(e.target.value)} />
      <input type="time" value={tempEnd} onChange={(e)=>setTempEnd(e.target.value)} />
      <button type="button" onClick={addBlock}>Add</button>

      <ol>
        {unavailable.map((u,i)=>(
          <li key={i}>
            {u.day} {u.start}–{u.end}
            <button type="button" onClick={()=>setUnavailable(unavailable.filter((_,k)=>k!==i))}>
              remove
            </button>
          </li>
        ))}
      </ol>
    </form>
  );
}

