"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** true solo en cliente tras hidratar; evita desajustes de tema entre servidor y cliente. */
export function useMounted(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
