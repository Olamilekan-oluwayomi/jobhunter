const EXPERIENCE_LEVELS = [
  { value: "senior", label: "Senior", re: /\b(senior|sr\.?|principal|staff|lead|manager)\b/i },
  { value: "mid", label: "Mid level", re: /\b(mid|mid-level|intermediate)\b/i },
  { value: "junior", label: "Junior", re: /\b(junior|jr\.?|entry|entry-level|graduate|intern)\b/i },
];

export function isRemoteJob(job) {
  return ["title", "location", "description"]
    .map((key) => job[key] ?? "")
    .join(" ")
    .toLowerCase()
    .includes("remote");
}

export function experienceLevel(job) {
  const text = [job.title, job.description].filter(Boolean).join(" ");
  for (const level of EXPERIENCE_LEVELS) {
    if (level.re.test(text)) return level.value;
  }
  return null;
}

export function parseSalaryRange(salary) {
  if (!salary) return null;
  const hourly = /\/(?:hr|hour)|\bper\s*hour\b|hourly/i.test(salary);
  const text = salary.replace(/,/g, "").replace(/[–—]/g, "-");
  const matches = [...text.matchAll(/(\d+(?:\.\d+)?)\s*(k)?/gi)];

  if (!matches.length) return null;

  const values = matches.map((m) => {
    let v = parseFloat(m[1]);
    if (m[2]) v *= 1000;
    if (hourly) v *= 40 * 52;
    return v;
  });

  return { min: Math.min(...values), max: Math.max(...values) };
}

export function companyInitials(company) {
  const parts = company.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

const MATCH_KEYWORDS = [
  "remote",
  "javascript",
  "typescript",
  "react",
  "node",
  "go",
  "rust",
  "python",
  "rust",
  "full-stack",
  "fullstack",
  "backend",
  "frontend",
  "api",
  "saas",
];

/**
 * Client-side proxy for the backend notification matcher. The API does not
 * persist a `matched` flag on jobs, so the dashboard signal is computed here.
 */
export function matchDetails(job) {
  const text = [job.title, job.description, job.location]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  const keywords = MATCH_KEYWORDS.filter((kw) => text.includes(kw));

  let score = 0;
  if (keywords.length) score += 1;
  if (isRemoteJob(job)) score += 1;
  if (job.salary) score += 1;

  return { score, keywords };
}