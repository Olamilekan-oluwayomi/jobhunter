import { useQuery } from "@tanstack/react-query";

import { getScrapeRuns } from "../api/scrape";
import { scrapeKeys } from "../utils/queryKeys";

export function useScrapeRuns(limit = 5) {
  return useQuery({
    queryKey: [...scrapeKeys.all, "runs", limit],
    queryFn: () => getScrapeRuns(limit),
  });
}