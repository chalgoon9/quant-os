import { useQuery } from "@tanstack/react-query";

import { getReconciliationLatest } from "../lib/api";

export function useReconciliationLatest() {
  return useQuery({
    queryKey: ["reconciliation-latest"],
    queryFn: getReconciliationLatest,
  });
}
