"use client";

import { useSyncExternalStore } from "react";

/*
  Sesión de demostración. El acceso todavía no valida credenciales: «Iniciar» entra siempre y solo
  se guarda el nombre que se escribió, en sessionStorage, para saludar y mostrar el avatar.
  Nunca se guarda la contraseña.
*/

const KEY = "trazia.sesion";
const listeners = new Set<() => void>();

export type DemoSession = { user: string };

function read(): string | null {
  try {
    return window.sessionStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function startDemoSession(user: string) {
  const name = user.trim() || "demo";
  try {
    window.sessionStorage.setItem(KEY, JSON.stringify({ user: name } satisfies DemoSession));
  } catch {
    /* sin almacenamiento: la sesión solo vive en esta pestaña */
  }
  listeners.forEach((l) => l());
}

export function endDemoSession() {
  try {
    window.sessionStorage.removeItem(KEY);
  } catch {
    /* nada que borrar */
  }
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Usuario de la sesión demo, o null si no se ha iniciado (o en el servidor). */
export function useDemoUser(): string | null {
  const raw = useSyncExternalStore(subscribe, read, () => null);
  if (!raw) return null;
  try {
    return (JSON.parse(raw) as DemoSession).user;
  } catch {
    return null;
  }
}

export function initialsOf(name: string): string {
  const [first = "demo", second] = name.replace(/[._@-]+/g, " ").trim().split(/\s+/).filter(Boolean);
  return (second ? first.charAt(0) + second.charAt(0) : first.slice(0, 2)).toUpperCase();
}
