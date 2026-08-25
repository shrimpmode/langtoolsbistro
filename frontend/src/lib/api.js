const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8010/api";

async function request(path, options) {
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

export function createConversation() {
  return request("/conversations/", { method: "POST" });
}

export function listMessages(conversationId) {
  return request(`/conversations/${conversationId}/messages/`);
}

export function sendMessage(conversationId, content) {
  return request(`/conversations/${conversationId}/messages/`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function getMenu() {
  return request("/menu/");
}
