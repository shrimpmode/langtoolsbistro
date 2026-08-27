import { useMenu } from "../hooks/useMenu";
import type { MenuCategory, MenuItem } from "../lib/types";

const CATEGORY_LABELS: Record<MenuCategory, string> = {
  appetizer: "Appetizers",
  main: "Mains",
  dessert: "Desserts",
  drink: "Drinks",
};

const CATEGORY_ORDER: MenuCategory[] = [
  "appetizer",
  "main",
  "dessert",
  "drink",
];

export default function MenuPanel() {
  const { data: menu, isLoading, error } = useMenu();

  const grouped = (menu ?? []).reduce<Partial<Record<MenuCategory, MenuItem[]>>>(
    (acc, item) => {
      (acc[item.category] ??= []).push(item);
      return acc;
    },
    {}
  );

  return (
    <div className="h-full overflow-y-auto p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-stone-500">
        Menu
      </h2>

      {error ? (
        <p className="text-sm text-red-600">
          Couldn't load menu: {error.message}
        </p>
      ) : isLoading ? (
        <p className="text-sm text-stone-400">Loading…</p>
      ) : (
        <div className="space-y-5">
          {CATEGORY_ORDER.filter((c) => grouped[c]?.length).map((category) => (
            <div key={category}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
                {CATEGORY_LABELS[category] || category}
              </h3>
              <ul className="space-y-2">
                {grouped[category]?.map((item) => (
                  <li
                    key={item.id}
                    className={`rounded-lg border border-stone-200 bg-white p-2 ${
                      item.is_available ? "" : "opacity-50"
                    }`}
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-medium text-stone-800">
                        {item.name}
                      </span>
                      <span className="whitespace-nowrap text-sm text-stone-600">
                        ${item.price}
                      </span>
                    </div>
                    {item.description ? (
                      <p className="mt-0.5 text-xs text-stone-500">
                        {item.description}
                      </p>
                    ) : null}
                    {!item.is_available ? (
                      <p className="mt-0.5 text-xs italic text-stone-400">
                        Currently unavailable
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
