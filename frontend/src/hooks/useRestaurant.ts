import { useQuery } from "@tanstack/react-query";
import { getRestaurant } from "../lib/api";
import type { RestaurantDetails } from "../lib/types";

export function useRestaurant() {
  return useQuery<RestaurantDetails>({
    queryKey: ["restaurant"],
    queryFn: getRestaurant,
    // Keeps "Open now" honest if the page is left open across opening or
    // closing time. Paused automatically while the tab is in the background.
    refetchInterval: 60_000,
  });
}
