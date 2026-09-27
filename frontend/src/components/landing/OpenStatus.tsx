import { formatClock } from "../../lib/formatTime";
import type { RestaurantDetails } from "../../lib/types";

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/** "Open now · until 10 PM", "Opens today at 5 PM", "Closed today · opens Tuesday at 5 PM" */
export function statusText(restaurant: RestaurantDetails): string {
  const { status, today, hours } = restaurant;
  if (status.open_now && status.closes_at) {
    return `Open now · until ${formatClock(status.closes_at)}`;
  }
  const next = status.next_opening;
  if (!next) return "Closed";

  const at = formatClock(next.time);
  if (next.weekday === today) return `Opens today at ${at}`;

  const daysAhead = (WEEKDAYS.indexOf(next.weekday) - WEEKDAYS.indexOf(today) + 7) % 7;
  const when = daysAhead === 1 ? "tomorrow" : next.weekday;
  const closedAllDay = hours.find((h) => h.weekday === today)?.open === null;
  return `${closedAllDay ? "Closed today" : "Closed now"} · opens ${when} at ${at}`;
}

export default function OpenStatus({ restaurant }: { restaurant: RestaurantDetails | undefined }) {
  if (!restaurant) {
    return <p className="h-6 text-sm text-muted">Checking today's hours…</p>;
  }
  const open = restaurant.status.open_now;
  return (
    <p className="inline-flex items-center gap-2 rounded-full border border-rule bg-white/70 px-3 py-1 text-sm font-medium">
      <span
        className={`h-2 w-2 rounded-full ${open ? "bg-olive" : "bg-tomato"}`}
        aria-hidden="true"
      />
      {statusText(restaurant)}
    </p>
  );
}
