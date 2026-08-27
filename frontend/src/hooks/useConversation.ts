import { useQuery } from "@tanstack/react-query";
import { createConversation } from "../lib/api";
import type { Conversation } from "../lib/types";

export function useConversation() {
  return useQuery<Conversation>({
    queryKey: ["conversation"],
    queryFn: createConversation,
    staleTime: Infinity,
  });
}
