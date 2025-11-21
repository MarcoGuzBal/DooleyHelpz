export type Transcript = { expected_grad_year?: number | string; courses: string[] };
export type UserProfile = {
  username: string;
  degree_type?: string;
  major: string[];
  minor: string[];
  year?: number | string;
  expected_grad_term?: string;
  preference_order: string[];
  interest_tags: string[];
  transcript: Transcript;
};
export type EligibleResp = { username: string; eligible: string[]; blocked: Record<string, string> };

const API = process.env.NEXT_PUBLIC_BACKEND_URL || "";

export async function saveUser(username: string, profile: UserProfile) {
  const r = await fetch(`${API}/api/users/${encodeURIComponent(username)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  if (!r.ok) throw new Error(`saveUser failed ${r.status}`);
}

export async function getEligible(username: string): Promise<EligibleResp> {
  const r = await fetch(`${API}/api/users/${encodeURIComponent(username)}/eligible`, { cache: "no-store" });
  if (!r.ok) throw new Error(`getEligible failed ${r.status}`);
  return r.json();
}
