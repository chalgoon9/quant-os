import { useQuery } from "@tanstack/react-query";

import { getKillSwitchActive } from "../lib/api";

export function useKillSwitchActive() {
  return useQuery({
    queryKey: ["kill-switch-active"],
    queryFn: getKillSwitchActive,
  });
}
