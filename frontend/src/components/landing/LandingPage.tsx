import { useState } from "react";
import { useRestaurant } from "../../hooks/useRestaurant";
import Gingham from "./Gingham";
import MenuSection from "./MenuSection";
import OpenStatus from "./OpenStatus";
import VisitSection from "./VisitSection";

interface LandingPageProps {
  /** Opens the chat; with a message, sends it as the guest's first line. */
  onOpenChat: (message?: string) => void;
  /** Opens the chat with the sign-in form showing. */
  onFindBooking: () => void;
}

const BOOK_MESSAGE = "I'd like to book a table.";

export default function LandingPage({ onOpenChat, onFindBooking }: LandingPageProps) {
  const { data: restaurant } = useRestaurant();
  const [question, setQuestion] = useState("");
  const name = restaurant?.name ?? "Trattoria Orchai";

  function ask(e: React.FormEvent) {
    e.preventDefault();
    const text = question.trim();
    if (!text) return;
    onOpenChat(text);
    setQuestion("");
  }

  const book = () => onOpenChat(BOOK_MESSAGE);

  return (
    // Bottom padding leaves room for the phone action bar.
    <div className="min-h-screen pb-20 md:pb-0">
      <header className="sticky top-0 z-20 border-b border-rule bg-linen/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-5 py-3">
          <a href="#top" className="font-display text-2xl leading-none">
            {name}
          </a>
          <nav className="flex items-center gap-6 text-sm font-semibold">
            <a href="#menu" className="hidden hover:text-tomato md:inline">
              Menu
            </a>
            <a href="#visit" className="hidden hover:text-tomato md:inline">
              Visit
            </a>
            <button type="button" onClick={onFindBooking} className="hidden hover:text-tomato md:inline">
              Find my booking
            </button>
            <button
              type="button"
              onClick={() => onOpenChat()}
              className="rounded-full border border-ink/20 px-4 py-1.5 hover:border-tomato hover:text-tomato"
            >
              Chat with us
            </button>
          </nav>
        </div>
        <Gingham />
      </header>

      <main id="top">
        <section className="mx-auto max-w-5xl px-5 pb-16 pt-14 md:pb-24 md:pt-20">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-olive">
            {restaurant?.address ?? " "}
          </p>
          <h1 className="mt-3 max-w-3xl text-balance font-display text-5xl leading-[1.05] md:text-7xl">
            {name}
          </h1>
          <p className="mt-4 max-w-xl text-lg text-muted md:text-xl">{restaurant?.tagline}</p>

          <div className="mt-6">
            <OpenStatus restaurant={restaurant} />
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={book}
              className="rounded-full bg-tomato px-6 py-3 font-semibold text-white hover:bg-tomato-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tomato"
            >
              Book a table
            </button>
            <a
              href="#menu"
              className="rounded-full border border-ink/25 px-6 py-3 font-semibold hover:border-ink"
            >
              See the menu
            </a>
          </div>

          <form onSubmit={ask} className="mt-10 max-w-xl">
            <label htmlFor="hero-question" className="text-sm font-semibold">
              Or ask us anything
            </label>
            <div className="mt-2 flex items-center gap-2 rounded-full border border-rule bg-white p-1.5 pl-5 shadow-sm focus-within:border-olive">
              <input
                id="hero-question"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Table for 4 on Friday?"
                autoComplete="off"
                className="min-w-0 flex-1 bg-transparent py-1.5 outline-none placeholder:text-muted/70"
              />
              <button
                type="submit"
                disabled={!question.trim()}
                className="rounded-full bg-olive px-4 py-2 text-sm font-semibold text-white hover:bg-olive-dark disabled:opacity-40"
              >
                Ask
              </button>
            </div>
            <p className="mt-2 text-sm text-muted">Our assistant answers right away and can book for you.</p>
          </form>
        </section>

        <MenuSection onAsk={onOpenChat} />
        <VisitSection restaurant={restaurant} onBook={book} />

        <section id="booking" className="scroll-mt-20 border-t border-rule">
          <div className="mx-auto max-w-5xl px-5 py-16 md:py-20">
            <h2 className="font-display text-3xl md:text-4xl">Already booked?</h2>
            <p className="mt-3 max-w-prose text-muted">
              Look up your booking with the confirmation code we gave you, or sign in with the email
              you booked with to see all your bookings.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => onOpenChat("I'd like to look up my booking.")}
                className="rounded-full border border-ink/25 px-5 py-2.5 font-semibold hover:border-ink"
              >
                Use my confirmation code
              </button>
              <button
                type="button"
                onClick={onFindBooking}
                className="rounded-full border border-ink/25 px-5 py-2.5 font-semibold hover:border-ink"
              >
                Sign in with email
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-rule">
        <Gingham className="opacity-60" />
        <div className="mx-auto flex max-w-5xl flex-wrap justify-between gap-2 px-5 py-8 text-sm text-muted">
          <span className="font-display text-lg text-ink">{name}</span>
          <span>{restaurant?.address}</span>
        </div>
      </footer>

      {/* Phones: the two main actions, always in reach. */}
      <div className="fixed inset-x-0 bottom-0 z-20 flex gap-2 border-t border-rule bg-linen/95 px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur md:hidden">
        <button
          type="button"
          onClick={book}
          className="flex-1 rounded-full bg-tomato py-3 font-semibold text-white"
        >
          Book a table
        </button>
        <button
          type="button"
          onClick={() => onOpenChat()}
          className="flex-1 rounded-full border border-ink/25 py-3 font-semibold"
        >
          Chat
        </button>
      </div>
    </div>
  );
}
