import { useState } from "react";
import { useConversation, useForgetConversation } from "./hooks/useConversation";
import ChatPanel from "./components/ChatPanel";
import GuestSignIn from "./components/GuestSignIn";
import MenuPanel from "./components/MenuPanel";

export default function App() {
  const {
    data: conversation,
    isSuccess: conversationLoaded,
    error: conversationError,
  } = useConversation();
  const forgetConversation = useForgetConversation();
  // Bumped by "New chat" to remount both panels with fresh state. Not the
  // conversation id: that changes from null to a real id when the first
  // message creates the conversation, and remounting then would drop the
  // message being sent.
  const [chatKey, setChatKey] = useState(0);

  function startNewChat() {
    forgetConversation();
    setChatKey((key) => key + 1);
  }

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
          Couldn't load your conversation: {conversationError.message}
        </div>
      ) : (
        <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[2fr_1fr]">
          <div className="min-h-0 border-r border-stone-200">
            <ChatPanel
              key={chatKey}
              ready={conversationLoaded}
              conversationId={conversation?.id ?? null}
              onNewChat={startNewChat}
            />
          </div>
          <div className="min-h-0 overflow-y-auto border-t border-stone-200 md:border-t-0">
            {conversationLoaded ? (
              <GuestSignIn key={chatKey} conversation={conversation ?? null} />
            ) : null}
            <MenuPanel />
          </div>
        </div>
      )}
    </div>
  );
}
