import { useDeferredValue, useMemo, useState } from "react";
import { LayoutGrid, SearchX, Table } from "lucide-react";

import { useJobs, useSavedJobs, useSources, useToggleSaved } from "../hooks";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import Input from "../components/ui/Input";
import Select from "../components/ui/Select";
import Skeleton from "../components/ui/Skeleton";
import { useToast } from "../components/ui/Toast";
import FilterBar, { FilterChips, activeFilterCount } from "./FilterBar";
import JobCard from "./JobCard";
import JobsTable, { JobsTableSkeleton } from "./JobsTable";
import Pagination from "./Pagination";
import { experienceLevel, parseSalaryRange } from "../utils/jobMeta";

const SORT_OPTIONS = [
  { value: "posted_at-desc", label: "Newest first" },
  { value: "posted_at-asc", label: "Oldest first" },
  { value: "salary-desc", label: "Salary high-to-low" },
  { value: "salary-asc", label: "Salary low-to-high" },
  { value: "company-asc", label: "Company A–Z" },
  { value: "title-asc", label: "Title A–Z" },
];

const EMPTY_FILTERS = {
  search: "",
  source: "",
  company: "",
  location: "",
  experience: "",
  remoteOnly: false,
  salaryMin: undefined,
  salaryMax: undefined,
};

const DISMISSED_KEY = "jobhunter-dismissed";

function loadDismissed() {
  try {
    return new Set(JSON.parse(localStorage.getItem(DISMISSED_KEY) ?? "[]"));
  } catch {
    return new Set();
  }
}

function JobCardSkeleton() {
  return (
    <div className="rounded-md border border-line bg-surface p-4">
      <div className="flex items-start justify-between">
        <Skeleton className="h-9 w-9" />
        <div className="flex gap-1.5">
          <Skeleton className="h-5 w-14" />
          <Skeleton className="h-5 w-14" />
        </div>
      </div>
      <Skeleton className="mt-3 h-4 w-3/4" />
      <Skeleton className="mt-2 h-3 w-1/3" />
      <div className="mt-3 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-2/3" />
      </div>
      <div className="mt-4 flex gap-2">
        <Skeleton className="h-8 flex-1" />
        <Skeleton className="h-8 w-20" />
      </div>
    </div>
  );
}

export default function JobsExplorer() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [sort, setSort] = useState("posted_at-desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [view, setView] = useState("table");
  const [filterOpen, setFilterOpen] = useState(false);
  const [dismissed, setDismissed] = useState(loadDismissed);

  const { push } = useToast();
  const deferredSearch = useDeferredValue(filters.search);

  const jobsQuery = useJobs({ page_size: 1000 });
  const savedQuery = useSavedJobs();
  const sourcesQuery = useSources();
  const toggleSave = useToggleSaved();

  const sources = sourcesQuery.data ?? [];

  const savedByJobId = useMemo(() => {
    const map = new Map();
    for (const entry of savedQuery.data ?? []) map.set(entry.job_id, entry.id);
    return map;
  }, [savedQuery.data]);

  const allJobs = useMemo(
    () => jobsQuery.data?.items ?? [],
    [jobsQuery.data],
  );

  const filtered = useMemo(() => {
    const company = filters.company.trim().toLowerCase();
    const location = filters.location.trim().toLowerCase();
    const q = deferredSearch.trim().toLowerCase();

    return allJobs.filter((job) => {
      if (company && !job.company.toLowerCase().includes(company)) return false;
      if (location && !(job.location ?? "").toLowerCase().includes(location))
        return false;
      if (filters.source && job.source !== filters.source) return false;
      if (filters.experience) {
        const level = experienceLevel(job);
        if (level !== filters.experience) return false;
      }
      if (filters.remoteOnly) {
        const text = `${job.title} ${job.location ?? ""} ${job.description ?? ""}`
          .toLowerCase();
        if (!text.includes("remote")) return false;
      }
      if (filters.salaryMin || filters.salaryMax) {
        const range = parseSalaryRange(job.salary);
        if (!range) return false;
        if (filters.salaryMin && range.max < filters.salaryMin) return false;
        if (filters.salaryMax && range.min > filters.salaryMax) return false;
      }
      if (
        q &&
        ![job.title, job.company, job.location, job.salary, job.description]
          .join(" ")
          .toLowerCase()
          .includes(q)
      ) {
        return false;
      }
      return true;
    });
  }, [allJobs, filters, deferredSearch]);

  const visible = useMemo(
    () => filtered.filter((job) => !dismissed.has(job.id)),
    [filtered, dismissed],
  );

  const sorted = useMemo(() => {
    const [field, order] = sort.split("-");
    const dir = order === "asc" ? 1 : -1;
    const ordered = [...visible];

    ordered.sort((a, b) => {
      if (field === "salary") {
        const ar = parseSalaryRange(a.salary);
        const br = parseSalaryRange(b.salary);
        const av = ar?.min ?? -1;
        const bv = br?.min ?? -1;
        return (av - bv) * dir;
      }
      if (field === "title") return a.title.localeCompare(b.title) * dir;
      if (field === "company") return a.company.localeCompare(b.company) * dir;
      return (new Date(a.posted_at) - new Date(b.posted_at)) * dir;
    });

    return ordered;
  }, [visible, sort]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageJobs = sorted.slice((safePage - 1) * pageSize, safePage * pageSize);

  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setPage(1);
  };

  const removeFilter = (key) => {
    if (key === "__all__") {
      handleResetFilters();
      return;
    }
    setFilters((f) => ({ ...f, [key]: EMPTY_FILTERS[key] }));
    setPage(1);
  };

  const handleToggleSave = (job) => {
    const savedId = savedByJobId.get(job.id);
    toggleSave.mutate(
      { ...job, _savedId: savedId },
      {
        onSuccess: () =>
          push(savedId ? "Removed from saved" : "Job saved", {
            description: job.company,
          }),
        onError: () =>
          push("Couldn't update saved jobs", { tone: "danger" }),
      },
    );
  };

  const handleDismiss = (jobId) => {
    setDismissed((prev) => {
      const next = new Set(prev);
      next.add(jobId);
      localStorage.setItem(DISMISSED_KEY, JSON.stringify([...next]));
      return next;
    });
    push("Job dismissed", { tone: "info" });
  };

  const restoreDismissed = () => {
    setDismissed(new Set());
    localStorage.removeItem(DISMISSED_KEY);
  };

  const isLoading =
    jobsQuery.isLoading ||
    jobsQuery.isFetching ||
    savedQuery.isLoading ||
    savedQuery.isFetching;

  if (jobsQuery.isError) {
    return (
      <ErrorState
        message={jobsQuery.error?.message}
        onRetry={() => jobsQuery.refetch()}
      />
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-5">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Job Board
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          {jobsQuery.data?.total ?? 0} jobs across {sources.length} sources ·{" "}
          {sorted.length.toLocaleString()} shown
        </p>
      </header>

      <div className="sticky top-16 z-10 -mx-4 mb-4 border-b border-line bg-base/85 px-4 py-3 backdrop-blur-md sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative min-w-0 flex-1 basis-64">
            <svg
              className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink-muted"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <Input
              value={filters.search}
              onChange={(e) => {
                setFilters((f) => ({ ...f, search: e.target.value }));
                setPage(1);
              }}
              placeholder="Search jobs, companies, skills…"
              className="pl-9"
              aria-label="Search jobs"
            />
          </div>

          <FilterBar
            filters={filters}
            sources={sources}
            onChange={(next) => {
              setFilters(next);
              setPage(1);
            }}
            open={filterOpen}
            onToggle={() => setFilterOpen((v) => !v)}
          />

          <Select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
            aria-label="Sort jobs"
            className="w-44"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </Select>

          <div className="flex items-center gap-1 rounded-sm border border-line bg-raised p-0.5">
            <button
              type="button"
              onClick={() => setView("table")}
              aria-pressed={view === "table"}
              aria-label="Table view"
              className={`rounded-sm p-1.5 transition-colors ${
                view === "table"
                  ? "bg-accent-soft text-accent-hover"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              <Table className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setView("cards")}
              aria-pressed={view === "cards"}
              aria-label="Card view"
              className={`rounded-sm p-1.5 transition-colors ${
                view === "cards"
                  ? "bg-accent-soft text-accent-hover"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>
        </div>

        {(activeFilterCount(filters) > 0 || dismissed.size > 0) && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <FilterChips filters={filters} onRemove={removeFilter} />
            {dismissed.size > 0 && (
              <button
                type="button"
                onClick={restoreDismissed}
                className="text-xs font-medium text-ink-muted transition-colors hover:text-ink"
              >
                Restore {dismissed.size} dismissed
              </button>
            )}
          </div>
        )}
      </div>

      {isLoading ? (
        view === "table" ? (
          <JobsTableSkeleton />
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <JobCardSkeleton key={i} />
            ))}
          </div>
        )
      ) : pageJobs.length ? (
        <>
          {view === "table" ? (
            <JobsTable
              jobs={pageJobs}
              onToggleSave={handleToggleSave}
              onDismiss={handleDismiss}
              savedByJobId={savedByJobId}
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {pageJobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  saved={Boolean(savedByJobId.get(job.id))}
                  onToggleSave={handleToggleSave}
                />
              ))}
            </div>
          )}

          <div className="mt-6 flex flex-col items-center gap-3">
            <div
              className="flex items-center gap-1 text-xs text-ink-muted"
              role="group"
              aria-label="Page size"
            >
              Per page
              {[25, 50, 100].map((size) => (
                <button
                  key={size}
                  type="button"
                  onClick={() => {
                    setPageSize(size);
                    setPage(1);
                  }}
                  aria-pressed={pageSize === size}
                  className={`rounded-sm px-2 py-1 font-medium tabular-nums ${
                    pageSize === size
                      ? "bg-raised text-ink"
                      : "text-ink-muted hover:text-ink"
                  }`}
                >
                  {size}
                </button>
              ))}
            </div>
            <Pagination
              page={safePage}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          </div>
        </>
      ) : (
        <EmptyState
          icon={<SearchX className="h-5 w-5" />}
          title="No jobs match"
          description="Try adjusting your search or clearing the filters."
          action={
            <Button variant="secondary" onClick={handleResetFilters}>
              Clear filters
            </Button>
          }
        />
      )}
    </div>
  );
}