import { useQuery } from "@tanstack/react-query";

import { postBacktestCompare } from "../lib/api";

export function useBacktestCompare(runIds: string[]) {
  return useQuery({
    queryKey: ["backtest-compare", ...runIds],
    queryFn: () => postBacktestCompare(runIds),
    enabled: runIds.length >= 2,
  });
}
