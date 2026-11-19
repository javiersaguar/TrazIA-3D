import type { Vec3 } from "@/workers/ifc-protocol";
/**
 * Pose de cámara. En perspectiva `zoom` es el zoom ortográfico equivalente (misma altura visible a
 * la distancia del objetivo), para que las vistas guardadas y el BCF sirvan en las dos proyecciones.
 */
export type CameraPose = { eye: Vec3; target: Vec3; zoom: number; projection?: "perspective" | "orthographic" };
/** Canal efímero entre los dos visores. No provoca renders de React. */
export class CameraLink {
  private listeners = new Map<symbol, (pose: CameraPose) => void>();
  private busy = false;
  subscribe(id: symbol, listener: (pose: CameraPose) => void) {
    this.listeners.set(id, listener); return () => { this.listeners.delete(id); };
  }
  publish(id: symbol, pose: CameraPose) {
    if (this.busy) return;
    this.busy = true;
    try { this.listeners.forEach((fn, key) => { if (key !== id) fn(pose); }); }
    finally { this.busy = false; }
  }
}
