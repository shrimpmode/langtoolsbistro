import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useEnsureConversation } from "../hooks/useConversation";
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
  /** False while App is still loading the saved conversation, if any. */
  ready: boolean;
  /** Null until the first message (or a sign-in) creates the conversation. */
  conversationId: string | null;
  /**
   * Forgets the conversation and remounts this panel with fresh state
   * (App keys it on a "New chat" counter).
   */
  onNewChat: () => void;
  onClose: () => void;
  /** Shown under the header, e.g. the sign-in strip. */
  banner?: ReactNode;
  /**
   * A message the landing page wants sent ("I'd like to book a table.").
   * Sent as soon as the panel can send, then cleared via onPendingMessageSent.
   */
  pendingMessage: string | null;
  onPendingMessageSent: () => void;
}

export default function ChatPanel({
  ready,
  conversationId,
  onNewChat,
  onClose,
  banner,
  pendingMessage,
  onPendingMessageSent,
}: ChatPanelProps) {
  // Messages sent since this conversation was opened; earlier ones come
  // from the saved history below.
  const [sessionMessages, setSessionMessages] = useState<ChatBubble[]>([]);
  const [input, setInput] = useState("");
  // True while the first message is creating the conversation, before
  // streaming starts, so a second click can't send twice.
  const [starting, setStarting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { send, isStreaming, statusText, answerText, tools, cards } = useStreamMessage();
  const ensureConversation = useEnsureConversation();

  // Saved history: on first load, after a page reload, and after "New chat".
  const history = useQuery({
    queryKey: ["messages", conversationId],
    queryFn: () => listMessages(conversationId!),
    enabled: !!conversationId,
    staleTime: Infinity,
  });
  // Built once per fetch, not per render, so each bubble keeps the same
  // props and MessageBubble's memo can skip re-rendering it.
  const historyBubbles = useMemo(() => (history.data ?? []).map(toBubble), [history.data]);
  const messages = [...historyBubbles, ...sessionMessages];
  // A disabled query (no conversation yet) also reports isPending, so only
  // count it as loading when there's a conversation to load.
  const historyLoading = !ready || (!!conversationId && history.isPending);

  // Depends on the count, not the array: `messages` is a new array every
  // render, which would scroll on every keystroke.
  const messageCount = messages.length;
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messageCount, isStreaming, answerText, statusText, cards.length]);

  const canSend = !historyLoading && !isStreaming && !starting;

  // Waits for canSend, so a message from the landing page isn't lost while
  // history is loading or an earlier reply is still streaming.
  useEffect(() => {
    if (!pendingMessage || !canSend) return;
    onPendingMessageSent();
    handleSend(pendingMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- handleSend changes every render
  }, [pendingMessage, canSend]);

  function showError(message: string) {
    setSessionMessages((prev) => [...prev, { role: "assistant", content: message, isError: true }]);
  }

  async function handleSend(text: string) {
    const content = text.trim();
    if (!content || !canSend) return;

    setSessionMessages((prev) => [...prev, { role: "user", content }]);
    setInput("");

    // The conversation is created here, on the first message, rather than
    // when the page loads.
    setStarting(true);
    let id: string;
    try {
      id = (await ensureConversation()).id;
    } catch (err) {
      showError(`Couldn't start the conversation: ${(err as Error).message}`);
      return;
    } finally {
      setStarting(false);
    }

    send({
      conversationId: id,
      content,
      onDone: (reply) => {
        setSessionMessages((prev) => [...prev, toBubble(reply)]);
      },
      onError: (err) => showError(`Something went wrong talking to the assistant: ${err.message}`),
    });
  }

  const lastTool = tools[tools.length - 1];
  const toolIsRunning = !!lastTool && !answerText;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-stone-200 bg-white px-4 py-2">
        <span className="text-sm font-semibold text-stone-700">
          {history.isError ? "Couldn't load earlier messages." : "Chat with us"}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={onNewChat}
            disabled={isStreaming || starting || messages.length === 0}
            title="Starts a new conversation. You'll be signed out."
            className="rounded-full border border-stone-300 px-3 py-0.5 text-xs text-stone-600 hover:border-amber-500 hover:text-amber-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            New chat
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close chat"
            className="rounded-full px-2 py-0.5 text-lg leading-none text-stone-500 hover:bg-stone-100 hover:text-stone-800"
          >
            ×
          </button>
        </div>
      </div>
      {banner}

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {historyLoading ? (
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
          disabled={historyLoading}
          placeholder={historyLoading ? "Loading…" : "Type a message…"}
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
