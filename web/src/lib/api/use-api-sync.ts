"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { ApiError } from "./client";
import { apiEnabled } from "./config";

export function useApiSync() {
  const client = useQueryClient();
  useEffect(() => {
    if (!apiEnabled) return;
    return client.getMutationCache().subscribe(event => {
      if (event.type !== "updated" || event.mutation.options.meta?.readOnly) return;
      const state = event.mutation.state;
      if (state.status !== "success" && !(state.status === "error" && state.error instanceof ApiError && state.error.status === 412)) return;
      for (const key of ["revision", "review-fields", "equipment", "changes"]) {
        void client.invalidateQueries({ queryKey: [key] });
      }
    });
  }, [client]);
}
