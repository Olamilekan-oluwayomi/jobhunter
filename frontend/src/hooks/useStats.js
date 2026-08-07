import { useQuery } from "@tanstack/react-query";

import { getStats } from "../api/stats";
import { statsKeys } from "../utils/queryKeys";

export function useStats() {
  return useQuery({
    queryKey: statsKeys.all,
    queryFn: getStats,
  });
}