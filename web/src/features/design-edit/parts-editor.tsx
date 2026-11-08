"use client";
import { useState } from "react";
import { Button } from "@/components/ui/primitives";
import type { DesignCatalog, PartChange } from "./api";
const LABELS: Record<string, string> = { diameter: "Diámetro", projection: "Proyección", elevation: "Elevación sobre suelo", azimuth: "Azimut interno", x: "X", y: "Y", z: "Z", dx: "Dirección X", dy: "Dirección Y", dz: "Dirección Z", size_x: "Tamaño X", size_y: "Tamaño Y", size_z: "Tamaño Z", width: "Anchura", height: "Altura", rail_diameter: "Diámetro larguero", rung_spacing: "Separación peldaños" };
const FIELDS = { nozzles: ["diameter", "projection", "elevation", "azimuth"], platforms: ["x", "y", "z", "size_x", "size_y", "size_z"], ladders: ["x", "y", "z", "width", "height", "rail_diameter", "rung_spacing"] };
const CONTROL = "w-full rounded border border-border bg-surface px-2 py-1.5 text-text";
export function PartsEditor({ catalog, changes, onChange, detailLevel, onDetailLevel, disabled }: {
    catalog: DesignCatalog;
    changes: PartChange[];
    onChange: (changes: PartChange[]) => void;
    detailLevel: 2 | 3 | undefined;
    onDetailLevel: (level: 2 | 3 | undefined) => void;
    disabled: boolean;
}) {
    const [action, setAction] = useState<"add" | "remove">("add");
    const [collection, setCollection] = useState<PartChange["collection"]>("nozzles");
    const [id, setId] = useState("");
    const [values, setValues] = useState<Record<string, string>>({});
    const [error, setError] = useState("");
    const fields = collection === "nozzles" && catalog.kind !== "vertical_vessel" ? ["diameter", "projection", "x", "y", "z", "dx", "dy", "dz"] : FIELDS[collection];
    function add() {
        if (!/^[A-Za-z][A-Za-z0-9_-]{0,63}$/.test(id)) {
            setError("Indica un ID válido de pieza (letra, números, guion o subrayado).");
            return;
        }
        if (changes.some(p => p.collection === collection && p.id === id)) {
            setError("Esa pieza ya está en el lote.");
            return;
        }
        const parameters: PartChange["parameters"] = {};
        if (action === "add")
            for (const key of fields) {
                const text = values[key] ?? "";
                if (!text.trim() || !Number.isFinite(Number(text))) {
                    setError(`Completa ${LABELS[key]} con un número.`);
                    return;
                }
                parameters[key] = { value: Number(text), unit: key.startsWith("d") && ["dx", "dy", "dz"].includes(key) ? "1" : key === "azimuth" ? "deg" : "mm" };
            }
        onChange([...changes, { action, collection, id, parameters }]);
        setId("");
        setValues({});
        setError("");
    }
    if (!catalog.parts?.collections.length)
        return <p className="text-xs text-muted">Esta representación solo permite editar sus dimensiones y atributos; no admite piezas detalladas.</p>;
    return <fieldset disabled={disabled} className="space-y-3 rounded-lg border border-border p-3" aria-label="Añadir o eliminar piezas">
    <legend className="px-1 font-semibold">Piezas del equipo</legend>
    <p className="text-xs text-muted">{catalog.parts.notice} La previsualización muestra el resultado antes de confirmar.</p>
    <div className="grid grid-cols-2 gap-2"><label>Acción<select aria-label="Acción de pieza" className={CONTROL} value={action} onChange={e => { setAction(e.target.value as typeof action); setId(""); }}><option value="add">Añadir</option><option value="remove">Eliminar</option></select></label><label>Tipo<select aria-label="Tipo de pieza" className={CONTROL} value={collection} onChange={e => { setCollection(e.target.value as typeof collection); setId(""); setValues({}); }}><option value="nozzles">Boquilla</option><option value="platforms">Plataforma</option><option value="ladders">Escalera</option></select></label></div>
    <label className="block">ID de pieza{action === "add" ? <input aria-label="ID de pieza nueva" className={CONTROL} value={id} maxLength={64} onChange={e => setId(e.target.value)} placeholder="N5 / PL1 / L1"/> : <select aria-label="Pieza que eliminar" className={CONTROL} value={id} onChange={e => setId(e.target.value)}><option value="">Selecciona una pieza existente</option>{(catalog.parts.existing[collection] ?? []).map(value => <option key={value}>{value}</option>)}</select>}</label>
    {action === "add" && <div className="grid grid-cols-2 gap-2">{fields.map(key => <label key={key} className="text-xs">{LABELS[key]} · {key === "azimuth" ? "°" : ["dx", "dy", "dz"].includes(key) ? "sin unidad" : "mm"}<input type="number" step="any" aria-label={`Pieza: ${LABELS[key]}`} className={CONTROL} value={values[key] ?? ""} onChange={e => setValues({ ...values, [key]: e.target.value })}/></label>)}</div>}
    {catalog.lod === 2 && <label className="flex items-start gap-2 text-xs"><input type="checkbox" aria-label="Elevar el nivel de detalle a LOD 3" checked={detailLevel === 3} onChange={e => onDetailLevel(e.target.checked ? 3 : undefined)}/>Elevar explícitamente a LOD 3 para incluir plataformas y escaleras.</label>}
    {error && <p role="alert" className="text-xs text-danger">{error}</p>}
    <Button size="sm" disabled={disabled || changes.length >= 20} onClick={add}>Incluir pieza en la propuesta</Button>
    <ul className="space-y-2">{changes.map((change, index) => <li className="rounded border border-border p-2 text-xs" key={`${change.collection}.${change.id}`}><div className="flex justify-between gap-2"><strong>{change.action === "add" ? "Alta" : "Baja"} · {change.collection}.{change.id}</strong><Button size="sm" variant="ghost" onClick={() => onChange(changes.filter((_, i) => i !== index))}>Quitar del lote</Button></div>{Object.entries(change.parameters).map(([key, value]) => <span key={key} className="mr-2 inline-block text-muted">{LABELS[key]}: {value.value} {value.unit}</span>)}</li>)}</ul>
  </fieldset>;
}
