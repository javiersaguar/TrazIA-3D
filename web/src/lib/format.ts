// useGrouping "always": en es-ES los números de 4 cifras no se agrupan por defecto (4800 → 4.800)
const numberFormat = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 2, useGrouping: "always" });
const signedFormat = new Intl.NumberFormat("es-ES", {
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
  useGrouping: "always",
});
const percentFormat = new Intl.NumberFormat("es-ES", {
  style: "percent",
  maximumFractionDigits: 0,
});

/** Unidad tal como se muestra al usuario. "1" es adimensional en el contrato. */
export function displayUnit(unit: string | undefined): string {
  switch (unit) {
    case undefined:
    case "1":
      return "";
    case "deg":
      return "°";
    case "C":
      return "°C";
    default:
      return unit;
  }
}

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

export function formatValue(value: number | string, unit?: string): string {
  if (typeof value === "string") return value;
  const u = displayUnit(unit);
  if (!u) return formatNumber(value);
  return u === "°" ? `${formatNumber(value)}°` : `${formatNumber(value)} ${u}`;
}

export function formatDelta(delta: number, unit?: string): string {
  const u = displayUnit(unit);
  const n = signedFormat.format(delta);
  if (!u) return n;
  return u === "°" ? `${n}°` : `${n} ${u}`;
}

export function formatPercent(ratio: number): string {
  return percentFormat.format(ratio);
}

export function shortHash(sha: string, size = 8): string {
  return sha.slice(0, size);
}

export function relativeSeconds(seconds: number): string {
  if (seconds < 60) return `hace ${Math.max(0, Math.round(seconds))} s`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `hace ${minutes} min`;
  return `hace ${Math.round(minutes / 60)} h`;
}
