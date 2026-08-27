import { useConversation } from "./hooks/useConversation";
import ChatPanel from "./components/ChatPanel";
import MenuPanel from "./components/MenuPanel";

export default function App() {
  const { data: conversation, error: conversationError } = useConversation();
  const conversationId = conversation?.id ?? null;

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b border-stone-200 bg-white px-6 py-4 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-800">
          🍝 Trattoria Orchai
        </h1>
        <p className="text-xs text-stone-500">
          Front-of-house chat, backed by a LangChain tool-calling agent.
        </p>
      </header>

      {conversationError ? (
        <div className="m-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Couldn't start a conversation: {conversationError.message}
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[2fr_1fr]">
          <div className="min-h-0 border-r border-stone-200">
            <ChatPanel conversationId={conversationId} />
          </div>
          <div className="min-h-0 border-t border-stone-200 md:border-t-0">
            <MenuPanel />
          </div>
        </div>
      )}
    </div>
  );
}
