import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ToastProvider } from "./components/ui/Toast";
import Workspace from "./Workspace";
import {
  getMe,
  getWorkspaceIndex,
  discoverJobs,
  getDiscoveryJob,
  saveProfile,
} from "./api/auth";
import { getApplications, updateApplication } from "./api/applications";

vi.mock("./api/auth", () => ({
  getMe: vi.fn(),
  getWorkspaceIndex: vi.fn(),
  discoverJobs: vi.fn(),
  getDiscoveryJob: vi.fn(),
  saveProfile: vi.fn(),
  logout: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
}));
vi.mock("./api/saved", () => ({ saveJob: vi.fn(), unsaveJob: vi.fn() }));
vi.mock("./api/applications", () => ({
  getApplications: vi.fn(),
  createApplication: vi.fn(),
  updateApplication: vi.fn(),
}));
vi.mock("./api/scrape", () => ({ runScrape: vi.fn() }));
const user = {
  id: 2,
  email: "alice@example.com",
  is_admin: false,
  profile: {
    name: "Alice",
    role: "Frontend Engineer",
    location: "Nigeria",
    skills: ["React"],
    remote: true,
    level: "Mid-level",
  },
};
const job = {
  id: 42,
  title: "Production React Engineer",
  company: "Actual Employer",
  location: "Worldwide",
  url: "https://example.com/job",
  match: { score: 88, matched_skills: ["React"] },
  eligibility: { status: "eligible", detail: "Source says Worldwide" },
};
beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("scrollTo", vi.fn());
  getMe.mockResolvedValue(user);
  getWorkspaceIndex.mockResolvedValue({ saved: [], applications: [] });
  getApplications.mockResolvedValue({ items: [], total: 0 });
  discoverJobs.mockResolvedValue({ items: [job], total: 1 });
  getDiscoveryJob.mockResolvedValue({
    ...job,
    description: "Full job description",
  });
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});
function mount(path = "/") {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <ToastProvider>
        <MemoryRouter initialEntries={[path]}>
          <Workspace />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}
it("renders backend scores and fetches one page, with on-demand details", async () => {
  mount();
  await screen.findByRole("button", { name: "Production React Engineer" });
  expect(screen.getByText("88/100")).toBeTruthy();
  expect(screen.queryByText("Forma")).toBeNull();
  expect(screen.queryByRole("button", { name: "Find new jobs" })).toBeNull();
  expect(discoverJobs.mock.calls[0][0].page_size).toBe(20);
  expect(discoverJobs).toHaveBeenCalledTimes(1);
  await userEvent.click(
    screen.getByRole("button", { name: "Production React Engineer" }),
  );
  expect(await screen.findByText("Full job description")).toBeTruthy();
  expect(getDiscoveryJob.mock.calls[0][0]).toBe(42);
});
it("shows sign in before requesting private jobs", async () => {
  getMe.mockRejectedValue({ response: { status: 401 } });
  mount();
  await screen.findByRole("button", { name: "Sign in" });
  expect(discoverJobs).not.toHaveBeenCalled();
  expect(getWorkspaceIndex).not.toHaveBeenCalled();
});
it("passes URL search and pagination to the server", async () => {
  discoverJobs.mockResolvedValue({ items: [job], total: 41 });
  mount("/?q=React&type=Contract&location=eligible&page=2&sort=newest");
  await screen.findByRole("button", { name: "Production React Engineer" });
  expect(discoverJobs.mock.calls[0][0]).toMatchObject({
    page: 2,
    search: "React",
    employment_type: "Contract",
    eligible_only: true,
    sort: "newest",
  });
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(discoverJobs.mock.calls.at(-1)[0].page).toBe(3));
});
it("shows API failures without sample data", async () => {
  discoverJobs.mockRejectedValue(new Error("offline"));
  mount();
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("Forma")).toBeNull();
});
it("queues application edits and sends status independently of notes", async () => {
  getWorkspaceIndex.mockResolvedValue({
    saved: [],
    applications: [{ id: 7, job_id: 42, status: "applied" }],
  });
  getApplications.mockResolvedValue({
    items: [{ id: 7, job_id: 42, status: "applied", notes: "Original", job }],
    total: 1,
  });
  let complete;
  updateApplication
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          complete = resolve;
        }),
    )
    .mockResolvedValue({});
  mount("/?view=applications");
  const notes = await screen.findByRole("textbox", { name: "Notes" });
  fireEvent.change(notes, { target: { value: "New note" } });
  fireEvent.blur(notes);
  await waitFor(() => expect(updateApplication).toHaveBeenCalledTimes(1));
  fireEvent.change(
    screen.getByRole("combobox", {
      name: "Status for Production React Engineer at Actual Employer",
    }),
    { target: { value: "Interview" } },
  );
  expect(updateApplication).toHaveBeenCalledTimes(1);
  expect(updateApplication.mock.calls[0]).toEqual([7, { notes: "New note" }]);
  complete({});
  await waitFor(() => expect(updateApplication).toHaveBeenCalledTimes(2));
  expect(updateApplication.mock.calls[1]).toEqual([7, { status: "interview" }]);
});
it("saves account preferences instead of storing them in the browser", async () => {
  saveProfile.mockImplementation(async (profile) => ({ ...user, profile }));
  mount("/?view=profile");
  const name = await screen.findByRole("textbox", { name: "First name" });
  fireEvent.change(name, { target: { value: "Alicia" } });
  await userEvent.click(
    screen.getByRole("button", { name: /Save preferences/ }),
  );
  await waitFor(() => expect(saveProfile).toHaveBeenCalled());
  expect(saveProfile.mock.calls[0][0].name).toBe("Alicia");
  expect(localStorage.getItem("jobhunter-preferences-v1")).toBeNull();
});
