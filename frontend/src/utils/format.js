export function formatRelativeDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";

  const diffDays = Math.floor((Date.now() - date.getTime()) / 86_400_000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 30) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString();
}

function jobTime(job) {
  const time = new Date(job.posted_at ?? 0).getTime();
  return Number.isNaN(time) ? null : time;
}

/** Count jobs whose posted_at falls within the last `days` days. */
export function countWithinDays(jobs, days) {
  if (!jobs) return 0;
  const cutoff = Date.now() - days * 86_400_000;
  return jobs.filter((job) => {
    const time = jobTime(job);
    return time !== null && time >= cutoff;
  }).length;
}

/** Count jobs posted on the calendar day `offsetDays` ago (0 = today). */
export function countOnCalendarDay(jobs, offsetDays) {
  if (!jobs) return 0;
  const day = new Date(Date.now() - offsetDays * 86_400_000).toDateString();
  return jobs.filter((job) => {
    const date = new Date(job.posted_at ?? 0);
    return !Number.isNaN(date.getTime()) && date.toDateString() === day;
  }).length;
}