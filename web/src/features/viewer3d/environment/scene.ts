import { Group, type MeshStandardMaterial, type Object3D } from "three";
import { disposeTree, type AtmosphereUniforms } from "./atmosphere";
import type { ContactProduct } from "./contacts";
import type { EnvironmentId, Palette, Quality } from "./palettes";
import type { SiteFrame } from "./site";

/*
  Contrato interno de cada entorno: construye su grupo de objetos una vez (memorizado por
  entorno, calidad y emplazamiento) y expone `update(t)` para lo que se mueve en CPU (barcos,
  vehículos, matorrales). Lo que se mueve en GPU (agua, partículas, aves, llamas) solo lee el
  uniforme de tiempo común `uEnvTime`.
*/

export type SceneContext = {
  id: EnvironmentId;
  palette: Palette;
  site: SiteFrame;
  quality: Quality;
  atmosphere: AtmosphereUniforms;
  /** Material compartido del atrezo (color, rugosidad y metalicidad por vértice). */
  props: MeshStandardMaterial;
  /** Igual, con sombreado facetado (rocas, bloques). */
  facets: MeshStandardMaterial;
};

export type EnvironmentScene = {
  group: Group;
  /** t es el tiempo absoluto del entorno (el mismo que `uEnvTime`). */
  update(t: number): void;
  /** Geometría IFC de la planta: el agua calcula con ella dónde la cortan las patas. */
  setProducts(products: readonly ContactProduct[]): void;
  dispose(): void;
  /** Número de objetos que se dibujan (para medir el presupuesto de draw calls). */
  stats(): { meshes: number; triangles: number };
};

export function sceneGroup(name: string, children: Object3D[]): Group {
  const group = new Group();
  group.name = name;
  for (const child of children) group.add(child);
  return group;
}

export function standardScene(
  group: Group,
  update: (t: number) => void = () => {},
  options: { setProducts?: (products: readonly ContactProduct[]) => void; dispose?: () => void } = {},
): EnvironmentScene {
  const extra = options.dispose ?? (() => {});
  return {
    group,
    update,
    setProducts: options.setProducts ?? (() => {}),
    dispose() {
      extra();
      disposeTree(group);
    },
    stats() {
      let meshes = 0, triangles = 0;
      group.traverse(object => {
        const mesh = object as Object3D & { isMesh?: boolean; geometry?: { index: { count: number } | null; attributes: { position: { count: number } }; instanceCount?: number }; count?: number };
        if (!mesh.isMesh || !mesh.geometry) return;
        meshes++;
        const g = mesh.geometry;
        const base = (g.index ? g.index.count : g.attributes.position.count) / 3;
        const instances = g.instanceCount ?? mesh.count ?? 1;
        triangles += base * (Number.isFinite(instances) ? instances : 1);
      });
      return { meshes, triangles };
    },
  };
}
