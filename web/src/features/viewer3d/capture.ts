import { BRAND } from "@/lib/brand";

/** Compone píxeles IFC y rótulos visibles; no captura controles ni documentos externos. */
export async function capturePng(canvas: HTMLCanvasElement): Promise<Blob> {
  const frame = canvas.closest<HTMLElement>('[data-testid="ifc-viewer"]');
  const rect = canvas.getBoundingClientRect();
  const output = document.createElement("canvas");
  output.width = canvas.width; output.height = canvas.height;
  const context = output.getContext("2d");
  if (!context || !rect.width || !rect.height) throw new Error("El visor no está disponible para capturar");
  context.fillStyle = BRAND.black; context.fillRect(0, 0, output.width, output.height);
  context.drawImage(canvas, 0, 0);
  const sx = canvas.width / rect.width, sy = canvas.height / rect.height;
  for (const node of frame?.querySelectorAll<HTMLElement>("[data-capture-label]") ?? []) {
    const box = node.getBoundingClientRect();
    if (!box.width || box.right < rect.left || box.left > rect.right || box.bottom < rect.top || box.top > rect.bottom) continue;
    const text = node.innerText.split("\n")[0] ?? "";
    context.font = `${12 * sy}px monospace`;
    context.fillStyle = BRAND.black;
    context.fillRect((box.left - rect.left) * sx, (box.top - rect.top) * sy, box.width * sx, box.height * sy);
    context.fillStyle = getComputedStyle(node).color;
    context.fillText(text, (box.left - rect.left + 5) * sx, (box.top - rect.top + box.height / 2 + 4) * sy);
  }
  context.fillStyle = BRAND.black; context.fillRect(0, canvas.height - 60, canvas.width, 60);
  context.fillStyle = BRAND.text; context.font = "14px monospace";
  const provenance = frame?.dataset.provenance ?? "Procedencia sin declarar";
  context.fillText(`TrazIA · ${provenance} · ${frame?.dataset.approval ?? "Estado sin declarar"}`, 12, canvas.height - 36, canvas.width - 24);
  context.font = "11px monospace";
  context.fillText(`${new Date().toISOString()} · ${frame?.dataset.triangles ?? "—"} triángulos IFC`, 12, canvas.height - 14);
  return new Promise((resolve, reject) => output.toBlob(blob => blob ? resolve(blob) : reject(new Error("No se pudo crear el PNG")), "image/png"));
}
