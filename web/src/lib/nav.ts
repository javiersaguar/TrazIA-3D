import { Box, Calculator, FileStack, FlaskConical, Gauge, Layers, LayoutDashboard, Settings, Sparkles, Workflow, type LucideIcon } from "lucide-react";
export type NavItem = { href: string; label: string; icon: LucideIcon; description: string; shortcut?: string; soon?: string; sketch?: boolean };
export type NavGroup = { label: string; items: NavItem[] };
export const SETTINGS_ITEM: NavItem = { href: "/ajustes", label: "Ajustes", icon: Settings, shortcut: "s", description: "Apariencia, preferencias de lectura y equipo." };
export const NAV: NavGroup[] = [
 { label: "Trabajo", items: [
  { href: "/proyecto", label: "Resumen", icon: LayoutDashboard, shortcut: "1", description: "Estado de los equipos y posición en planta. Demostración con datos sintéticos." },
  { href: "/documentos", label: "Documentos", icon: FileStack, shortcut: "d", description: "Familias, proyectos y diseños, con sus documentos de origen." },
  { href: "/modelo", label: "Modelo", icon: Box, shortcut: "m", description: "Revisa la evidencia, compara revisiones y explora el IFC en un único espacio." },
  { href: "/pipeline", label: "Pipeline", icon: Workflow, shortcut: "2", description: "Etapas y eventos de cada ejecución, con su procedencia." },
  { href: "/lote", label: "Lotes e informes", icon: Layers, shortcut: "l", description: "Procesamiento y exportaciones del proyecto en un mismo lugar." },
 ]},
 { label: "Calidad", items: [
  { href: "/bench", label: "Bench", icon: Gauge, shortcut: "5", description: "Banco de pruebas y comparación de estrategias sobre datos sintéticos." },
  { href: "/impacto", label: "Impacto", icon: Calculator, shortcut: "6", description: "Escenario de ahorro por proyecto. El tiempo de revisión humana sigue sin medir." },
 ]},
 { label: "Laboratorio", items: [
  { href: "/lab/firma", label: "Del plano al modelo", icon: Sparkles, shortcut: "9", description: "El plano de V-101 se levanta hasta el acero, con las regiones leídas iluminadas." },
  { href: "/lab/3d", label: "Laboratorio 3D", icon: FlaskConical, shortcut: "8", description: "Cotas y rendimiento del visor, planta y comparación de revisiones a tamaño completo." },
 ]},
];
export const NAV_ITEMS = [...NAV.flatMap(g => g.items), SETTINGS_ITEM];
export function navItemFor(pathname: string): NavItem | undefined {
 const aliases: Record<string,string> = { "/revision": "/modelo", "/cambios": "/modelo", "/proyectos": "/documentos", "/familias": "/documentos", "/informes": "/lote", "/estudio": "/bench" };
 const path = aliases[pathname] ?? pathname;
 return NAV_ITEMS.find(i => path === i.href || path.startsWith(`${i.href}/`));
}
