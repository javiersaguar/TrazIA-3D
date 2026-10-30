import { SketchPage } from "@/components/shell/sketch-page";
import { ProjectsSketch } from "@/features/bocetos/projects-sketch";

export const metadata = { title: "Proyectos" };

export default function ProyectosPage() {
  return (
    <SketchPage href="/proyectos">
      <ProjectsSketch />
    </SketchPage>
  );
}
