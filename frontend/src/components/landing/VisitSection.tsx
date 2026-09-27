import { formatClock } from "../../lib/formatTime";
import type { RestaurantDetails } from "../../lib/types";

export default function VisitSection({
  docked,
  restaurant,
  onBook,
}: {
  /** Chat docked beside the page: two columns only on wider windows. */
  docked: boolean;
  restaurant: RestaurantDetails | undefined;
  onBook: () => void;
}) {
  return (
    <section id="visit" className="scroll-mt-20 border-t border-rule bg-olive-soft/60">
      <div
        className={`mx-auto grid max-w-5xl gap-12 px-5 py-16 md:py-20 ${
          docked ? "xl:grid-cols-2" : "md:grid-cols-2"
        }`}
      >
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-olive">Visit</p>
          <h2 className="mt-2 font-display text-4xl md:text-5xl">Find us</h2>
          <p className="mt-6 text-xl">{restaurant?.address ?? " "}</p>
          <p className="mt-3 max-w-prose text-muted">{restaurant?.walk_ins}</p>
          <button
            type="button"
            onClick={onBook}
            className="mt-8 rounded-full bg-tomato px-6 py-3 font-semibold text-white hover:bg-tomato-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tomato"
          >
            Book a table
          </button>
        </div>

        <div>
          <h3 className="font-display text-2xl text-olive">Opening hours</h3>
          {restaurant ? (
            <dl className="mt-4 divide-y divide-rule border-y border-rule">
              {restaurant.hours.map((day) => {
                const isToday = day.weekday === restaurant.today;
                return (
                  <div
                    key={day.weekday}
                    className={`flex items-center justify-between gap-4 px-3 py-2.5 ${
                      isToday ? "bg-white font-semibold" : ""
                    }`}
                  >
                    <dt className="flex items-center gap-2">
                      {day.weekday}
                      {isToday ? (
                        <span className="rounded-full bg-olive px-2 py-0.5 text-xs font-semibold text-white">
                          Today
                        </span>
                      ) : null}
                    </dt>
                    <dd className={`tabular-nums ${day.open ? "" : "text-muted"}`}>
                      {day.open && day.close
                        ? `${formatClock(day.open)} – ${formatClock(day.close)}`
                        : "Closed"}
                    </dd>
                  </div>
                );
              })}
            </dl>
          ) : (
            <p className="mt-4 text-muted">Loading our hours…</p>
          )}
        </div>
      </div>
    </section>
  );
}
