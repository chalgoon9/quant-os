import { useQuery } from "@tanstack/react-query";

import { getDatasetBars } from "../lib/api";

export function useDatasetBars(dataset: string | null, symbol?: string, limit = 25) {
  return useQuery({
    queryKey: ["dataset-bars", dataset, symbol ?? "", limit],
    queryFn: () => getDatasetBars(dataset!, symbol, limit),
    enabled: Boolean(dataset),
  });
}
