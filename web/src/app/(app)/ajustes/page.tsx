import { SketchPage } from "@/components/shell/sketch-page";
import { SettingsSketch } from "@/features/bocetos/settings-sketch";

export const metadata = { title: "Ajustes" };

export default function AjustesPage() {
  return (
    <SketchPage href="/ajustes" note="El tema funciona de verdad; el resto de controles solo cambia esta vista.">
      <SettingsSketch />
    </SketchPage>
  );
}
