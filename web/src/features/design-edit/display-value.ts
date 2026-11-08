/** Conversión de presentación; el servidor sigue siendo quien normaliza y valida. */
export function convertDisplay(value: string, from: string, to: string): string {
  if (from === to) return value;
  if (!/^[+-]?(?:\d+\.?\d*|\.\d+)$/.test(value.trim())) return "";
  let number = Number(value);
  const tables = [
    {mm:1, cm:10, m:1000, in:25.4, ft:304.8},
    {kg:1, t:1000, lb:0.45359237},
    {bar:1, barg:1, kPa:0.01, MPa:10, psi:0.0689475729},
    {bara:1, psia:0.0689475729},
  ];
  const table = tables.find(t => from in t && to in t) as Record<string,number> | undefined;
  if (table) number *= table[from]! / table[to]!;
  else if (from === "C" && to === "F") number = number * 9/5 + 32;
  else if (from === "F" && to === "C") number = (number-32) * 5/9;
  else return "";
  return Number(number.toPrecision(12)).toString();
}
