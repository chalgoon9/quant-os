import { useQuery } from "@tanstack/react-query";

import { getRuntime } from "../lib/api";

export function useRuntime() {
  return useQuery({
    queryKey: ["runtime"],
    queryFn: getRuntime,
  });
}
