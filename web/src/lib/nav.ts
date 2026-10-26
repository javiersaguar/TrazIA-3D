import {
  Calculator,
  Gauge,
  GitCompareArrows,
  Layers,
  LayoutDashboard,
  ScanSearch,
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
  shortcut?: string;
  soon?: string;
};

export type NavGroup = { label: string; items: NavItem[] };

export const NAV: NavGroup[] = [
  {
    label: "Trabajo",
    items: [
      {
        href: "/proyecto",
        label: "Proyecto",
        icon: LayoutDashboard,
        shortcut: "1",
        description: "Equipos del proyecto, su estado de revisión y su posición en planta. Solo V-101 tiene datos; el resto es ilustrativo.",
      },
      {
        href: "/pipeline",
        label: "Pipeline",
        icon: Workflow,
        shortcut: "2",
        description: "Etapas que convierten los documentos en modelo. Repetición simulada sobre los documentos sintéticos de V-101.",
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
        description: "Métricas del jurado medidas contra los IFC de referencia de Técnicas Reunidas. Pendiente del dataset oficial.",
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
    label: "Próximamente",
    items: [
      { href: "#familias", label: "Familias", icon: Shapes, soon: "F2", description: "" },
      { href: "#lote", label: "Lote", icon: Layers, soon: "F3", description: "" },
    ],
  },
];

export const NAV_ITEMS = NAV.flatMap((g) => g.items).filter((i) => !i.soon);

export function navItemFor(pathname: string): NavItem | undefined {
  return NAV_ITEMS.find((i) => pathname === i.href || pathname.startsWith(`${i.href}/`));
}
