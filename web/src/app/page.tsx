import type { Metadata } from "next";

import { display } from "@/features/landing/fonts";
import { LandingPage } from "@/features/landing/landing-page";

export const metadata: Metadata = {
  title: { absolute: "TrazIA-3D · del plano al modelo 3D" },
};

export default function Home() {
  return <LandingPage fontClassName={display.variable} />;
}
