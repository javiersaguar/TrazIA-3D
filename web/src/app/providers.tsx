"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "motion/react";
import { ThemeProvider } from "next-themes";
import { useState, type ReactNode } from "react";
import { Toaster } from "sonner";

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          // stale-while-revalidate: se muestra la caché y se revalida en segundo plano
          queries: { staleTime: 30_000, gcTime: 5 * 60_000, refetchOnWindowFocus: true, retry: 1 },
        },
      }),
  );

  return (
    <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem={false} disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>
        <MotionConfig reducedMotion="user">
          <Tooltip.Provider delayDuration={350} skipDelayDuration={150}>
            {children}
            <Toaster
              position="bottom-center"
              theme="system"
              toastOptions={{
                classNames: {
                  toast:
                    "!bg-surface-raised !text-text !border !border-border !rounded-[var(--radius-card)] !shadow-[var(--shadow-pop)] !font-sans",
                  description: "!text-muted",
                  actionButton: "!bg-accent-soft !text-accent-text !font-medium",
                },
              }}
            />
          </Tooltip.Provider>
        </MotionConfig>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
