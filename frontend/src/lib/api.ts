import type { Conversation, Message, MenuItem, MockEmail, ToolArtifact } from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8010/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }
  return res.json();
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: string
  ) {
    super(`${status}: ${body}`);
  }

  /** The API's human-readable {"detail": ...} message, if it sent one. */
  get detail(): string | null {
    try {
      return JSON.parse(this.body).detail ?? null;
    } catch {
      return null;
    }
  }
}

export function createConversation(): Promise<Conversation> {
  return request("/conversations/", { method: "POST" });
}

export function getConversation(conversationId: string): Promise<Conversation> {
  return request(`/conversations/${conversationId}/`);
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
  onToolEnd?: (tool: string, artifact: ToolArtifact | null) => void;
  onDone?: (message: Message) => void;
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
      else if (eventType === "tool_end") handlers.onToolEnd?.(payload.tool, payload.artifact);
      else if (eventType === "done") handlers.onDone?.(payload as Message);
    }
  }
}

export function getMenu(): Promise<MenuItem[]> {
  return request("/menu/");
}

export function requestLoginCode(conversationId: string, email: string): Promise<void> {
  return request(`/conversations/${conversationId}/login/`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function verifyLoginCode(
  conversationId: string,
  email: string,
  code: string
): Promise<Conversation> {
  return request(`/conversations/${conversationId}/login/verify/`, {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
}

export function logout(conversationId: string): Promise<Conversation> {
  return request(`/conversations/${conversationId}/logout/`, { method: "POST" });
}

/** Emails the mock email service "sent". The endpoint 404s outside dev. */
export function getMockInbox(): Promise<MockEmail[]> {
  return request("/mock-inbox/");
}
