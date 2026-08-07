import { CalendarClock, MapPin } from "lucide-react";

import SourceBadge from "../components/SourceBadge";
import { formatRelativeDate } from "../utils/format";
import { matchDetails } from "../utils/jobMeta";

export default function JobListItem({ job }) {
  const { score } = matchDetails(job);

  return (
    <div className="group py-3.5 first:pt-0 last:pb-0">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <a
              href={job.url}
              target="_blank"
              rel="noreferrer"
              className="truncate text-sm font-medium text-ink transition-colors group-hover:text-accent-hover"
            >
              {job.title}
            </a>
            {score > 0 && (
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            )}
            <SourceBadge source={job.source} />
          </div>

          <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
            <span className="font-medium text-ink-secondary">{job.company}</span>
            {job.location && (
              <span className="inline-flex items-center gap-1">
                <MapPin className="h-3 w-3" />
                {job.location}
              </span>
            )}
            <span className="inline-flex items-center gap-1">
              <CalendarClock className="h-3 w-3" />
              {formatRelativeDate(job.posted_at)}
            </span>
          </div>
        </div>

        {job.salary && (
          <span className="shrink-0 rounded-sm bg-raised px-2 py-0.5 text-xs font-medium text-ink-secondary tabular-nums">
            {job.salary}
          </span>
        )}
      </div>
    </div>
  );
}