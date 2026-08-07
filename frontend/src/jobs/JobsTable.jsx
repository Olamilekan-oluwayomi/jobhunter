import { ArrowUpRight, Bookmark, X } from "lucide-react";

import CompanyLogo from "../components/CompanyLogo";
import SourceBadge from "../components/SourceBadge";
import Button from "../components/ui/Button";
import Skeleton from "../components/ui/Skeleton";
import { formatRelativeDate } from "../utils/format";
import { matchDetails } from "../utils/jobMeta";

function MatchCell({ job }) {
  const { score } = matchDetails(job);
  if (score <= 0) return <span className="text-ink-faint">—</span>;
  return (
    <span
      className="inline-block h-1.5 w-1.5 rounded-full bg-accent"
      title={`Matched on ${score} cue${score === 1 ? "" : "s"}`}
      aria-label={`Matched on ${score} cue${score === 1 ? "" : "s"}`}
    />
  );
}

function JobRow({ job, saved, onToggleSave, onDismiss }) {
  return (
    <tr className="group transition-colors duration-150 hover:bg-raised/60">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <CompanyLogo company={job.company} size="sm" />
          <div className="min-w-0">
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer"
              className="block max-w-sm truncate text-sm font-medium text-ink transition-colors group-hover:text-accent-hover"
            >
              {job.title}
            </a>
            <div className="mt-0.5 flex items-center gap-1.5 text-xs text-ink-muted">
              <span className="font-medium text-ink-secondary">{job.company}</span>
              {job.location && (
                <span className="hidden truncate md:inline">· {job.location}</span>
              )}
            </div>
          </div>
        </div>
      </td>

      <td className="px-2 py-3 whitespace-nowrap">
        <SourceBadge source={job.source} />
      </td>

      <td className="px-2 py-3 text-sm whitespace-nowrap text-ink-secondary tabular-nums">
        {job.salary ?? "—"}
      </td>

      <td className="px-2 py-3 text-sm whitespace-nowrap text-ink-muted tabular-nums">
        {formatRelativeDate(job.posted_at)}
      </td>

      <td className="px-2 py-3 text-center">
        <MatchCell job={job} />
      </td>

      <td className="py-3 pr-4 pl-2 text-right">
        <div className="flex items-center justify-end gap-1 lg:opacity-0 lg:transition-opacity lg:duration-150 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100">
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            aria-label={`Apply to ${job.title}`}
          >
            <Button variant="ghost" size="sm">
              <ArrowUpRight className="h-4 w-4" />
            </Button>
          </a>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onToggleSave(job)}
            aria-label={saved ? "Remove from saved" : "Save job"}
          >
            <Bookmark
              className={`h-4 w-4 ${saved ? "fill-current text-accent" : ""}`}
            />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDismiss(job.id)}
            aria-label="Dismiss job"
          >
            <X className="h-4 w-4 text-ink-muted" />
          </Button>
        </div>
      </td>
    </tr>
  );
}

export default function JobsTable({
  jobs,
  onToggleSave,
  onDismiss,
  savedByJobId,
}) {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-surface">
      <div className="overflow-x-auto scrollbar-thin">
        <table className="min-w-[720px] w-full border-collapse">
          <thead>
            <tr className="border-b border-line text-left text-xs font-medium tracking-wider text-ink-faint uppercase">
              <th scope="col" className="px-4 py-2.5 font-medium">
                Posting
              </th>
              <th scope="col" className="px-2 py-2.5 font-medium">
                Source
              </th>
              <th scope="col" className="px-2 py-2.5 font-medium">
                Salary
              </th>
              <th scope="col" className="px-2 py-2.5 font-medium">
                Posted
              </th>
              <th scope="col" className="px-2 py-2.5 text-center font-medium">
                Match
              </th>
              <th scope="col" className="py-2.5 pr-4 pl-2 text-right font-medium">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {jobs.map((job) => (
              <JobRow
                key={job.id}
                job={job}
                saved={Boolean(savedByJobId.get(job.id))}
                onToggleSave={onToggleSave}
                onDismiss={onDismiss}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function JobsTableSkeleton() {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-surface">
      <div className="border-b border-line px-4 py-2.5">
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="divide-y divide-line">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3">
            <Skeleton className="h-8 w-8" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-3.5 w-2/5" />
              <Skeleton className="h-3 w-1/4" />
            </div>
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-5 w-20" />
            <Skeleton className="h-4 w-14" />
          </div>
        ))}
      </div>
    </div>
  );
}