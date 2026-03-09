import { useQuery } from "@tanstack/react-query";

import { getOpsSummary } from "../lib/api";

export function useOpsSummary() {
  return useQuery({
    queryKey: ["ops-summary"],
    queryFn: getOpsSummary,
  });
}
