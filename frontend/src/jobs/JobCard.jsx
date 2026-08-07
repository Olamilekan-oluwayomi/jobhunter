import { memo, useState } from "react";
import {
  ArrowUpRight,
  Bookmark,
  CalendarClock,
  ChevronDown,
  MapPin,
  Wallet,
  Wifi,
} from "lucide-react";

import CompanyLogo from "../components/CompanyLogo";
import SourceBadge from "../components/SourceBadge";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import { formatRelativeDate } from "../utils/format";
import { isRemoteJob } from "../utils/jobMeta";

const DESCRIPTION_LIMIT = 240;

function JobCardBase({ job, saved, onToggleSave }) {
  const [expanded, setExpanded] = useState(false);

  const description = job.description?.trim();
  const showMore = description && description.length > DESCRIPTION_LIMIT;
  const visible = expanded
    ? description
    : description?.slice(0, DESCRIPTION_LIMIT);

  return (
    <Card className="flex h-full flex-col p-4 transition-colors duration-150 hover:border-line-strong">
      <div className="flex items-start justify-between gap-3">
        <CompanyLogo company={job.company} />
        <div className="flex flex-wrap items-center justify-end gap-1.5">
          {isRemoteJob(job) && (
            <Badge variant="accent">
              <Wifi className="h-3 w-3" />
              Remote
            </Badge>
          )}
          <SourceBadge source={job.source} />
        </div>
      </div>

      <h3 className="mt-3 line-clamp-2 text-base leading-snug font-semibold text-ink">
        <a href={job.url} target="_blank" rel="noreferrer" className="transition-colors hover:text-accent-hover">
          {job.title}
        </a>
      </h3>

      <p className="mt-1 text-sm font-medium text-accent-hover">{job.company}</p>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted">
        {job.location && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3.5 w-3.5" />
            {job.location}
          </span>
        )}
        {job.salary && (
          <span className="inline-flex items-center gap-1 tabular-nums">
            <Wallet className="h-3.5 w-3.5" />
            {job.salary}
          </span>
        )}
        <span className="inline-flex items-center gap-1 tabular-nums">
          <CalendarClock className="h-3.5 w-3.5" />
          {formatRelativeDate(job.posted_at)}
        </span>
      </div>

      {visible && (
        <div className="mt-3">
          <p
            className={`text-sm leading-relaxed text-ink-secondary whitespace-pre-line ${expanded ? "" : "line-clamp-3"}`}
          >
            {visible}
          </p>
          {showMore && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-accent-hover transition-colors hover:text-accent"
            >
              {expanded ? "Show less" : "Show more"}
              <ChevronDown
                className={`h-3.5 w-3.5 transition-transform duration-150 ${expanded ? "rotate-180" : ""}`}
              />
            </button>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-1 items-end gap-2 border-t border-line pt-3">
        <a href={job.url} target="_blank" rel="noreferrer" className="min-w-0 flex-1">
          <Button variant="primary" size="sm" className="w-full">
            Apply
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Button>
        </a>
        <Button
          variant={saved ? "secondary" : "outline"}
          size="sm"
          onClick={() => onToggleSave(job)}
          aria-label={saved ? "Remove from saved" : "Save job"}
        >
          <Bookmark className={`h-3.5 w-3.5 ${saved ? "fill-current text-accent" : ""}`} />
          {saved ? "Saved" : "Save"}
        </Button>
      </div>
    </Card>
  );
}

const JobCard = memo(JobCardBase);
export default JobCard;