export type MessageRole = "user" | "assistant";

export interface Conversation {
  id: string;
  created_at: string;
  guest_email: string;
}

export interface MockEmail {
  id: number;
  to: string;
  subject: string;
  body: string;
  sent_at: string;
}

export interface Message {
  id: number;
  role: MessageRole;
  content: string;
  tool_calls: ToolCall[];
  created_at: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  /** Structured data the tool returned for the UI; never shown to the model. */
  artifact?: ToolArtifact | null;
}

export interface ReservationCardData {
  code: string; // formatted, e.g. "K7Q-4MX"
  customer_name: string;
  party_size: number;
  date: string; // YYYY-MM-DD
  time: string; // HH:MM, 24-hour
  status: "confirmed" | "cancelled";
}

export interface ToolArtifact {
  kind: "reservation_created" | "reservation_list";
  reservations: ReservationCardData[];
}

export type MenuCategory = "appetizer" | "main" | "dessert" | "drink";

export interface MenuItem {
  id: number;
  name: string;
  description: string;
  category: MenuCategory;
  price: string;
  is_available: boolean;
}

export interface ChatBubble {
  role: MessageRole;
  content: string;
  toolsUsed?: string[];
  cards?: ToolArtifact[];
  isError?: boolean;
}
