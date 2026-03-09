import { useMutation, useQueryClient } from "@tanstack/react-query";

import { postUpbitDailyIngestion } from "../lib/api";

export function useIngestUpbitDaily() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: postUpbitDailyIngestion,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["datasets"] }),
        queryClient.invalidateQueries({ queryKey: ["dataset-bars"] }),
      ]);
    },
  });
}
