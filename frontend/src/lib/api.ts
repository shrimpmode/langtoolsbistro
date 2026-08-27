import type { Conversation, Message, MenuItem } from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8010/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export function createConversation(): Promise<Conversation> {
  return request("/conversations/", { method: "POST" });
}

export function listMessages(conversationId: string): Promise<Message[]> {
  return request(`/conversations/${conversationId}/messages/`);
}

export function sendMessage(
  conversationId: string,
  content: string
): Promise<Message> {
  return request(`/conversations/${conversationId}/messages/`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function getMenu(): Promise<MenuItem[]> {
  return request("/menu/");
}
