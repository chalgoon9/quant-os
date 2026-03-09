import { useQuery } from "@tanstack/react-query";

import { getDailyReportLatest } from "../lib/api";

export function useDailyReport() {
  return useQuery({
    queryKey: ["daily-report-latest"],
    queryFn: getDailyReportLatest,
  });
}
