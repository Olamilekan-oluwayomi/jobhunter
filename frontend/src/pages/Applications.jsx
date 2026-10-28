import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, BriefcaseBusiness } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { getApplications, updateApplication } from "../api/applications";
import { applicationKeys, statsKeys } from "../utils/queryKeys";
import { useToast } from "../components/ui/Toast";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import PageLoader from "../components/PageLoader";
import DashboardLayout from "../layout/DashboardLayout";

const statuses = {
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};

function ApplicationEntry({ entry }) {
  const [notes, setNotes] = useState(entry.notes || "");
  const queryClient = useQueryClient();
  const { push } = useToast();
  const update = useMutation({
    mutationFn: (payload) => updateApplication(entry.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      queryClient.invalidateQueries({ queryKey: statsKeys.all });
      push("Application updated");
    },
    onError: () =>
      push("Could not save changes", {
        description: "Your notes are still here. Try again.",
        tone: "danger",
      }),
  });
  return (
    <article className="rounded-lg border border-line bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-accent">
            {entry.job?.company || "Company unavailable"}
          </p>
          <h2 className="mt-1 text-base font-semibold">
            {entry.job?.title || "Job unavailable"}
          </h2>
          <p className="mt-2 text-xs text-ink-secondary">
            Recorded {new Date(entry.applied_at).toLocaleDateString()} ·{" "}
            {entry.job?.location || "Location not specified"}
          </p>
        </div>
        {entry.job?.url && (
          <a
            className="flex items-center gap-1 text-xs text-accent hover:underline"
            href={entry.job.url}
            target="_blank"
            rel="noreferrer"
          >
            View posting <ArrowUpRight size={14} />
          </a>
        )}
      </div>
      <div className="mt-5 grid gap-4 sm:grid-cols-[160px_1fr]">
        <label className="text-xs text-ink-secondary">
          Status
          <select
            className="mt-2 block w-full rounded-sm border border-line bg-base p-2.5 text-sm text-ink"
            aria-label={`Status for ${entry.job?.title || entry.id}`}
            value={entry.status}
            disabled={update.isPending}
            onChange={(event) => update.mutate({ status: event.target.value, notes })}
          >
            {Object.entries(statuses).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <div>
          <label className="text-xs text-ink-secondary">
            Notes
            <textarea
              className="mt-2 block min-h-24 w-full rounded-sm border border-line bg-base p-3 text-sm text-ink"
              maxLength={2000}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Interview preparation, contacts, or your next step…"
            />
          </label>
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="text-xs text-ink-secondary">
              {notes.length}/2000
            </span>
            <Button
              size="sm"
              variant="secondary"
              disabled={update.isPending || notes === (entry.notes || "")}
              onClick={() => update.mutate({ notes })}
            >
              {update.isPending ? "Saving…" : "Save notes"}
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function ApplicationsPage() {
  const [search, setSearch] = useSearchParams();
  const parsedPage = Number(search.get("page"));
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;
  const status = Object.hasOwn(statuses, search.get("status"))
    ? search.get("status")
    : "";
  const params = { page, page_size: 20, ...(status ? { status } : {}) };
  const applications = useQuery({
    queryKey: [...applicationKeys.all, params],
    queryFn: () => getApplications(params),
  });
  const total = applications.data?.total || 0;
  return (
    <DashboardLayout>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Applications
            </h1>
            <p className="mt-2 text-sm text-ink-secondary">
              Keep track of your conversations, decisions, and next steps.
            </p>
          </div>
          <label className="text-xs text-ink-secondary">
            Filter by status
            <select
              className="mt-2 block rounded-sm border border-line bg-surface p-2 text-sm text-ink"
              value={status}
              onChange={(event) =>
                setSearch(
                  event.target.value ? { status: event.target.value } : {},
                )
              }
            >
              <option value="">All statuses</option>
              {Object.entries(statuses).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </header>
        {applications.isPending ? (
          <PageLoader />
        ) : applications.isError ? (
          <ErrorState
            message="We couldn't load applications. Check that the updated backend is running."
            onRetry={applications.refetch}
          />
        ) : !applications.data?.items.length ? (
          <EmptyState
            icon={<BriefcaseBusiness size={22} />}
            title={
              status
                ? "No applications in this stage"
                : "Your next chapter starts here"
            }
            description="After submitting an application, record it from Saved jobs."
            action={
              <Link className="text-accent hover:underline" to="/saved">
                Open saved jobs
              </Link>
            }
          />
        ) : (
          <div className="space-y-4">
            {applications.data.items.map((entry) => (
              <ApplicationEntry key={entry.id} entry={entry} />
            ))}
          </div>
        )}
        {!applications.isPending && !applications.isError && (
          <div className="mt-6 flex items-center justify-between gap-4">
            <span className="text-xs text-ink-secondary">
              {total} application{total === 1 ? "" : "s"} · Page {page}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() =>
                  setSearch({
                    ...(status ? { status } : {}),
                    page: String(page - 1),
                  })
                }
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page * 20 >= total}
                onClick={() =>
                  setSearch({
                    ...(status ? { status } : {}),
                    page: String(page + 1),
                  })
                }
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
