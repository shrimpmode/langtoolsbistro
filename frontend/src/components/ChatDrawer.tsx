import { useEffect, type ReactNode } from "react";
import type { Conversation } from "../lib/types";
import ChatPanel from "./ChatPanel";
import GuestSignIn from "./GuestSignIn";

interface ChatDrawerProps {
  open: boolean;
  onClose: () => void;
  /** Bumped by "New chat" to remount the chat and sign-in with fresh state. */
  chatKey: number;
  ready: boolean;
  loadError: Error | null;
  conversation: Conversation | null;
  onNewChat: () => void;
  signInOpen: boolean;
  onSignInOpenChange: (open: boolean) => void;
  pendingMessage: string | null;
  onPendingMessageSent: () => void;
}

/**
 * The chat, sliding in over the right of the page (full screen on phones).
 *
 * It stays mounted while closed - hidden with `invisible`, which also takes
 * it out of the tab order - so closing it mid-reply doesn't cut the stream
 * off, and reopening shows the conversation exactly as it was.
 */
export default function ChatDrawer({
  open,
  onClose,
  chatKey,
  ready,
  loadError,
  conversation,
  onNewChat,
  signInOpen,
  onSignInOpenChange,
  pendingMessage,
  onPendingMessageSent,
}: ChatDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);

  useEffect(() => {
    if (open) document.getElementById("chat-input")?.focus();
  }, [open]);

  const signedIn = !!conversation?.guest_email;

  let banner: ReactNode;
  if (loadError) {
    banner = (
      <p className="border-b border-red-200 bg-red-50 px-4 py-2 text-xs text-red-700">
        Couldn't load your conversation. Check your connection and refresh the page.
      </p>
    );
  } else if (!ready) {
    banner = null;
  } else if (signedIn || signInOpen) {
    banner = (
      <div className="relative">
        {!signedIn ? (
          <button
            type="button"
            onClick={() => onSignInOpenChange(false)}
            className="absolute right-4 top-4 text-xs text-stone-500 hover:text-stone-800"
          >
            Hide
          </button>
        ) : null}
        <GuestSignIn key={chatKey} conversation={conversation} />
      </div>
    );
  } else {
    banner = (
      <div className="flex items-center justify-between gap-2 border-b border-stone-200 bg-white px-4 py-2 text-xs text-stone-500">
        <span>Sign in to see your bookings without a code.</span>
        <button
          type="button"
          onClick={() => onSignInOpenChange(true)}
          className="font-semibold text-amber-700 hover:underline"
        >
          Sign in
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Phones only: dims the page behind the full-screen chat. */}
      <div
        aria-hidden="true"
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-ink/30 transition-opacity motion-reduce:transition-none md:hidden ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        role="dialog"
        aria-label="Chat with the restaurant"
        // Phones: full screen. Tablets: a panel over the page. From lg up:
        // docked to the right half, with the landing page reflowing into
        // the left half (see LandingPage's `docked`).
        className={`fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col bg-stone-100 font-sans shadow-2xl transition-[transform,visibility] duration-300 motion-reduce:transition-none lg:w-1/2 lg:max-w-none lg:border-l lg:border-stone-200 lg:shadow-none ${
          open ? "visible translate-x-0" : "invisible translate-x-full"
        }`}
      >
        <div className="min-h-0 flex-1">
          <ChatPanel
            key={chatKey}
            ready={ready}
            conversationId={conversation?.id ?? null}
            onNewChat={onNewChat}
            onClose={onClose}
            banner={banner}
            pendingMessage={pendingMessage}
            onPendingMessageSent={onPendingMessageSent}
          />
        </div>
      </aside>
    </>
  );
}
