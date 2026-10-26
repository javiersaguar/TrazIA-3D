import type { ReactNode } from "react";

/** Cabecera de página: título y una frase que dice qué se ve y de dónde salen los datos. */
export function PageHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-[22px] leading-tight font-semibold">{title}</h1>
        <p className="mt-1 max-w-[90ch] text-[13px] text-muted">{description}</p>
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}
