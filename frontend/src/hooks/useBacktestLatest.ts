import { useQuery } from "@tanstack/react-query";

import { getBacktestLatest } from "../lib/api";

export function useBacktestLatest() {
  return useQuery({
    queryKey: ["backtest-latest"],
    queryFn: getBacktestLatest,
  });
}
