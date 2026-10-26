/** Marca: alzado de un recipiente con su línea de cota, en una baldosa. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={`inline-flex size-9 shrink-0 items-center justify-center rounded-[10px] bg-accent-strong text-white ${className ?? ""}`}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
        <path d="M8 7.5c0-2 1.8-3.5 4-3.5s4 1.5 4 3.5v8c0 2-1.8 3.5-4 3.5s-4-1.5-4-3.5z" />
        <path d="M16 9.5h2.5M5.5 13H8" />
        <path d="M20 4v15M19 4h2M19 19h2" strokeWidth="1.2" opacity="0.75" />
      </svg>
    </span>
  );
}
