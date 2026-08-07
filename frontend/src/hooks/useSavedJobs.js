import { useQuery } from "@tanstack/react-query";

import { getSavedJobs } from "../api/saved";
import { savedKeys } from "../utils/queryKeys";

export function useSavedJobs() {
  return useQuery({
    queryKey: savedKeys.all,
    queryFn: getSavedJobs,
  });
}