import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { ToastProvider } from "./components/ui/Toast";
import Workspace from "./Workspace";
import { getJobs } from "./api/jobs";
import { getSavedJobs } from "./api/saved";
import { getApplications } from "./api/applications";

vi.mock("./api/jobs", () => ({getJobs: vi.fn()}));
vi.mock("./api/saved", () => ({getSavedJobs: vi.fn(),saveJob:vi.fn(),unsaveJob:vi.fn()}));
vi.mock("./api/applications", () => ({getApplications:vi.fn(),createApplication:vi.fn(),updateApplication:vi.fn()}));
vi.mock("./api/scrape", () => ({runScrape:vi.fn()}));
beforeEach(()=>{localStorage.clear();getSavedJobs.mockResolvedValue([]);getApplications.mockResolvedValue({items:[],total:0});});
afterEach(()=>{cleanup();vi.clearAllMocks();});
function mount(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ToastProvider><MemoryRouter><Workspace /></MemoryRouter></ToastProvider></QueryClientProvider>);}
it("renders real API jobs without sample branding",async()=>{
 getJobs.mockResolvedValue({items:[{id:42,title:"Production React Engineer",company:"Actual Employer",location:"Remote",description:"React and TypeScript",url:"https://example.com/job"}],total:1});
 mount();
 expect(await screen.findByRole("button",{name:"Production React Engineer"})).toBeTruthy();
 expect(screen.queryByText("Forma")).toBeNull();
 expect(screen.queryByText(/Fictional jobs/)).toBeNull();
 expect(screen.getByRole("button",{name:"Find new jobs"})).toBeTruthy();
});
it("does not fill an empty account with fictional saved jobs or applications",async()=>{
 getJobs.mockResolvedValue({items:[],total:0});mount();
 await screen.findByText("Let's widen the search.");
 expect(screen.queryByText("Layers")).toBeNull();
 expect(screen.queryByText("Northstar")).toBeNull();
});
it("shows an API failure without substituting sample data",async()=>{
 getJobs.mockRejectedValue(new Error("offline"));mount();
 expect(await screen.findByRole("alert")).toBeTruthy();
 expect(screen.queryByText("Forma")).toBeNull();
});
