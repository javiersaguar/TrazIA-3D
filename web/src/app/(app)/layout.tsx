import type { ReactNode } from "react";
import { CommandMenu } from "@/components/shell/command-menu";
import { CopilotLauncher, CopilotPanel } from "@/components/shell/copilot";
import { GlobalKeys } from "@/components/shell/global-keys";
import { ShortcutsDialog } from "@/components/shell/shortcuts-dialog";
import { MobileNav, Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { GuidedTour } from "@/features/tour/guided-tour";

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <main className="mx-auto w-full max-w-[1520px] flex-1 px-4 pt-5 pb-24 sm:px-6 sm:pt-6">{children}</main>
      </div>
      <MobileNav />
      <CommandMenu />
      <ShortcutsDialog />
      <CopilotPanel />
      <CopilotLauncher />
      <GlobalKeys />
      <GuidedTour />
    </div>
  );
}
