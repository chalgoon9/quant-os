import { useQuery } from "@tanstack/react-query";

import { getBacktestRunDetail } from "../lib/api";

export function useBacktestRunDetail(runId: string | null) {
  return useQuery({
    queryKey: ["backtest-run-detail", runId],
    queryFn: () => getBacktestRunDetail(runId!),
    enabled: Boolean(runId),
  });
}
