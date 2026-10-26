import { ViewTransition, type ReactNode } from "react";

/** Envuelve el contenido de cada page.tsx: los layouts persisten y no disparan enter/exit. */
export function PageTransition({ children }: { children: ReactNode }) {
  return (
    <ViewTransition enter="page" exit="page" default="none">
      {children}
    </ViewTransition>
  );
}
