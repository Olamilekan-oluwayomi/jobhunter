import { Briefcase, SearchX } from "lucide-react";

import Card from "../components/ui/Card";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import { SkeletonRow } from "../components/ui/Skeleton";
import JobListItem from "./JobListItem";

export default function RecentJobs({
  jobs,
  isLoading,
  isError,
  errorMessage,
  onRetry,
  query,
}) {
  let body;

  if (isLoading) {
    body = (
      <div className="divide-y divide-line">
        {Array.from({ length: 5 }).map((_, i) => (
          <SkeletonRow key={i} />
        ))}
      </div>
    );
  } else if (isError) {
    body = <ErrorState message={errorMessage} onRetry={onRetry} />;
  } else if (!jobs.length) {
    body = query ? (
      <EmptyState
        icon={<SearchX className="h-5 w-5" />}
        title="No matching jobs"
        description={`Nothing matched “${query}”. Try a broader search.`}
      />
    ) : (
      <EmptyState
        icon={<Briefcase className="h-5 w-5" />}
        title="No jobs yet"
        description="Run a scrape to populate the job board."
      />
    );
  } else {
    body = (
      <div className="divide-y divide-line px-4">
        {jobs.map((job) => (
          <JobListItem key={job.id} job={job} />
        ))}
      </div>
    );
  }

  return (
    <Card>
      <div className="flex items-center justify-between border-b border-line px-4 py-3.5">
        <h2 className="text-sm font-semibold text-ink">Recent jobs</h2>
        <span className="text-xs text-ink-muted tabular-nums">
          {jobs.length} shown
        </span>
      </div>
      <div className="px-4">{body}</div>
    </Card>
  );
}