import { useMutation, useQueryClient } from "@tanstack/react-query";

import { saveJob, unsaveJob } from "../api/saved";
import { savedKeys } from "../utils/queryKeys";

export function useToggleSaved() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (job) =>
      job._savedId ? unsaveJob(job._savedId) : saveJob(job.id),
    onMutate: async (job) => {
      await queryClient.cancelQueries({ queryKey: savedKeys.all });
      const previous = queryClient.getQueryData(savedKeys.all);

      queryClient.setQueryData(savedKeys.all, (old = []) => {
        if (job._savedId) {
          return old.filter((entry) => entry.id !== job._savedId);
        }
        return [
          {
            id: `pending-${job.id}`,
            job_id: job.id,
            saved_at: new Date().toISOString(),
            job,
          },
          ...old,
        ];
      });

      return { previous };
    },

    onError: (_err, _job, context) => {
      if (context?.previous) {
        queryClient.setQueryData(savedKeys.all, context.previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: savedKeys.all });
    },
  });
}