export type MessageRole = "user" | "assistant";

export interface Conversation {
  id: string;
  created_at: string;
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
  isError?: boolean;
}
