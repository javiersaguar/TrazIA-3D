import type { Vec3 } from "@/workers/ifc-protocol";
export type CameraPose = { eye: Vec3; target: Vec3; zoom: number };
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
