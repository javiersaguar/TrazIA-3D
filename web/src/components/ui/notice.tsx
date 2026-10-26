import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "./primitives";

/** Aviso ámbar de honestidad sobre los datos (como el de "Demo geográfica ilustrativa"). */
export function SyntheticNotice({ children, className }: { children?: ReactNode; className?: string }) {
  return (
    <div
      role="note"
      className={cn(
        "flex items-start gap-2.5 rounded-[var(--radius-card)] border border-warning-border bg-warning-bg px-4 py-2.5 text-[13px] text-warning",
        className,
      )}
    >
      <Icon icon={TriangleAlert} className="mt-0.5" />
      <p>
        <span className="font-medium">Datos sintéticos · no son del dataset de TR.</span>{" "}
        <span className="opacity-90">{children}</span>
      </p>
    </div>
  );
}
