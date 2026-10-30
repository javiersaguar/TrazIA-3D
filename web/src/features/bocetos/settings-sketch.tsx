"use client";

import { useTheme } from "next-themes";
import { useState, type ReactNode } from "react";

import { Segmented } from "@/components/ui/controls";
import { Code, Panel, PanelHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { TEAM } from "@/lib/mock/bocetos";
import { initialsOf } from "@/lib/session";
import { useMounted } from "@/lib/use-mounted";

type Policy = "deny" | "synthetic_only" | "allow";

// Mismos valores y significado que src/trazia/vision/policy.py (DEC-31)
const POLICIES: { value: Policy; title: string; text: string }[] = [
  { value: "deny", title: "Ninguno", text: "Ningún documento sale del equipo. Solo modelos locales." },
  { value: "synthetic_only", title: "Solo sintéticos", text: "Los proveedores externos solo ven documentos sintéticos. Es el valor por defecto." },
  { value: "allow", title: "Con autorización", text: "También documentos reales, y solo si se cita la autorización escrita de TR." },
];

function Row({ title, text, children }: { title: string; text: string; children: ReactNode }) {
  return (
    <div className="grid gap-3 border-t border-border px-5 py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] md:items-center">
      <div>
        <p className="text-[14px] font-medium text-text">{title}</p>
        <p className="mt-0.5 text-[13px] text-muted">{text}</p>
      </div>
      <div className="md:justify-self-end">{children}</div>
    </div>
  );
}

export function SettingsSketch() {
  const [policy, setPolicy] = useState<Policy>("synthetic_only");
  const [strategy, setStrategy] = useState<"A" | "B" | "C" | "D">("B");
  const { theme, setTheme } = useTheme();
  const mounted = useMounted();

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        <Panel>
          <PanelHeader title="Proveedores externos" description="Qué documentos pueden salir hacia un modelo que no corre en local." />
          <fieldset className="grid gap-2 px-5 pb-5 sm:grid-cols-3">
            <legend className="sr-only">Política de proveedores externos</legend>
            {POLICIES.map((p) => (
              <label
                key={p.value}
                className={cn(
                  "cursor-pointer rounded-[var(--radius-card)] border p-3 transition-[border-color,background-color] duration-[var(--dur-base)]",
                  policy === p.value ? "border-accent bg-accent-soft" : "border-border hover:border-border-strong",
                )}
              >
                <input type="radio" name="politica" value={p.value} checked={policy === p.value} onChange={() => setPolicy(p.value)} className="sr-only" />
                <span className="flex items-center gap-2 text-[14px] font-medium text-strong">
                  <span className={cn("size-3.5 rounded-full border", policy === p.value ? "border-[4px] border-accent" : "border-border-strong")} aria-hidden />
                  {p.title}
                </span>
                <span className="mt-1 block text-[12.5px] text-muted">{p.text}</span>
                <Code className="mt-2 block text-[11px]">{p.value}</Code>
              </label>
            ))}
          </fieldset>
          <p className="border-t border-border px-5 py-3 text-[12px] text-faint">
            Hoy se fija con <Code>TRAZIA_EXTERNAL_PROVIDERS</Code>; en el boceto este control no lo cambia.
          </p>
        </Panel>

        <Panel>
          <PanelHeader title="Lectura y modelos" />
          <Row title="Estrategia por defecto" text="La que se usa al subir un documento nuevo.">
            <Segmented
              label="Estrategia por defecto"
              value={strategy}
              onChange={setStrategy}
              options={(["A", "B", "C", "D"] as const).map((s) => ({ value: s, label: s }))}
            />
          </Row>
          <Row title="Modelo local" text="Servidor Ollama del equipo para el copiloto y la visión.">
            <span className="text-[13px] text-text">
              <Code className="text-[12px] text-text">qwen3-vl:4b-instruct</Code> en <Code className="text-[12px]">127.0.0.1:11434</Code>
            </span>
          </Row>
          <Row title="Apariencia" text="Oscuro por defecto, como en la demo.">
            <Segmented
              label="Tema"
              value={mounted ? (theme as "dark" | "light" | "system") ?? "dark" : "dark"}
              onChange={setTheme}
              options={[
                { value: "dark", label: "Oscuro" },
                { value: "light", label: "Claro" },
                { value: "system", label: "Sistema" },
              ]}
            />
          </Row>
        </Panel>
      </div>

      <Panel className="h-fit">
        <PanelHeader title="Equipo" description="Personas con acceso a este proyecto." />
        <ul className="divide-y divide-border border-t border-border">
          {TEAM.map((m) => (
            <li key={m.name} className="flex items-center gap-3 px-5 py-3">
              <span className="inline-flex size-8 shrink-0 items-center justify-center rounded-full border border-border-strong bg-surface-raised font-mono text-[11px] text-text">
                {initialsOf(m.name)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[14px] text-text">{m.name}</span>
                <span className="block truncate text-[12px] text-muted">{m.role}</span>
              </span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
