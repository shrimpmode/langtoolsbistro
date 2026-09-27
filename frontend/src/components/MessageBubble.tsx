interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  isError?: boolean;
}

export default function MessageBubble({
  role,
  content,
  toolsUsed,
  isError,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2 shadow-sm ${
          isError
            ? "bg-red-50 text-red-800 border border-red-200"
            : isUser
              ? "bg-amber-700 text-white"
              : "bg-white text-stone-800 border border-stone-200"
        }`}
      >
        {!isUser && toolsUsed?.length ? (
          <div className="mb-1 flex flex-wrap gap-1">
            {toolsUsed.map((tool, i) => (
              <span
                key={i}
                className="inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
              >
                🔧 {tool}
              </span>
            ))}
          </div>
        ) : null}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
      </div>
    </div>
  );
}
