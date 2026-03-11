import { useQuery } from "@tanstack/react-query";

import { getBacktestRuns } from "../lib/api";

type UseBacktestRunsParams = {
  strategyId?: string;
  dataset?: string;
  profileId?: string;
  limit?: number;
};

export function useBacktestRuns(params: UseBacktestRunsParams) {
  return useQuery({
    queryKey: ["backtest-runs", params.strategyId, params.dataset, params.profileId, params.limit ?? 20],
    queryFn: () => getBacktestRuns(params),
  });
}
