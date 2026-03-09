import { useQuery } from "@tanstack/react-query";

import { getOrderDetail } from "../lib/api";

export function useOrderDetail(orderId: string | null) {
  return useQuery({
    queryKey: ["order-detail", orderId],
    queryFn: () => getOrderDetail(orderId!),
    enabled: Boolean(orderId),
  });
}
