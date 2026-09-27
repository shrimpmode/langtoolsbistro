import { useCallback, useState } from "react";
import { useConversation, useForgetConversation } from "./hooks/useConversation";
import ChatDrawer from "./components/ChatDrawer";
import LandingPage from "./components/landing/LandingPage";

export default function App() {
  const {
    data: conversation,
    isSuccess: conversationLoaded,
    error: conversationError,
  } = useConversation();
  const forgetConversation = useForgetConversation();

  const [chatOpen, setChatOpen] = useState(false);
  const [signInOpen, setSignInOpen] = useState(false);
  // A line the landing page wants sent as the guest's next message.
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  // Bumped by "New chat" to remount the chat with fresh state. Not the
  // conversation id: that changes from null to a real id when the first
  // message creates the conversation, and remounting then would drop the
  // message being sent.
  const [chatKey, setChatKey] = useState(0);

  const openChat = useCallback((message?: string) => {
    setChatOpen(true);
    if (message) setPendingMessage(message);
  }, []);

  const closeChat = useCallback(() => setChatOpen(false), []);

  function findBooking() {
    setSignInOpen(true);
    setChatOpen(true);
  }

  function startNewChat() {
    forgetConversation();
    setSignInOpen(false);
    setChatKey((key) => key + 1);
  }

  return (
    <>
      <LandingPage onOpenChat={openChat} onFindBooking={findBooking} />
      <ChatDrawer
        open={chatOpen}
        onClose={closeChat}
        chatKey={chatKey}
        ready={conversationLoaded}
        loadError={conversationError}
        conversation={conversation ?? null}
        onNewChat={startNewChat}
        signInOpen={signInOpen}
        onSignInOpenChange={setSignInOpen}
        pendingMessage={pendingMessage}
        onPendingMessageSent={() => setPendingMessage(null)}
      />
    </>
  );
}
