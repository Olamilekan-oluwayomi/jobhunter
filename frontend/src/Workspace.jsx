import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  getApplications,
  createApplication,
  updateApplication,
} from "./api/applications";
import { saveJob, unsaveJob } from "./api/saved";
import { runScrape } from "./api/scrape";
import {
  getMe,
  logout,
  saveProfile,
  getWorkspaceIndex,
  discoverJobs,
  getDiscoveryJob,
} from "./api/auth";
import { useToast } from "./components/ui/Toast";
import SignIn from "./components/SignIn";
import Preview from "./preview/Preview";

function presentJob(job) {
  return {
    ...job,
    live: true,
    mark: job.company.slice(0, 2),
    color: "#e5eddf",
    days: job.posted_at
      ? Math.max(
          0,
          Math.floor(
            (Date.now() - new Date(job.posted_at).getTime()) / 86400000,
          ),
        )
      : null,
    location: job.location || "Location not specified",
    salary: job.salary || "Not disclosed",
    type: job.type || "Not specified",
    level: job.level || "Not specified",
    skills: job.match?.matched_skills || [],
    summary:
      job.description ||
      "Open the original posting for the full role description.",
    tasks: [],
  };
}

export default function Workspace() {
  const client = useQueryClient();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: getMe,
    retry: false,
    staleTime: 60000,
  });
  useEffect(() => {
    const expired = async () => {
      await client.cancelQueries({ queryKey: ["workspace"] });
      client.removeQueries({ queryKey: ["workspace"] });
      client.setQueryData(["session"], null);
    };
    window.addEventListener("jobhunter-session-expired", expired);
    return () =>
      window.removeEventListener("jobhunter-session-expired", expired);
  }, [client]);
  if (session.isPending) return <p role="status">Loading your workspace?</p>;
  if (session.isError && session.error.response?.status !== 401)
    return (
      <div role="alert">
        Could not load your account.{" "}
        <button onClick={() => session.refetch()}>Try again</button>
      </div>
    );
  if (!session.data || session.isError)
    return (
      <SignIn
        onSuccess={(user) => {
          client.removeQueries({ queryKey: ["workspace"] });
          client.setQueryData(["session"], user);
        }}
      />
    );
  return <AccountWorkspace key={session.data.id} user={session.data} />;
}

const stages = {
  applied: "Applied",
  interview: "Interview",
  offer: "Offer",
  rejected: "Closed",
};
const statuses = {
  Applied: "applied",
  Interview: "interview",
  Offer: "offer",
  Closed: "rejected",
};

function AccountWorkspace({ user }) {
  const client = useQueryClient();
  const { push } = useToast();
  const [params] = useSearchParams();
  const view = params.get("view") || "discover";
  const page = Math.max(1, Number.parseInt(params.get("page") || "1", 10) || 1);
  const [drafts, setDrafts] = useState({});
  const busy = useRef(new Set());
  const updates = useRef(new Map());
  const prefix = ["workspace", user.id];
  const filters = {
    page,
    page_size: 20,
    search: params.get("q") || undefined,
    employment_type: ["Full-time", "Contract"].includes(params.get("type"))
      ? params.get("type")
      : undefined,
    eligible_only: params.get("location") === "eligible",
    saved_only: view === "saved",
    sort: params.get("sort") === "newest" ? "newest" : "match",
  };
  const jobs = useQuery({
    queryKey: [...prefix, "jobs", filters],
    queryFn: ({ signal }) => discoverJobs(filters, signal),
    enabled: view !== "applications" && view !== "profile",
  });
  const index = useQuery({
    queryKey: [...prefix, "index"],
    queryFn: getWorkspaceIndex,
  });
  const applications = useQuery({
    queryKey: [...prefix, "applications", page],
    queryFn: () => getApplications({ page, page_size: 20 }),
    enabled: view === "applications",
  });
  const refresh = () => client.invalidateQueries({ queryKey: prefix });
  const act = async (key, action, message) => {
    if (busy.current.has(key)) return false;
    busy.current.add(key);
    try {
      await action();
      await refresh();
      push(message);
      return true;
    } catch (error) {
      push(
        typeof error.response?.data?.detail === "string"
          ? error.response.data.detail
          : "Could not save changes. Please try again.",
        { tone: "danger" },
      );
      if (error.response?.status === 409) await refresh();
      return false;
    } finally {
      busy.current.delete(key);
    }
  };
  const scrape = useMutation({
    mutationFn: runScrape,
    onSuccess: (result) => {
      refresh();
      push(`${result.saved} new jobs added`);
    },
    onError: (error) =>
      push(
        error.response?.data?.detail ||
          "Could not fetch new jobs. Please try again.",
        { tone: "danger" },
      ),
  });
  const all = new Map((jobs.data?.items || []).map((job) => [job.id, job]));
  for (const entry of applications.data?.items || [])
    if (entry.job) all.set(entry.job.id, entry.job);
  const listing = view === "applications" ? applications : jobs;
  const records =
    view === "applications"
      ? applications.data?.items || []
      : index.data?.applications || [];
  return (
    <Preview
      workspace={{
        profile: user.profile,
        jobs: [...all.values()].map(presentJob),
        resultIds: (jobs.data?.items || []).map((job) => job.id),
        total: listing.data?.total || 0,
        page,
        pageSize: 20,
        saved: (index.data?.saved || []).map((entry) => entry.job_id),
        applications: records.map((entry) => ({
          jobId: entry.job_id,
          stage: stages[entry.status],
          notes: drafts[entry.job_id] ?? entry.notes ?? "",
        })),
        applicationCount: index.data?.applications?.length || 0,
        activeCount: (index.data?.applications || []).filter(
          (entry) => entry.status !== "rejected",
        ).length,
        loading:
          index.isPending ||
          (listing.isPending && listing.fetchStatus !== "idle"),
        error:
          index.isError || listing.isError
            ? "Some workspace data could not be loaded. "
            : "",
        retry: refresh,
        toggleSave: (id) => {
          const entry = index.data?.saved.find((item) => item.job_id === id);
          return act(
            `saved-${id}`,
            () => (entry ? unsaveJob(entry.id) : saveJob(id)),
            entry ? "Removed from saved jobs" : "Job saved",
          );
        },
        recordApplication: (id) =>
          act(
            `apply-${id}`,
            () => createApplication({ job_id: id, status: "applied" }),
            "Application recorded",
          ),
        draftNote: (id, notes) =>
          setDrafts((previous) => ({ ...previous, [id]: notes })),
        updateApplication: (id, values) => {
          const entry = index.data?.applications.find(
            (item) => item.job_id === id,
          );
          if (!entry) return;
          // Status changes never carry a stale copy of notes. Queue every edit per application.
          const payload = {
            ...(values.stage ? { status: statuses[values.stage] } : {}),
            ...(Object.hasOwn(values, "notes") ? { notes: values.notes } : {}),
          };
          const pending = (updates.current.get(id) || Promise.resolve())
            .catch(() => {})
            .then(async () => {
              const success = await act(
                `application-${id}`,
                () => updateApplication(entry.id, payload),
                "Application updated",
              );
              if (success && Object.hasOwn(payload, "notes"))
                setDrafts((previous) => {
                  if (previous[id] !== payload.notes) return previous;
                  const next = { ...previous };
                  delete next[id];
                  return next;
                });
            });
          updates.current.set(id, pending);
          pending.finally(() => {
            if (updates.current.get(id) === pending) updates.current.delete(id);
          });
          return pending;
        },
        saveProfile: (profile) =>
          act(
            "profile",
            async () => {
              const next = await saveProfile(profile);
              client.setQueryData(["session"], next);
            },
            "Preferences saved",
          ),
        openJob: async (id) =>
          presentJob(
            await client.fetchQuery({
              queryKey: [...prefix, "detail", id, user.profile],
              queryFn: ({ signal }) => getDiscoveryJob(id, signal),
            }),
          ),
        canScrape: user.is_admin,
        scrape: () => scrape.mutate(),
        scraping: scrape.isPending,
        signOut: () =>
          act(
            "logout",
            async () => {
              await logout();
              await client.cancelQueries({ queryKey: ["workspace"] });
              client.removeQueries({ queryKey: ["workspace"] });
              client.setQueryData(["session"], null);
            },
            "Signed out",
          ),
      }}
    />
  );
}
