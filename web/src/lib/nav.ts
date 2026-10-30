import {
  Box,
  Calculator,
  FileOutput,
  FileStack,
  FlaskConical,
  FolderKanban,
  Gauge,
  GitCompareArrows,
  History,
  Layers,
  LayoutDashboard,
  ScanSearch,
  Settings,
  Shapes,
  Workflow,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Frase de cabecera: qué se ve y de dónde salen los datos. */
  description: string;
  /** Tecla tras G para ir a la pantalla. */
  shortcut?: string;
  soon?: string;
  /** Pantalla en boceto: datos de ejemplo, sin conexión con el núcleo. */
  sketch?: boolean;
};

export type NavGroup = { label: string; items: NavItem[] };

export const NAV: NavGroup[] = [
  {
    label: "Trabajo",
    items: [
      {
        href: "/proyectos",
        label: "Proyectos",
        icon: FolderKanban,
        shortcut: "p",
        sketch: true,
        description: "Cartera de proyectos con su avance y sus equipos. Boceto con datos de ejemplo.",
      },
      {
        href: "/proyecto",
        label: "Resumen",
        icon: LayoutDashboard,
        shortcut: "1",
        description: "Equipos del proyecto, su estado de revisión y su posición en planta. Solo V-101 tiene datos; el resto es ilustrativo.",
      },
      {
        href: "/documentos",
        label: "Documentos",
        icon: FileStack,
        shortcut: "d",
        sketch: true,
        description: "Bandeja de planos y hojas de datos: recibidos, leídos y revisados. Boceto con datos de ejemplo.",
      },
      {
        href: "/pipeline",
        label: "Pipeline",
        icon: Workflow,
        shortcut: "2",
        description: "Etapas que convierten los documentos en modelo. El aviso indica el origen de los eventos de cada ejecución.",
      },
      {
        href: "/revision",
        label: "Revisión",
        icon: ScanSearch,
        shortcut: "3",
        description: "Cada valor con su evidencia en el plano y su elemento en 3D. Todo sale del JSON extraído y del IFC generado.",
      },
      {
        href: "/cambios",
        label: "Cambios",
        icon: GitCompareArrows,
        shortcut: "4",
        description: "Qué cambia de la rev A a la rev B, cuánto, dónde y a qué disciplinas afecta. Datos del delta del núcleo.",
      },
      {
        href: "/modelo",
        label: "Modelo 3D",
        icon: Box,
        shortcut: "m",
        sketch: true,
        description: "Del holograma al modelo: el IFC generado y una galería de equipos ilustrativos.",
      },
    ],
  },
  {
    label: "Calidad",
    items: [
      {
        href: "/bench",
        label: "Bench",
        icon: Gauge,
        shortcut: "5",
        description: "Métricas del jurado medidas sobre un conjunto sintético con verdad conocida. Con el dataset del reto se medirá contra sus IFC de referencia.",
      },
      {
        href: "/estudio",
        label: "Estudio",
        icon: FlaskConical,
        shortcut: "7",
        description: "Las cuatro estrategias de la pág. 13 medidas con los mismos documentos: puntuación, intervalos, ablaciones y coste. Elegimos con datos.",
      },
      {
        href: "/impacto",
        label: "Impacto",
        icon: Calculator,
        shortcut: "6",
        description: "Horas de modelado que se ahorran por proyecto con las cifras del reto y el tiempo de revisión medido.",
      },
    ],
  },
  {
    label: "Gestión",
    items: [
      {
        href: "/familias",
        label: "Familias",
        icon: Shapes,
        shortcut: "f",
        sketch: true,
        description: "Catálogo de familias de equipos y su cobertura. Boceto con datos de ejemplo.",
      },
      {
        href: "/lote",
        label: "Lote",
        icon: Layers,
        shortcut: "l",
        sketch: true,
        description: "Procesamiento por lotes: cola de trabajos, progreso y coste. Boceto con datos de ejemplo.",
      },
      {
        href: "/informes",
        label: "Informes",
        icon: FileOutput,
        shortcut: "i",
        sketch: true,
        description: "Exportaciones IFC, BCF, CSV e informe, con la huella de los datos. Boceto con datos de ejemplo.",
      },
      {
        href: "/auditoria",
        label: "Auditoría",
        icon: History,
        shortcut: "a",
        sketch: true,
        description: "Quién cambió qué y cuándo: ediciones, aprobaciones e invalidaciones. Boceto con datos de ejemplo.",
      },
      {
        href: "/ajustes",
        label: "Ajustes",
        icon: Settings,
        shortcut: "s",
        sketch: true,
        description: "Proveedores, estrategia por defecto, modelo local, tema y equipo. Boceto con datos de ejemplo.",
      },
    ],
  },
];

export const NAV_ITEMS = NAV.flatMap((g) => g.items).filter((i) => !i.soon);

export function navItemFor(pathname: string): NavItem | undefined {
  return NAV_ITEMS.find((i) => pathname === i.href || pathname.startsWith(`${i.href}/`));
}
