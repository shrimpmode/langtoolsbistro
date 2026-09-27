/** A thin red-check tablecloth strip. Decorative only. */
export default function Gingham({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`h-3 ${className}`}
      style={{
        backgroundImage:
          "repeating-linear-gradient(90deg, rgba(179,64,43,0.75) 0 6px, transparent 6px 12px)," +
          "repeating-linear-gradient(0deg, rgba(179,64,43,0.45) 0 6px, transparent 6px 12px)",
      }}
    />
  );
}
