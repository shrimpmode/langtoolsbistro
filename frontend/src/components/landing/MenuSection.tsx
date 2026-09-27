import { useMenu } from "../../hooks/useMenu";
import type { MenuCategory, MenuItem } from "../../lib/types";

const CATEGORY_LABELS: Record<MenuCategory, string> = {
  appetizer: "Antipasti",
  main: "Mains",
  dessert: "Dolci",
  drink: "To drink",
};
const CATEGORY_ORDER: MenuCategory[] = ["appetizer", "main", "dessert", "drink"];

/** "14.00" -> "14", "7.50" -> "7.50", the way printed menus show prices. */
function formatPrice(price: string): string {
  return price.endsWith(".00") ? price.slice(0, -3) : price;
}

function Dish({ item }: { item: MenuItem }) {
  return (
    <li className={item.is_available ? "" : "opacity-50"}>
      <div className="flex items-baseline gap-2">
        <span className="font-semibold">{item.name}</span>
        {/* Dotted leader between name and price, as on a printed menu. */}
        <span aria-hidden="true" className="flex-1 -translate-y-1 border-b border-dotted border-muted/50" />
        <span className="tabular-nums">{formatPrice(item.price)}</span>
      </div>
      {item.description ? <p className="mt-0.5 text-sm text-muted">{item.description}</p> : null}
      {!item.is_available ? <p className="text-xs italic text-muted">Not available today</p> : null}
    </li>
  );
}

export default function MenuSection({ onAsk }: { onAsk: (message: string) => void }) {
  const { data: menu, isLoading, error } = useMenu();

  const byCategory = (menu ?? []).reduce<Partial<Record<MenuCategory, MenuItem[]>>>((acc, item) => {
    (acc[item.category] ??= []).push(item);
    return acc;
  }, {});

  return (
    <section id="menu" className="scroll-mt-20 border-t border-rule">
      <div className="mx-auto max-w-5xl px-5 py-16 md:py-20">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-olive">Menu</p>
        <h2 className="mt-2 font-display text-4xl md:text-5xl">What we're cooking</h2>
        <p className="mt-3 max-w-prose text-muted">Prices in US dollars.</p>

        {error ? (
          <p className="mt-10 text-tomato">We couldn't load the menu just now. Try refreshing the page.</p>
        ) : isLoading ? (
          <p className="mt-10 text-muted">Loading the menu…</p>
        ) : (
          <div className="mt-10 grid gap-x-16 gap-y-12 md:grid-cols-2">
            {CATEGORY_ORDER.filter((c) => byCategory[c]?.length).map((category) => (
              <div key={category}>
                <h3 className="border-b border-rule pb-2 font-display text-2xl text-olive">
                  {CATEGORY_LABELS[category]}
                </h3>
                <ul className="mt-4 space-y-4">
                  {byCategory[category]!.map((item) => (
                    <Dish key={item.id} item={item} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        <p className="mt-12 text-muted">
          Questions about a dish or an allergy?{" "}
          <button
            type="button"
            onClick={() => onAsk("I have a question about the menu.")}
            className="font-semibold text-tomato underline decoration-tomato/40 underline-offset-4 hover:decoration-tomato"
          >
            Ask us in the chat
          </button>
        </p>
      </div>
    </section>
  );
}
