import { useRef, useState, useEffect } from "react";
import { sendMessage } from "../lib/api.js";
import MessageBubble from "./MessageBubble.jsx";

const SUGGESTIONS = [
  "What's on the menu?",
  "Book a table for 4 tonight at 7pm under Alex",
  "Do you have a table booked for Alex?",
  "What time do you close?",
];

export default function ChatPanel({ conversationId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  async function handleSend(text) {
    const content = text.trim();
    if (!content || !conversationId || isSending) return;

    setMessages((prev) => [...prev, { role: "user", content }]);
    setInput("");
    setIsSending(true);

    try {
      const reply = await sendMessage(conversationId, content);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: reply.content,
          toolUsed: reply.tool_used,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Something went wrong talking to the assistant: ${err.message}`,
          isError: true,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="mx-auto max-w-sm space-y-3 pt-8 text-center">
            <p className="text-sm text-stone-500">
              Say hello, ask about the menu, or book a table.
            </p>
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
              toolUsed={m.toolUsed}
              isError={m.isError}
            />
          ))
        )}
        {isSending ? (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-stone-200 bg-white px-4 py-2 text-sm text-stone-400 shadow-sm">
              thinking…
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
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!conversationId}
          placeholder={
            conversationId ? "Type a message…" : "Starting conversation…"
          }
          className="flex-1 rounded-full border border-stone-300 px-4 py-2 text-sm focus:border-amber-500 focus:outline-none disabled:bg-stone-100"
        />
        <button
          type="submit"
          disabled={!conversationId || isSending || !input.trim()}
          className="rounded-full bg-amber-700 px-5 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-stone-300"
        >
          Send
        </button>
      </form>
    </div>
  );
}
