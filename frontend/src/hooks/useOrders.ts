import { useQuery } from "@tanstack/react-query";

import { getOrders } from "../lib/api";

export function useOrders(limit = 25) {
  return useQuery({
    queryKey: ["orders", limit],
    queryFn: () => getOrders(limit),
  });
}
