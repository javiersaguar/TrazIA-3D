"use client";

import { useEffect, useState } from "react";

/*
  /reiniciar deja la demo como recién instalada en este navegador: borra documentos añadidos,
  familias y proyectos, borradores, cambios de Diseños, vistas guardadas y preferencias.
  `scripts/demo.py --reiniciar` la abre antes que el resto de pestañas y además restaura el estado
  de la API. ?destino=/ruta elige la pantalla de después (por defecto /documentos).
*/
const DESTINO = "/documentos";
const BASES_DE_DATOS = ["trazia.documents.v1"];

function destino() {
  const pedido = new URLSearchParams(window.location.search).get("destino");
  return pedido && pedido.startsWith("/") && !pedido.startsWith("//") ? pedido : DESTINO;
}

function borrarBase(nombre: string) {
  return new Promise<void>((resolve) => {
    try {
      const peticion = indexedDB.deleteDatabase(nombre);
      peticion.onsuccess = peticion.onerror = peticion.onblocked = () => resolve();
    } catch {
      resolve();
    }
  });
}

async function borrarTodo() {
  for (const almacen of [() => window.localStorage, () => window.sessionStorage]) {
    try {
      almacen().clear();
    } catch {
      /* almacenamiento no disponible */
    }
  }
  await Promise.all(BASES_DE_DATOS.map(borrarBase));
}

export default function ReiniciarDemo() {
  const [listo, setListo] = useState(false);
  useEffect(() => {
    let vigente = true;
    void borrarTodo().then(() => {
      if (!vigente) return;
      setListo(true);
      // Recarga completa: los estados guardados en memoria se vuelven a leer ya vacíos.
      window.setTimeout(() => window.location.replace(destino()), 700);
    });
    return () => {
      vigente = false;
    };
  }, []);
  return (
    <main className="drafting-grid flex min-h-dvh items-center justify-center p-6">
      <div className="max-w-md text-center" role="status" aria-live="polite">
        <h1 className="text-2xl font-semibold">{listo ? "Demo reiniciada" : "Reiniciando la demo…"}</h1>
        <p className="mt-2 text-[13px] text-muted">
          Se borran los documentos, borradores y cambios guardados en este navegador. Los datos de la
          API se restauran desde <code className="font-mono">scripts/demo.py --reiniciar</code>.
        </p>
      </div>
    </main>
  );
}
