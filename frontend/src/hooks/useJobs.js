import { useQuery } from "@tanstack/react-query";

import { getJobs } from "../api/jobs";
import { jobKeys } from "../utils/queryKeys";

export function useJobs(params) {
  return useQuery({
    queryKey: jobKeys.list(params),
    queryFn: () => getJobs(params),
  });
}