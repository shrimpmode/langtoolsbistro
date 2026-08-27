import { useMutation } from "@tanstack/react-query";
import { sendMessage } from "../lib/api";
import type { Message } from "../lib/types";

interface SendMessageInput {
  conversationId: string;
  content: string;
}

export function useSendMessage() {
  return useMutation<Message, Error, SendMessageInput>({
    mutationFn: ({ conversationId, content }) =>
      sendMessage(conversationId, content),
  });
}
