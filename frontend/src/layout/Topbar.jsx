import { Menu, RefreshCw } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useLocation } from "react-router-dom";

import { useToast } from "../components/ui/Toast";
import Button from "../components/ui/Button";
import { runScrape } from "../api/scrape";

const TITLES = {
  "/": "Dashboard",
  "/jobs": "Jobs",
  "/saved": "Saved Jobs",
  "/applications": "Applications",
};

export default function Topbar({ onMenuClick }) {
  const location = useLocation();
  const title = TITLES[location.pathname] ?? "JobHunter";
  const { push } = useToast();

  const scrapeMutation = useMutation({
    mutationFn: runScrape,
    onSuccess: (data) => {
      push("Scrape complete", {
        description: `${data.saved} new · ${data.already_exists} already seen · ${data.total_jobs} fetched`,
      });
    },
    onError: () => {
      push("Scrape failed", {
        description: "Check the backend logs and try again.",
        tone: "danger",
      });
    },
  });

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-base/80 px-4 backdrop-blur-md sm:px-6 lg:px-8">
      <button
        className="rounded-sm p-1.5 text-ink-secondary transition-colors hover:bg-line hover:text-ink lg:hidden"
        onClick={onMenuClick}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="flex items-center gap-2 text-sm">
        <span className="text-ink-faint">Pages</span>
        <span className="text-ink-faint">/</span>
        <span className="font-medium text-ink">{title}</span>
      </div>

      <div className="flex-1" />

      <Button
        variant="secondary"
        size="sm"
        onClick={() => scrapeMutation.mutate()}
        disabled={scrapeMutation.isPending}
      >
        <RefreshCw
          className={`h-3.5 w-3.5 ${scrapeMutation.isPending ? "animate-spin" : ""}`}
        />
        {scrapeMutation.isPending ? "Scraping…" : "Run scrape"}
      </Button>
    </header>
  );
}