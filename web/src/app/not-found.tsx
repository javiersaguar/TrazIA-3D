import Link from "next/link";

export default function NotFound() {
  return (
    <main className="drafting-grid flex min-h-dvh items-center justify-center p-6">
      <div className="max-w-md text-center">
        <p className="font-mono text-xs text-faint">404</p>
        <h1 className="mt-2 text-2xl font-semibold">Esta pantalla no existe</h1>
        <p className="mt-2 text-[13px] text-muted">El enlace puede ser antiguo. Vuelve al proyecto para seguir revisando V-101.</p>
        <Link
          href="/proyecto"
          className="mt-5 inline-flex h-9 items-center rounded-[var(--radius-control)] bg-accent px-4 text-[13px] font-semibold text-accent-contrast"
        >
          Ir al proyecto
        </Link>
      </div>
    </main>
  );
}
