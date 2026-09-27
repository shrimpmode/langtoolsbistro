import { memo } from "react";
import { toolLabel } from "../lib/toolLabels";
import type { ToolArtifact } from "../lib/types";
import BookingCards from "./BookingCard";
import Markdown from "./Markdown";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  cards?: ToolArtifact[];
  isError?: boolean;
}

export function ToolChip({ label, active = false }: { label: string; active?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
      <span
        className={`h-1.5 w-1.5 rounded-full bg-amber-600 ${active ? "animate-pulse" : ""}`}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}

// memo: while a reply streams, ChatPanel re-renders on every token (and on
// every keystroke in the input). Without memo, every earlier message would
// re-render and re-parse its Markdown each time. Saved messages keep the
// same props, so memo lets React skip them.
const MessageBubble = memo(function MessageBubble({
  role,
  content,
  toolsUsed,
  cards,
  isError,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 shadow-sm ${
          isError
            ? "border border-red-200 bg-red-50 text-red-800"
            : isUser
              ? "bg-amber-700 text-white"
              : "border border-stone-200 bg-white text-stone-800"
        }`}
      >
        {!isUser && toolsUsed?.length ? (
          <div className="mb-1.5 flex flex-wrap gap-1">
            {toolsUsed.map((tool, i) => (
              <ToolChip key={i} label={toolLabel(tool, "done")} />
            ))}
          </div>
        ) : null}
        {!isUser && cards?.length ? <CardList cards={cards} /> : null}
        {isUser || isError ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
        ) : (
          <div className="text-sm leading-relaxed">
            <Markdown>{content}</Markdown>
          </div>
        )}
      </div>
    </div>
  );
});

export default MessageBubble;

/** Booking cards, shown above the reply text both while streaming and after. */
export function CardList({ cards }: { cards: ToolArtifact[] }) {
  return (
    <div className="mb-2 space-y-2">
      {cards.map((artifact, i) => (
        <BookingCards key={i} artifact={artifact} />
      ))}
    </div>
  );
}
