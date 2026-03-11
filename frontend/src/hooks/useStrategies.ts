import { useQuery } from "@tanstack/react-query";

import { getStrategies } from "../lib/api";

export function useStrategies() {
  return useQuery({
    queryKey: ["strategies"],
    queryFn: getStrategies,
  });
}
