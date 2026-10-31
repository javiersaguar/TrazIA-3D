/** Entrada decimal del inspector; los límites físicos los valida la API por campo. */
export function parseReviewNumber(draft: string) {
  const value = draft.trim();
  if (value.includes(",") && value.includes(".") && !/^[+-]?\d{1,3}(?:\.\d{3})+,\d*$/.test(value)) return NaN;
  const normalized = value.includes(",") ? value.replace(/\./g, "").replace(",", ".") : value;
  return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(normalized) ? Number(normalized) : NaN;
}
