import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ToastProvider } from "../components/ui/Toast";
import {
  createApplication,
  getApplications,
  updateApplication,
} from "../api/applications";
import { getSavedJobs } from "../api/saved";
import SavedPage from "./Saved";
import ApplicationsPage from "./Applications";

vi.mock("../api/applications", () => ({
  createApplication: vi.fn(),
  getApplications: vi.fn(),
  updateApplication: vi.fn(),
}));
vi.mock("../api/saved", () => ({
  getSavedJobs: vi.fn(),
  saveJob: vi.fn(),
  unsaveJob: vi.fn(),
}));
vi.mock("../layout/DashboardLayout", () => ({
  default: ({ children }) => <>{children}</>,
}));

const job = {
  id: 5,
  title: "Frontend Engineer",
  company: "Acme",
  location: "Remote",
  url: "https://example.com/job",
  source: "Lever",
  posted_at: "2026-10-20T12:00:00Z",
};
function mount(children, route = "/") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}
beforeEach(() => vi.clearAllMocks());
afterEach(() => cleanup());

it("records an application only after an explicit record action", async () => {
  getSavedJobs.mockResolvedValue([{ id: 1, job_id: 5, job }]);
  createApplication.mockResolvedValue({ id: 8, job_id: 5, status: "applied" });
  const user = userEvent.setup();
  mount(<SavedPage />);
  await screen.findByText("Frontend Engineer");
  expect(createApplication).not.toHaveBeenCalled();
  expect(screen.getByRole("link", { name: "Apply" }).getAttribute("href")).toBe(
    job.url,
  );
  await user.click(
    screen.getByRole("button", { name: "I've applied — record it" }),
  );
  await waitFor(() =>
    expect(createApplication).toHaveBeenCalledWith({
      job_id: 5,
      status: "applied",
    }),
  );
  expect(await screen.findByText("Application recorded")).toBeTruthy();
});

it("preserves drafted notes when the server rejects a save", async () => {
  getApplications.mockResolvedValue({
    items: [
      {
        id: 8,
        job_id: 5,
        status: "applied",
        applied_at: "2026-10-20T12:00:00Z",
        notes: "",
        job,
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  });
  updateApplication.mockRejectedValue(new Error("Network unavailable"));
  const user = userEvent.setup();
  mount(<ApplicationsPage />);
  await screen.findByText("Frontend Engineer");
  await user.type(screen.getByLabelText("Notes"), "Ask about timezone overlap");
  await user.click(screen.getByRole("button", { name: "Save notes" }));
  expect(await screen.findByText("Could not save changes")).toBeTruthy();
  expect(screen.getByLabelText("Notes").value).toBe(
    "Ask about timezone overlap",
  );
  expect(updateApplication).toHaveBeenCalledWith(8, {
    notes: "Ask about timezone overlap",
  });
});

it("uses server-side status filtering from the URL", async () => {
  getApplications.mockResolvedValue({
    items: [],
    total: 0,
    page: 2,
    page_size: 20,
  });
  mount(<ApplicationsPage />, "/applications?status=interview&page=2");
  await screen.findByText("No applications in this stage");
  expect(getApplications).toHaveBeenCalledWith({
    page: 2,
    page_size: 20,
    status: "interview",
  });
});
