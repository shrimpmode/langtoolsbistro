import { useQueryClient, useQuery, type QueryClient } from "@tanstack/react-query";
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

function saveId(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Not fatal: the chat works, it just won't survive a reload.
  }
}

/**
 * The saved conversation, or null if there isn't one yet. Never creates
 * one: a visitor who only looks at the page shouldn't leave a database
 * row behind. See useEnsureConversation.
 */
async function loadSavedConversation(): Promise<Conversation | null> {
  const savedId = readSavedId();
  if (!savedId) return null;
  try {
    return await getConversation(savedId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      saveId(null); // deleted, or from another database
      return null;
    }
    throw err;
  }
}

export function useConversation() {
  return useQuery<Conversation | null>({
    queryKey: ["conversation"],
    queryFn: loadSavedConversation,
    staleTime: Infinity,
  });
}

// Shared across callers so sending a message and requesting a sign-in code
// at the same moment create one conversation, not two.
let creating: Promise<Conversation> | null = null;

async function ensureConversation(queryClient: QueryClient): Promise<Conversation> {
  const existing = queryClient.getQueryData<Conversation | null>(["conversation"]);
  if (existing) return existing;

  creating ??= createConversation()
    .then((conversation) => {
      saveId(conversation.id);
      // Brand new, so there's no history to fetch. Seeding it also stops a
      // fetch from racing the first message and showing it twice.
      queryClient.setQueryData(["messages", conversation.id], []);
      queryClient.setQueryData(["conversation"], conversation);
      return conversation;
    })
    .finally(() => {
      creating = null;
    });
  return creating;
}

/**
 * Returns a function that gives the current conversation, creating it
 * first if needed. Called when the guest actually does something that
 * needs one: sending a message or signing in.
 */
export function useEnsureConversation() {
  const queryClient = useQueryClient();
  return () => ensureConversation(queryClient);
}

/**
 * Forgets the current conversation. The next message or sign-in starts a
 * new one, so "New chat" itself creates nothing (and signs the guest out).
 */
export function useForgetConversation() {
  const queryClient = useQueryClient();
  return () => {
    saveId(null);
    queryClient.setQueryData(["conversation"], null);
  };
}
