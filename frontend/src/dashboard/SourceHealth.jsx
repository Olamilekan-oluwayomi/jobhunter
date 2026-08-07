import { Activity } from "lucide-react";

import SourceBadge from "../components/SourceBadge";
import Card from "../components/ui/Card";
import EmptyState from "../components/ui/EmptyState";
import { SkeletonRow } from "../components/ui/Skeleton";
import { formatRelativeDate } from "../utils/format";

const STATUS = {
  active: { label: "Active", dot: "bg-success" },
  stale: { label: "Not fetched", dot: "bg-warning" },
  none: { label: "No runs yet", dot: "bg-ink-faint" },
};

export default function SourceHealth({ sources, runs, isLoading }) {
  const showSkeleton = isLoading && !sources.length;

  if (showSkeleton) {
    return (
      <Card>
        <div className="flex items-center justify-between border-b border-line px-4 py-3.5">
          <h2 className="text-sm font-semibold text-ink">Source health</h2>
        </div>
        <div className="px-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      </Card>
    );
  }

  if (!sources.length) {
    return (
      <Card>
        <EmptyState
          icon={<Activity className="h-5 w-5" />}
          title="No sources yet"
          description="Run a scrape to register sources and their last scrape status."
        />
      </Card>
    );
  }

  const latest = runs[0];
  const bySource = latest?.by_source ?? {};

  const rows = sources.map((source) => {
    const meta = bySource[source.name] ?? { fetched: 0, new: 0 };
    let status;
    if (!latest) status = STATUS.none;
    else if ((meta.fetched ?? 0) > 0) status = STATUS.active;
    else status = STATUS.stale;

    return {
      name: source.name,
      jobs: source.job_count,
      fetched: meta.fetched ?? 0,
      fresh: meta.new ?? 0,
      lastRun: latest?.started_at ?? null,
      ...status,
    };
  });

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-line px-4 py-3.5">
        <h2 className="text-sm font-semibold text-ink">Source health</h2>
        <span className="text-xs text-ink-muted">
          {latest
            ? `last run ${formatRelativeDate(latest.started_at)}`
            : "no scrape runs recorded"}
        </span>
      </div>

      <div className="divide-y divide-line">
        {rows.map((row) => (
          <div
            key={row.name}
            className="flex items-center gap-3 px-4 py-2.5"
          >
            <span
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${row.dot}`}
              aria-hidden="true"
            />
            <SourceBadge source={row.name} />
            <span className="w-24 shrink-0 text-xs text-ink-secondary">
              {row.label}
            </span>

            <div className="flex-1" />

<span className="hidden text-xs text-ink-muted sm:inline">
              {row.lastRun
                ? row.fetched > 0
                  ? `${row.fresh} new in last run`
                  : "0 fetched last run"
                : "—"}
            </span>
            <span className="w-16 shrink-0 text-right text-sm font-medium text-ink tabular-nums">
              {row.jobs}
            </span>
            <span className="w-14 shrink-0 text-left text-xs text-ink-muted">
              jobs
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}