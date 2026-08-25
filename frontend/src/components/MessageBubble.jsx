export default function MessageBubble({ role, content, toolUsed, isError }) {
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
        {!isUser && toolUsed ? (
          <span className="mb-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
            🔧 {toolUsed}
          </span>
        ) : null}
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
      </div>
    </div>
  );
}
