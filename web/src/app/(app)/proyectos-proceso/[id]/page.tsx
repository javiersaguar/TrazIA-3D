import { notFound } from "next/navigation";
import { PageTransition } from "@/components/shell/page-transition";
import { processProjects } from "@/features/process-projects/catalog";
import { ProcessProjectWorkspace } from "@/features/process-projects/project-workspace";

export const metadata = { title: "Proyecto 3D de proceso" };

export function generateStaticParams() {
  return processProjects.map(project => ({ id: project.id }));
}

export default async function ProcessProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const project = processProjects.find(item => item.id === id);
  if (!project) notFound();
  return <PageTransition><ProcessProjectWorkspace project={project} /></PageTransition>;
}
