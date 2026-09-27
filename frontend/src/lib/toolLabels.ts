// Guest-facing names for the agent's tools. The raw names (check_reservation,
// ...) are implementation details a guest shouldn't have to decode.
//
// "done" labels describe the attempt, not the outcome: a booking request can
// still be refused (no email, bad date), and the reply explains why.
const LABELS: Record<string, { active: string; done: string }> = {
  list_menu: { active: "Checking the menu…", done: "Checked the menu" },
  create_reservation: { active: "Booking your table…", done: "Booking request" },
  check_reservation: { active: "Looking up bookings…", done: "Looked up bookings" },
};

export function toolLabel(name: string, state: "active" | "done"): string {
  return LABELS[name]?.[state] ?? name;
}
