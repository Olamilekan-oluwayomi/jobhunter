import { useCallback, useMemo, useState } from "react";

import { useJobs, useScrapeRuns, useSources, useStats } from "../hooks";
import RecentActivity from "./RecentActivity";
import RecentJobs from "./RecentJobs";
import SearchBar from "./SearchBar";
import SourceHealth from "./SourceHealth";
import StatsGrid from "./StatsGrid";

export default function Dashboard() {
  const [query, setQuery] = useState("");

  const statsQuery = useStats();
  const jobsQuery = useJobs({ page_size: 50 });
  const sourcesQuery = useSources();
  const runsQuery = useScrapeRuns(1);

  const handleQuery = useCallback((value) => setQuery(value), []);

  const allJobs = useMemo(
    () => jobsQuery.data?.items ?? [],
    [jobsQuery.data],
  );

  const jobs = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return allJobs;
    return allJobs.filter((job) =>
      [job.title, job.company, job.location, job.source]
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [allJobs, query]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Track your job search across every source.
        </p>
      </div>

      <StatsGrid
        stats={statsQuery.data}
        jobs={allJobs}
        isLoading={jobsQuery.isLoading}
      />

      <div className="mt-6">
        <SourceHealth
          sources={sourcesQuery.data ?? []}
          runs={runsQuery.data ?? []}
          isLoading={sourcesQuery.isLoading}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="min-w-0 xl:col-span-2">
          <div className="mb-4">
            <SearchBar onQuery={handleQuery} />
          </div>
          <RecentJobs
            jobs={jobs}
            query={query}
            isLoading={jobsQuery.isLoading}
            isError={jobsQuery.isError}
            errorMessage={jobsQuery.error?.message}
            onRetry={() => void jobsQuery.refetch()}
          />
        </div>

        <RecentActivity
          recentJobs={jobs}
          stats={statsQuery.data}
          isLoading={statsQuery.isLoading}
        />
      </div>
    </div>
  );
}