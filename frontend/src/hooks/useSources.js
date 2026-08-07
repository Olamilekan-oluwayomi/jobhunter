import { useQuery } from "@tanstack/react-query";

import { getSources } from "../api/sources";
import { sourcesKeys } from "../utils/queryKeys";

export function useSources() {
  return useQuery({
    queryKey: sourcesKeys.all,
    queryFn: getSources,
  });
}