import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Check } from "lucide-react";
import { Link } from "react-router-dom";
import { createApplication } from "../api/applications";
import { useSavedJobs } from "../hooks/useSavedJobs";
import { useToggleSaved } from "../hooks/useToggleSaved";
import { applicationKeys, statsKeys } from "../utils/queryKeys";
import { useToast } from "../components/ui/Toast";
import Button from "../components/ui/Button";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import PageLoader from "../components/PageLoader";
import JobCard from "../jobs/JobCard";
import DashboardLayout from "../layout/DashboardLayout";

export default function SavedPage() {
  const saved = useSavedJobs();
  const toggle = useToggleSaved();
  const queryClient = useQueryClient();
  const { push } = useToast();
  const record = useMutation({
    mutationFn: (jobId) =>
      createApplication({ job_id: jobId, status: "applied" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: applicationKeys.all });
      queryClient.invalidateQueries({ queryKey: statsKeys.all });
      push("Application recorded", {
        description: "You can update its status in Applications.",
      });
    },
    onError: (error) =>
      push(
        error.response?.status === 409
          ? "This application is already recorded"
          : "Could not record application",
        { tone: error.response?.status === 409 ? "info" : "danger" },
      ),
  });
  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">Saved jobs</h1>
          <p className="mt-2 text-sm text-ink-secondary">
            Your shortlist. Apply on the employer's site, then record your
            application here.
          </p>
        </header>
        {saved.isPending ? (
          <PageLoader />
        ) : saved.isError ? (
          <ErrorState
            message="We couldn't load your saved jobs."
            onRetry={saved.refetch}
          />
        ) : !saved.data?.length ? (
          <EmptyState
            icon={<Bookmark size={22} />}
            title="Your shortlist starts here"
            description="Save an opportunity from the Jobs page to return to it later."
            action={
              <Link className="text-accent hover:underline" to="/jobs">
                Explore jobs
              </Link>
            }
          />
        ) : (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {saved.data.map(
              (entry) =>
                entry.job && (
                  <section key={entry.id} className="flex flex-col gap-2">
                    <JobCard
                      job={entry.job}
                      saved
                      onToggleSave={() => {
                        if (!toggle.isPending)
                          toggle.mutate(
                            { ...entry.job, _savedId: entry.id },
                            {
                              onError: () =>
                                push("Could not remove saved job", {
                                  tone: "danger",
                                }),
                            },
                          );
                      }}
                    />
                    <Button
                      variant="secondary"
                      disabled={record.isPending}
                      onClick={() => record.mutate(entry.job_id)}
                    >
                      <Check size={15} />
                      {record.isPending && record.variables === entry.job_id
                        ? "Recording…"
                        : "I've applied — record it"}
                    </Button>
                  </section>
                ),
            )}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
