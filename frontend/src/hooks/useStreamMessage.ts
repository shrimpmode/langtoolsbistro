import { useCallback, useEffect, useRef, useState } from "react";
import { streamMessage } from "../lib/api";
import type { Message, ToolArtifact } from "../lib/types";

interface StreamState {
  isStreaming: boolean;
  /**
   * Text the model wrote before calling a tool ("Let me check that for
   * you!"). Shown faded as a status line: the backend doesn't save it as
   * part of the reply, so showing it as the answer would make the text
   * change when the stream finishes.
   */
  statusText: string;
  /** Text since the last tool call: the part that becomes the saved reply. */
  answerText: string;
  /** Tools started so far this turn, in order. */
  tools: string[];
  /** Card data from tools that have finished, shown before the reply text. */
  cards: ToolArtifact[];
}

interface SendArgs {
  conversationId: string;
  content: string;
  onDone: (message: Message) => void;
  onError: (error: Error) => void;
}

const initialState: StreamState = {
  isStreaming: false,
  statusText: "",
  answerText: "",
  tools: [],
  cards: [],
};

export function useStreamMessage() {
  const [state, setState] = useState<StreamState>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(({ conversationId, content, onDone, onError }: SendArgs) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ ...initialState, isStreaming: true });

    streamMessage(
      conversationId,
      content,
      {
        onToken: (text) => setState((prev) => ({ ...prev, answerText: prev.answerText + text })),
        onToolStart: (tool) =>
          setState((prev) => ({
            ...prev,
            tools: [...prev.tools, tool],
            // Whatever was written before this tool call was a preamble,
            // not the answer, so move it to the status line.
            statusText: [prev.statusText, prev.answerText.trim()].filter(Boolean).join(" "),
            answerText: "",
          })),
        onToolEnd: (_tool, artifact) => {
          if (artifact) setState((prev) => ({ ...prev, cards: [...prev.cards, artifact] }));
        },
        onDone: (message) => {
          setState(initialState);
          onDone(message);
        },
      },
      controller.signal
    ).catch((err: Error) => {
      if (controller.signal.aborted) return;
      setState(initialState);
      onError(err);
    });
  }, []);

  return { ...state, send };
}
