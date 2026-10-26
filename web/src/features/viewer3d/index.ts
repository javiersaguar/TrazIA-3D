/*
  Punto de entrada del 3D. Las pantallas importan SIEMPRE desde aquí y con
  next/dynamic({ ssr: false }), por ejemplo:
    const IfcViewer = dynamic(() => import("@/features/viewer3d").then((m) => m.IfcViewer), { ssr: false });
*/
export { IfcViewer } from "./ifc-viewer";
export { PlantScene, RevisionMorph } from "./stub";
export type {
  Annotation,
  IfcViewerProps,
  PlantEquipment,
  PlantSceneProps,
  RevisionMorphProps,
} from "./types";
