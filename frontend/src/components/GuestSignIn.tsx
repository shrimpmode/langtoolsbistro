import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useEnsureConversation } from "../hooks/useConversation";
import { ApiError, logout, requestLoginCode, verifyLoginCode } from "../lib/api";
import type { Conversation } from "../lib/types";
import MockInbox from "./MockInbox";

interface GuestSignInProps {
  /** Null until the guest's first message or sign-in creates one. */
  conversation: Conversation | null;
}

type Step = "email" | "code";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.detail) return err.detail;
    if (err.status === 400) return "Check the email address and try again.";
  }
  return "Something went wrong. Try again.";
}

export default function GuestSignIn({ conversation }: GuestSignInProps) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ensureConversation = useEnsureConversation();
  const signedInEmail = conversation?.guest_email ?? "";

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const sendCode = () =>
    run(async () => {
      // Sign-in belongs to a conversation, so this is the other action
      // (besides sending a message) that creates one.
      const { id } = await ensureConversation();
      await requestLoginCode(id, email);
      setCode("");
      setStep("code");
      queryClient.invalidateQueries({ queryKey: ["mock-inbox"] });
    });

  const verify = () =>
    run(async () => {
      const { id } = await ensureConversation();
      const updated = await verifyLoginCode(id, email, code);
      queryClient.setQueryData(["conversation"], updated);
      setStep("email");
      setCode("");
    });

  const signOut = () =>
    run(async () => {
      if (!conversation) return;
      const updated = await logout(conversation.id);
      queryClient.setQueryData(["conversation"], updated);
    });

  return (
    <section className="space-y-3 border-b border-stone-200 p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-stone-500">
        Your bookings
      </h2>

      {signedInEmail ? (
        <div className="space-y-2">
          <p className="text-sm text-stone-700">
            Signed in as{" "}
            <span className="font-medium text-stone-900">{signedInEmail}</span>.
            Ask the assistant about your bookings, no code needed.
          </p>
          <button
            onClick={signOut}
            disabled={busy}
            className="text-xs font-medium text-amber-700 hover:underline disabled:opacity-50"
          >
            Sign out
          </button>
        </div>
      ) : step === "email" ? (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            sendCode();
          }}
        >
          <p className="text-xs text-stone-500">
            Sign in to see your bookings without a confirmation code. We'll email you a
            6-digit code.
          </p>
          <label htmlFor="guest-email" className="sr-only">
            Email address
          </label>
          <input
            id="guest-email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-md border border-stone-300 px-3 py-1.5 text-sm focus:border-amber-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !email.trim()}
            className="w-full rounded-md bg-amber-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-stone-300"
          >
            {busy ? "Sending…" : "Email me a code"}
          </button>
        </form>
      ) : (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            verify();
          }}
        >
          <p className="text-xs text-stone-500">
            We sent a code to <span className="font-medium text-stone-700">{email}</span>. It
            expires in 10 minutes.
          </p>
          <label htmlFor="guest-code" className="sr-only">
            6-digit code
          </label>
          <input
            id="guest-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            placeholder="123456"
            className="w-full rounded-md border border-stone-300 px-3 py-1.5 font-mono text-sm tracking-widest focus:border-amber-500 focus:outline-none"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy || code.length !== 6}
              className="flex-1 rounded-md bg-amber-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-stone-300"
            >
              {busy ? "Checking…" : "Sign in"}
            </button>
            <button
              type="button"
              onClick={() => {
                setStep("email");
                setError(null);
              }}
              className="rounded-md border border-stone-300 px-3 py-1.5 text-sm text-stone-600 hover:border-amber-500"
            >
              Back
            </button>
          </div>
        </form>
      )}

      {error ? <p className="text-xs text-red-600">{error}</p> : null}

      {!signedInEmail ? (
        <MockInbox onUseCode={step === "code" ? setCode : undefined} />
      ) : null}
    </section>
  );
}
