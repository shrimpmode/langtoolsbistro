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

export interface StreamHandlers {
  onToken?: (text: string) => void;
  onToolStart?: (tool: string) => void;
  onDone?: (message: Message) => void;
  /** Backend-reported failure mid-stream (e.g. the agent call itself errored).
   * Distinct from streamMessage() rejecting, which signals a transport-level
   * failure (bad HTTP status, network error, or an aborted request). */
  onError?: (error: Error) => void;
}

/**
 * Consumes the SSE stream from the streaming message endpoint, invoking the
 * matching handler for each event as it arrives. Uses fetch + a manual
 * ReadableStream reader rather than EventSource, since EventSource can only
 * issue GET requests and this endpoint takes the message body as POST data.
 */
export async function streamMessage(
  conversationId: string,
  content: string,
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(
    `${API_BASE_URL}/conversations/${conversationId}/messages/stream/`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
      signal,
    }
  );
  if (!res.ok || !res.body) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventType = "";
      let data = "";
      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event: ")) eventType = line.slice("event: ".length);
        else if (line.startsWith("data: ")) data = line.slice("data: ".length);
      }
      if (!eventType || !data) continue;

      const payload = JSON.parse(data);
      if (eventType === "token") handlers.onToken?.(payload.text);
      else if (eventType === "tool_start") handlers.onToolStart?.(payload.tool);
      else if (eventType === "done") handlers.onDone?.(payload as Message);
      else if (eventType === "error") handlers.onError?.(new Error(payload.detail));
    }
  }
}

export function getMenu(): Promise<MenuItem[]> {
  return request("/menu/");
}
