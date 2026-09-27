import { useState } from "react";
import type { ReservationCardData, ToolArtifact } from "../lib/types";

// Rendered from the tool's own structured output (ToolMessage.artifact), not
// parsed out of the model's prose - so the code shown here is exactly what's
// in the database, whatever wording the model chose.

function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  // Built from parts so it stays the same calendar day in every time zone.
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatTime(hhmm: string): string {
  const [hours, minutes] = hhmm.split(":").map(Number);
  return new Date(2000, 0, 1, hours, minutes).toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function CopyCodeButton({ code }: { code: string }) {
  const [label, setLabel] = useState("Copy");
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard
          .writeText(code)
          .then(() => setLabel("Copied"))
          .catch(() => setLabel("Couldn't copy"))
          .finally(() => setTimeout(() => setLabel("Copy"), 1500));
      }}
      className="rounded-md border border-stone-300 px-2 py-0.5 text-xs text-stone-600 hover:border-amber-500 hover:text-amber-700"
    >
      {label}
    </button>
  );
}

function ReservationCard({ reservation, title }: { reservation: ReservationCardData; title: string }) {
  const cancelled = reservation.status === "cancelled";
  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-stone-500">{title}</span>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
            cancelled ? "bg-stone-200 text-stone-600" : "bg-emerald-100 text-emerald-800"
          }`}
        >
          {cancelled ? "Cancelled" : "Confirmed"}
        </span>
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] text-stone-500">Confirmation code</p>
          <p className="font-mono text-lg font-semibold tracking-widest text-stone-900">
            {reservation.code}
          </p>
        </div>
        <CopyCodeButton code={reservation.code} />
      </div>

      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <div>
          <dt className="text-[11px] text-stone-500">Date</dt>
          <dd className="text-stone-800">{formatDate(reservation.date)}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-stone-500">Time</dt>
          <dd className="text-stone-800">{formatTime(reservation.time)}</dd>
        </div>
        <div>
          <dt className="text-[11px] text-stone-500">Party</dt>
          <dd className="text-stone-800">
            {reservation.party_size} {reservation.party_size === 1 ? "guest" : "guests"}
          </dd>
        </div>
        <div>
          <dt className="text-[11px] text-stone-500">Name</dt>
          <dd className="truncate text-stone-800">{reservation.customer_name}</dd>
        </div>
      </dl>
    </div>
  );
}

export default function BookingCards({ artifact }: { artifact: ToolArtifact }) {
  const title = artifact.kind === "reservation_created" ? "Booking confirmed" : "Your booking";
  return (
    <div className="space-y-2">
      {artifact.reservations.map((reservation) => (
        <ReservationCard key={reservation.code} reservation={reservation} title={title} />
      ))}
    </div>
  );
}
