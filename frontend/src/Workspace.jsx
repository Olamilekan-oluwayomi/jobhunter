import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getJobs } from "./api/jobs";
import { getSavedJobs, saveJob, unsaveJob } from "./api/saved";
import {
  getApplications,
  createApplication,
  updateApplication,
} from "./api/applications";
import { runScrape } from "./api/scrape";
import { useToast } from "./components/ui/Toast";
import Preview from "./preview/Preview";
import { skillOptions } from "./preview/data";

async function allPages(fetcher, pageSize) {
  const items = [];
  let page = 1;
  while (true) {
    const result = await fetcher({ page, page_size: pageSize });
    items.push(...result.items);
    if (items.length >= result.total || !result.items.length) return items;
    page += 1;
  }
}

function presentJob(job) {
  const text = `${job.title} ${job.description || ""}`;
  const location = job.location || "Location not specified";
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
    salary: job.salary || "Not disclosed",
    type: /\bcontract\b/i.test(text)
      ? "Contract"
      : /full[- ]?time/i.test(text)
        ? "Full-time"
        : "Not specified",
    level: /\b(senior|staff|lead|principal)\b/i.test(job.title)
      ? "Senior"
      : /\b(junior|intern|entry)\b/i.test(job.title)
        ? "Junior"
        : "Not specified",
    skills: skillOptions.filter((skill) =>
      text.toLowerCase().includes(skill.toLowerCase()),
    ),
    region: /worldwide|anywhere in the world/i.test(location)
      ? "worldwide"
      : "unknown",
    summary:
      job.description ||
      "Open the original posting for the full role description.",
    tasks: [],
  };
}

export default function Workspace() {
  const client = useQueryClient();
  const { push } = useToast();
  const [drafts, setDrafts] = useState({});
  const busy = useRef(new Set());
  const jobs = useQuery({
    queryKey: ["workspace", "jobs"],
    queryFn: () => allPages(getJobs, 1000),
  });
  const saved = useQuery({
    queryKey: ["workspace", "saved"],
    queryFn: getSavedJobs,
  });
  const applications = useQuery({
    queryKey: ["workspace", "applications"],
    queryFn: () => allPages(getApplications, 100),
  });
  const refresh = () => client.invalidateQueries({ queryKey: ["workspace"] });
  const act = async (key, action, message) => {
    if (busy.current.has(key)) return;
    busy.current.add(key);
    try {
      await action();
      await refresh();
      push(message);
    } catch (error) {
      push(
        error.response?.status === 409
          ? "Already recorded. Refreshing your workspace."
          : "Could not save changes. Please try again.",
        { tone: "danger" },
      );
      if (error.response?.status === 409) refresh();
    } finally {
      busy.current.delete(key);
    }
  };
  const scrape = useMutation({
    mutationFn: runScrape,
    onSuccess: (result) => {
      refresh();
      push(`${result.saved} new jobs added`, {
        description: `${result.total_jobs} openings checked.`,
      });
    },
    onError: () =>
      push("Could not fetch new jobs. Please try again.", { tone: "danger" }),
  });
  const all = new Map((jobs.data || []).map((job) => [job.id, job]));
  for (const entry of [...(saved.data || []), ...(applications.data || [])])
    if (entry.job) all.set(entry.job.id, entry.job);
  return (
    <Preview
      workspace={{
        jobs: [...all.values()].map(presentJob),
        saved: (saved.data || []).map((entry) => entry.job_id),
        applications: (applications.data || []).map((entry) => ({
          jobId: entry.job_id,
          stage: {
            applied: "Applied",
            interview: "Interview",
            offer: "Offer",
            rejected: "Closed",
          }[entry.status],
          notes: drafts[entry.job_id] ?? entry.notes ?? "",
        })),
        loading: jobs.isPending || saved.isPending || applications.isPending,
        error:
          jobs.isError || saved.isError || applications.isError
            ? "Some workspace data could not be loaded. "
            : "",
        retry: refresh,
        toggleSave: (id) => {
          const entry = saved.data?.find((item) => item.job_id === id);
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
          const entry = applications.data?.find((item) => item.job_id === id);
          if (!entry) return;
          const payload = {
            ...(values.stage
              ? {
                  status: {
                    Applied: "applied",
                    Interview: "interview",
                    Offer: "offer",
                    Closed: "rejected",
                  }[values.stage],
                }
              : {}),
            notes: values.notes ?? drafts[id] ?? entry.notes ?? "",
          };
          return act(
          `application-${id}-${values.stage ? "status" : "notes"}`,
            () => updateApplication(entry.id, payload),
            "Application updated",
          );
        },
        scrape: () => scrape.mutate(),
        scraping: scrape.isPending,
      }}
    />
  );
}
