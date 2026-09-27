import { useQuery } from "@tanstack/react-query";
import { getMockInbox } from "../lib/api";
import type { MockEmail } from "../lib/types";

interface MockInboxProps {
  /**
   * Set while the guest is waiting for a sign-in code. The inbox then
   * checks for new mail every few seconds and offers to fill codes in.
   * Otherwise it loads once and doesn't poll.
   */
  onUseCode?: (code: string) => void;
}

/**
 * Shows emails from the backend's mock email service - nothing is really
 * sent in development. Hidden entirely when the endpoint isn't available.
 */
export default function MockInbox({ onUseCode }: MockInboxProps) {
  const { data: emails, isError } = useQuery<MockEmail[]>({
    queryKey: ["mock-inbox"],
    queryFn: getMockInbox,
    refetchInterval: onUseCode ? 3000 : false,
    retry: false,
  });

  if (isError || !emails) return null;

  return (
    <div className="rounded-md border border-dashed border-stone-300 bg-stone-50 p-2">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-stone-500">
        Mock inbox · development only
      </p>
      {emails.length === 0 ? (
        <p className="text-xs text-stone-400">No emails yet. Sign-in codes show up here.</p>
      ) : (
        <ul className="space-y-1.5">
          {emails.slice(0, 3).map((email) => {
            const code = email.subject.match(/\b\d{6}\b/)?.[0];
            return (
              <li key={email.id} className="rounded bg-white p-2 text-xs shadow-sm">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="truncate text-stone-500">To: {email.to}</span>
                  <time className="shrink-0 text-stone-400" dateTime={email.sent_at}>
                    {new Date(email.sent_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </time>
                </div>
                <p className="mt-0.5 font-medium text-stone-800">{email.subject}</p>
                {code && onUseCode ? (
                  <button
                    onClick={() => onUseCode(code)}
                    className="mt-1 text-amber-700 hover:underline"
                  >
                    Fill in {code}
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
