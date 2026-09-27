import { useRef, useState, useEffect } from "react";
import { useStartNewConversation } from "../hooks/useConversation";
import { useStreamMessage } from "../hooks/useStreamMessage";
import { listMessages } from "../lib/api";
import { toolLabel } from "../lib/toolLabels";
import Markdown from "./Markdown";
import MessageBubble, { CardList, ToolChip } from "./MessageBubble";
import type { ChatBubble, Message, ToolArtifact } from "../lib/types";

const SUGGESTIONS = [
  "What's on the menu?",
  "Book a table for 4 tonight at 7pm under Alex, alex@example.com",
  "Look up my booking",
  "What time do you close?",
];

type HistoryState = "loading" | "ready" | "error";

function toBubble(message: Message): ChatBubble {
  return {
    role: message.role,
    content: message.content,
    toolsUsed: message.tool_calls.map((call) => call.name),
    cards: message.tool_calls
      .map((call) => call.artifact)
      .filter((artifact): artifact is ToolArtifact => !!artifact),
  };
}

interface ChatPanelProps {
  conversationId: string | null;
}

export default function ChatPanel({ conversationId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [historyState, setHistoryState] = useState<HistoryState>("loading");
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const { send, isStreaming, statusText, answerText, tools, cards } = useStreamMessage();
  const startNewConversation = useStartNewConversation();

  // Load the saved history whenever the conversation changes: on first
  // load, after a page reload, and after "New chat".
  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;
    setMessages([]);
    setHistoryState("loading");
    listMessages(conversationId)
      .then((history) => {
        if (cancelled) return;
        setMessages(history.map(toBubble));
        setHistoryState("ready");
      })
      .catch(() => {
        if (!cancelled) setHistoryState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, answerText, statusText]);

  const canSend = !!conversationId && historyState !== "loading" && !isStreaming;

  function handleSend(text: string) {
    const content = text.trim();
    if (!content || !conversationId || !canSend) return;

    setMessages((prev) => [...prev, { role: "user", content }]);
    setInput("");

    send({
      conversationId,
      content,
      onDone: (reply) => {
        setMessages((prev) => [...prev, toBubble(reply)]);
      },
      onError: (err) => {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Something went wrong talking to the assistant: ${err.message}`,
            isError: true,
          },
        ]);
      },
    });
  }

  const lastTool = tools[tools.length - 1];
  const toolIsRunning = !!lastTool && !answerText;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-stone-200 bg-white px-4 py-2">
        <span className="text-xs text-stone-500">
          {historyState === "error" ? "Couldn't load earlier messages." : "Chat"}
        </span>
        <button
          onClick={() => startNewConversation()}
          disabled={isStreaming || messages.length === 0}
          title="Starts a new conversation. You'll be signed out."
          className="rounded-full border border-stone-300 px-3 py-0.5 text-xs text-stone-600 hover:border-amber-500 hover:text-amber-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          New chat
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {historyState === "loading" ? (
          <p className="pt-8 text-center text-sm text-stone-400">Loading your conversation…</p>
        ) : messages.length === 0 ? (
          <div className="mx-auto max-w-sm space-y-3 pt-8 text-center">
            <p className="text-sm text-stone-500">Say hello, ask about the menu, or book a table.</p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className="rounded-full border border-stone-300 bg-white px-3 py-1 text-xs text-stone-600 hover:border-amber-500 hover:text-amber-700"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <MessageBubble
              key={i}
              role={m.role}
              content={m.content}
              toolsUsed={m.toolsUsed}
              cards={m.cards}
              isError={m.isError}
            />
          ))
        )}

        {isStreaming ? (
          <div className="flex justify-start">
            <div className="max-w-[75%] space-y-1.5 rounded-2xl border border-stone-200 bg-white px-4 py-2 shadow-sm">
              {statusText ? <p className="text-xs italic text-stone-400">{statusText}</p> : null}
              {tools.length ? (
                <div className="flex flex-wrap gap-1">
                  {tools.map((tool, i) => {
                    const active = toolIsRunning && i === tools.length - 1;
                    return (
                      <ToolChip
                        key={i}
                        label={toolLabel(tool, active ? "active" : "done")}
                        active={active}
                      />
                    );
                  })}
                </div>
              ) : null}
              {cards.length ? <CardList cards={cards} /> : null}
              {answerText ? (
                <div className="text-sm leading-relaxed text-stone-800">
                  <Markdown>{answerText}</Markdown>
                </div>
              ) : !toolIsRunning ? (
                <p className="text-sm text-stone-400">Thinking…</p>
              ) : null}
            </div>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="flex gap-2 border-t border-stone-200 bg-white p-3"
      >
        <label htmlFor="chat-input" className="sr-only">
          Message
        </label>
        <input
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!conversationId}
          placeholder={conversationId ? "Type a message…" : "Starting conversation…"}
          className="flex-1 rounded-full border border-stone-300 px-4 py-2 text-sm focus:border-amber-500 focus:outline-none disabled:bg-stone-100"
        />
        <button
          type="submit"
          disabled={!canSend || !input.trim()}
          className="rounded-full bg-amber-700 px-5 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-stone-300"
        >
          Send
        </button>
      </form>
    </div>
  );
}
