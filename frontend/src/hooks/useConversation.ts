import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, createConversation, getConversation } from "../lib/api";
import type { Conversation } from "../lib/types";

// Remembering the conversation id is what lets a page reload keep the chat
// history and the guest's sign-in, which both belong to the conversation.
const STORAGE_KEY = "orchai.conversationId";

function readSavedId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null; // storage blocked (e.g. private mode): just start fresh
  }
}

function saveId(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    // Not fatal: the chat works, it just won't survive a reload.
  }
}

async function loadOrCreateConversation(): Promise<Conversation> {
  const savedId = readSavedId();
  if (savedId) {
    try {
      return await getConversation(savedId);
    } catch (err) {
      // Deleted or from another database: fall through and start a new one.
      if (!(err instanceof ApiError && err.status === 404)) throw err;
    }
  }
  const conversation = await createConversation();
  saveId(conversation.id);
  return conversation;
}

export function useConversation() {
  return useQuery<Conversation>({
    queryKey: ["conversation"],
    queryFn: loadOrCreateConversation,
    staleTime: Infinity,
  });
}

/** Starts a fresh conversation, which also signs the guest out. */
export function useStartNewConversation() {
  const queryClient = useQueryClient();
  return async () => {
    const conversation = await createConversation();
    saveId(conversation.id);
    queryClient.setQueryData(["conversation"], conversation);
  };
}
