"use client";
import { useMemo, useState, useSyncExternalStore, type RefObject } from "react";
import type { CameraHandle } from "./stage";
import { readViews, viewsKey, type SavedView } from "./saved-views";
import styles from "./viewer.module.css";

function subscribe(listener: () => void) {
  window.addEventListener("storage", listener); window.addEventListener("trazia-views", listener);
  return () => { window.removeEventListener("storage", listener); window.removeEventListener("trazia-views", listener); };
}

export function ViewBookmarks({ url, camera, onRestore }: { url: string; camera: RefObject<CameraHandle | null>; onRestore?(): void }) {
  const raw = useSyncExternalStore(subscribe, () => {
    try { return localStorage.getItem(viewsKey(url)); } catch { return null; }
  }, () => null);
  const views = useMemo(() => readViews(raw), [raw]);
  const [name, setName] = useState("");
  const [selected, setSelected] = useState("");
  const [message, setMessage] = useState("");
  const save = (next: SavedView[]) => {
    try { localStorage.setItem(viewsKey(url), JSON.stringify(next)); window.dispatchEvent(new Event("trazia-views")); }
    catch { setMessage("No se pudo guardar la vista; comprueba el almacenamiento del navegador"); }
  };
  return <div className={styles.bookmarks} aria-label="Vistas personales del IFC">
    <input className={styles.select} aria-label="Nombre de la vista" placeholder="Nombre de vista" maxLength={40}
      value={name} onChange={event => setName(event.target.value)} />
    <button type="button" className={styles.button} disabled={!name.trim() || views.length >= 8} onClick={() => {
      const pose = camera.current?.pose?.();
      if (!pose) return;
      const id = crypto.randomUUID();
      save([...views, { id, name: name.trim(), pose }]); setName(""); setSelected(id);
    }}>Guardar vista</button>
    <select className={styles.select} aria-label="Recuperar vista guardada" value={selected} onChange={event => {
      setSelected(event.target.value);
      const view = views.find(v => v.id === event.target.value);
      if (view) { camera.current?.restore?.(view.pose); onRestore?.(); }
    }}><option value="">Vistas personales ({views.length}/8)</option>
      {views.map(view => <option key={view.id} value={view.id}>{view.name}</option>)}
    </select>
    <button type="button" className={styles.button} disabled={!selected} onClick={() => {
      save(views.filter(v => v.id !== selected)); setSelected("");
    }}>Eliminar vista</button>
    <span role="status" className={styles.small}>{message}</span>
  </div>;
}
