import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Preview from "./Preview";

const key = "jobhunter-design-preview-v1";
const readState = () => JSON.parse(localStorage.getItem(key));
const mount = (path = "/preview") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Preview />
    </MemoryRouter>,
  );
const nav = () => within(screen.getByRole("navigation", { name: "Workspace" }));

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal("scrollTo", vi.fn());
  vi.stubGlobal(
    "fetch",
    vi.fn(() => {
      throw new Error("Preview must not call the backend");
    }),
  );
  // jsdom has no browser top layer. Verify dialog lifecycle separately from visual QA.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("design preview journeys", () => {
  it("labels fictional data and supports search with recovery from no results", async () => {
    const user = userEvent.setup();
    mount();
    expect(
      screen.getByText(/Fictional jobs and a sample profile/),
    ).toBeTruthy();
    await user.type(
      screen.getByRole("textbox", { name: "Search jobs" }),
      "no-such-role",
    );
    expect(
      screen.getByRole("heading", { name: "Let's widen the search." }),
    ).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(screen.getAllByRole("article")).toHaveLength(6);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("saves a role and makes it available in the Saved journey after remount", async () => {
    const user = userEvent.setup();
    const view = mount();
    await user.click(
      screen.getByRole("button", { name: "Save Frontend Engineer at Forma" }),
    );
    expect(readState().saved).toContain(1);
    view.unmount();
    mount("/preview?view=saved");
    expect(screen.getAllByRole("article")).toHaveLength(3);
    await user.click(
      screen.getByRole("button", { name: "Unsave Frontend Engineer at Forma" }),
    );
    expect(screen.getAllByRole("article")).toHaveLength(2);
  });

  it("combines type and location filters without including US-only roles", async () => {
    const user = userEvent.setup();
    mount("/preview?view=explore");
    await user.click(screen.getByRole("button", { name: "Filters" }));
    await user.selectOptions(
      screen.getByLabelText("Location eligibility"),
      "eligible",
    );
    await user.selectOptions(
      screen.getByLabelText("Employment type"),
      "Contract",
    );
    expect(screen.getAllByRole("article")).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "React Developer" }),
    ).toBeTruthy();
  });

  it("records one sample application, updates its status and persists notes", async () => {
    const user = userEvent.setup();
    mount("/preview?q=Forma");
    const trigger = screen.getByRole("button", { name: "View role" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Frontend Engineer" });
    await user.click(
      within(dialog).getByRole("button", { name: "Record sample application" }),
    );
    expect(
      within(dialog).getByRole("button", { name: "Application recorded" })
        .disabled,
    ).toBe(true);
    fireEvent(dialog, new Event("cancel", { bubbles: true, cancelable: true }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(document.activeElement).toBe(trigger);
    await user.click(nav().getByRole("button", { name: "Applications" }));
    await user.selectOptions(
      screen.getByLabelText("Status for Frontend Engineer at Forma"),
      "Interview",
    );
    const article = screen
      .getByRole("button", { name: "Frontend Engineer" })
      .closest("article");
    await user.type(
      within(article).getByLabelText("Notes"),
      "Prepare portfolio walkthrough",
    );
    expect(readState().applications.find((item) => item.jobId === 1)).toEqual({
      jobId: 1,
      stage: "Interview",
      notes: "Prepare portfolio walkthrough",
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("persists profile changes and applies them to the shortlist", async () => {
    const user = userEvent.setup();
    mount("/preview?view=profile");
    await user.clear(screen.getByLabelText("First name"));
    await user.type(screen.getByLabelText("First name"), "Sam");
    await user.selectOptions(
      screen.getByLabelText("Where are you based?"),
      "United States",
    );
    await user.click(screen.getByRole("button", { name: "Save preferences" }));
    expect(readState().profile.name).toBe("Sam");
    await user.click(nav().getByRole("button", { name: "For you" }));
    expect(screen.getByText("YOUR NEXT CHAPTER, SAM")).toBeTruthy();
    expect(screen.getByText("US residents")).toBeTruthy();
  });

  it("switches theme and recovers from invalid stored JSON", async () => {
    localStorage.setItem(key, "broken json");
    const user = userEvent.setup();
    mount();
    await user.click(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    );
    expect(readState().dark).toBe(true);
    expect(
      screen.getByRole("button", { name: "Switch to light theme" }),
    ).toBeTruthy();
  });
});
