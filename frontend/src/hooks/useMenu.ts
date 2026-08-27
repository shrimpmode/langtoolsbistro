import { useQuery } from "@tanstack/react-query";
import { getMenu } from "../lib/api";
import type { MenuItem } from "../lib/types";

export function useMenu() {
  return useQuery<MenuItem[]>({
    queryKey: ["menu"],
    queryFn: getMenu,
  });
}
