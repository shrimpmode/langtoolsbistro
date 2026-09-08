import { useCallback, useEffect, useRef, useState } from "react";
import { streamMessage } from "../lib/api";
import type { Message } from "../lib/types";

interface StreamState {
  isStreaming: boolean;
  streamedText: string;
  streamingTool: string | null;
}

interface SendArgs {
  conversationId: string;
  content: string;
  onDone: (message: Message) => void;
  onError: (error: Error) => void;
}

const initialState: StreamState = {
  isStreaming: false,
  streamedText: "",
  streamingTool: null,
};

export function useStreamMessage() {
  const [state, setState] = useState<StreamState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(
    ({ conversationId, content, onDone, onError }: SendArgs) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState({ isStreaming: true, streamedText: "", streamingTool: null });

      streamMessage(
        conversationId,
        content,
        {
          onToken: (text) =>
            setState((prev) => ({ ...prev, streamedText: prev.streamedText + text })),
          onToolStart: (tool) =>
            setState((prev) => ({
              ...prev,
              streamingTool: tool,
              // Visually separate a spoken preamble ("I'll check that for
              // you!") from whatever text follows the tool call - the
              // backend only strips the preamble from the persisted reply,
              // not from what's shown live while streaming.
              streamedText: prev.streamedText ? prev.streamedText + "\n" : prev.streamedText,
            })),
          onDone: (message) => {
            setState(initialState);
            onDone(message);
          },
          onError: (err) => {
            setState(initialState);
            onError(err);
          },
        },
        controller.signal
      ).catch((err: Error) => {
        if (controller.signal.aborted) return;
        setState(initialState);
        onError(err);
      });
    },
    []
  );

  return { ...state, send };
}
