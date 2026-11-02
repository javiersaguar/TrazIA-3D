/** Fases de la secuencia «Del plano al modelo»; «at» es el avance (0–1) en que empieza cada una. */
export const SIGNATURE_PHASES = [
  { at: 0, title: "El plano conserva la evidencia", text: "Las cinco cotas se localizan en su región real del PDF." },
  { at: 0.28, title: "La geometría del IFC se levanta", text: "Las mallas del IFC pasan de alambre a acero. La secuencia es ilustrativa." },
  { at: 0.82, title: "Modelo DRAFT listo para revisar", text: "La aprobación continúa en el espacio de revisión; esta secuencia no valida el equipo." },
] as const;
