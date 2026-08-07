import { Activity, FolderHeart, Send } from "lucide-react";

import Card from "../components/ui/Card";
import EmptyState from "../components/ui/EmptyState";
import { SkeletonRow } from "../components/ui/Skeleton";
import { formatRelativeDate } from "../utils/format";
import { matchDetails } from "../utils/jobMeta";

function MatchBadge() {
  return (
    <span className="rounded-sm bg-accent-soft px-1.5 py-0.5 text-[10px] font-medium text-accent-hover">
      Match
    </span>
  );
}

function ActivityRow({ icon, text, meta, badge, time }) {
  return (
    <div className="flex items-start gap-3 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-line bg-raised text-ink-muted">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-ink">{text}</p>
        {meta && <p className="mt-0.5 truncate text-xs text-ink-muted">{meta}</p>}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        {badge}
        <span className="text-xs text-ink-faint">{time}</span>
      </div>
    </div>
  );
}

export default function RecentActivity({ recentJobs, stats, isLoading }) {
  if (isLoading) {
    return (
      <Card>
        <div className="border-b border-line px-4 py-3.5">
          <h2 className="text-sm font-semibold text-ink">Latest matches</h2>
        </div>
        <div className="px-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonRow key={i} />
          ))}
        </div>
      </Card>
    );
  }

  const jobRows = recentJobs.slice(0, 5).map((job) => ({
    key: `job-${job.id}`,
    icon: <Activity className="h-4 w-4" />,
    text: job.title,
    meta: `${job.company} · ${job.source}`,
    badge: matchDetails(job).score > 0 ? <MatchBadge /> : null,
    time: formatRelativeDate(job.posted_at),
  }));

  const statusRows = Object.entries(stats?.by_status ?? {}).map(
    ([status, count]) => ({
      key: `status-${status}`,
      icon: <Send className="h-4 w-4" />,
      text: `${count} application${count === 1 ? "" : "s"} · ${status}`,
      meta: "Application pipeline",
      badge: null,
      time: "",
    }),
  );

  const savedRow =
    stats?.total_saved > 0
      ? {
          key: "saved",
          icon: <FolderHeart className="h-4 w-4" />,
          text: `${stats.total_saved} ${stats.total_saved === 1 ? "job" : "jobs"} saved`,
          meta: "Bookmarks",
          badge: null,
          time: "",
        }
      : null;

  const rows = [...jobRows, ...statusRows, savedRow].filter(Boolean);

  return (
    <Card>
      <div className="border-b border-line px-4 py-3.5">
        <h2 className="text-sm font-semibold text-ink">Latest matches</h2>
      </div>
      {rows.length ? (
        <div className="divide-y divide-line px-4">
          {rows.slice(0, 5).map((row) => (
            <ActivityRow key={row.key} {...row} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Activity className="h-5 w-5" />}
          title="No activity yet"
          description="New jobs and application updates will appear here."
        />
      )}
    </Card>
  );
}