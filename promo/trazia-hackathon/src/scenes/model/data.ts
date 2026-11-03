import { useEffect, useState } from 'react';
import { BufferAttribute, BufferGeometry, SRGBColorSpace, Texture, TextureLoader } from 'three';
import { toCreasedNormals } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { continueRender, delayRender, staticFile } from 'remotion';

// Geometría real del IFC sintético (scripts/export_ifc.py): una malla por producto, emparejadas por GlobalId.
type RawProduct = { id: string; type: string; name: string; description: string | null; v: number[]; f: number[] };
type Raw = { products: RawProduct[] };
export type Evidence = { path: string; bbox: [number, number, number, number] };

export type Part = {
  id: string;
  name: string;
  type: string;
  /** Geometría rev A (o rev B si la pieza es nueva), con normales por pliegue. */
  geometry: BufferGeometry;
  /** Geometría rev B cuando la topología cambia (virola y faldón): se muestra al terminar el morph. */
  geometryB?: BufferGeometry;
  /** Transformación vertical que lleva A a B en piezas prismáticas sin correspondencia de vértices. */
  stretch?: { sy: number; ty: number };
  morph: boolean; // tiene objetivo de morph por vértice
  added: boolean; // solo existe en la rev B
  changed: boolean; // pertenece a un cambio de changes.json (se tiñe de naranja)
  center: [number, number, number];
  yMid: number;
};

const CREASE = (35 * Math.PI) / 180;
const build = (p: RawProduct) => {
  const g = new BufferGeometry();
  g.setAttribute('position', new BufferAttribute(new Float32Array(p.v), 3));
  g.setIndex(p.f);
  return toCreasedNormals(g, CREASE);
};
const bbox = (v: number[]) => {
  const mn = [Infinity, Infinity, Infinity];
  const mx = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < v.length; i++) {
    const k = i % 3;
    if (v[i] < mn[k]) mn[k] = v[i];
    if (v[i] > mx[k]) mx[k] = v[i];
  }
  return { mn, mx };
};
// Cambios con geometría en changes.json: altura (virola), faldón, N3 y N4 nueva
const isChanged = (name: string) => name === 'V-101' || name === 'V-101/skirt' || /N3|N4/.test(name);

export const buildParts = (a: Raw, b: Raw): Part[] => {
  const byId = new Map(b.products.map((p) => [p.id, p]));
  const parts: Part[] = [];
  for (const pa of a.products) {
    const pb = byId.get(pa.id);
    const { mn, mx } = bbox(pa.v);
    const center: [number, number, number] = [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2];
    const geometry = build(pa);
    const part: Part = { id: pa.id, name: pa.name, type: pa.type, geometry, morph: false, added: false, changed: isChanged(pa.name), center, yMid: center[1] };
    if (pb) {
      const sameTopo = pb.v.length === pa.v.length && pb.f.length === pa.f.length && pb.f.every((x, i) => x === pa.f[i]);
      if (sameTopo) {
        const gb = build(pb);
        geometry.morphAttributes.position = [gb.getAttribute('position')];
        geometry.morphAttributes.normal = [gb.getAttribute('normal')];
        part.morph = true;
      } else {
        // Virola y faldón: mismo prisma, otra altura. Se estira A en Y y al final se muestra la malla B real.
        const A = bbox(pa.v);
        const B = bbox(pb.v);
        const sy = (B.mx[1] - B.mn[1]) / (A.mx[1] - A.mn[1]);
        part.stretch = { sy, ty: B.mn[1] - A.mn[1] * sy };
        part.geometryB = build(pb);
      }
    }
    parts.push(part);
  }
  for (const pb of b.products) {
    if (a.products.some((p) => p.id === pb.id)) continue;
    const { mn, mx } = bbox(pb.v);
    const center: [number, number, number] = [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2];
    parts.push({ id: pb.id, name: pb.name, type: pb.type, geometry: build(pb), morph: false, added: true, changed: true, center, yMid: center[1] });
  }
  return parts;
};

export type ModelData = { parts: Part[]; paper: Texture; aspect: number; evidence: Evidence[] };

/** Carga JSON + textura con delayRender (render determinista). */
export const useModelData = (): ModelData | null => {
  const [data, setData] = useState<ModelData | null>(null);
  const [handle] = useState(() => delayRender('geometría IFC y plano GA', { timeoutInMilliseconds: 120000 }));
  useEffect(() => {
    let live = true;
    (async () => {
      const [a, b, ev] = await Promise.all(
        ['geometry/rev_a.json', 'geometry/rev_b.json', 'textures/evidence-rev-a.json'].map((p) => fetch(staticFile(p)).then((r) => r.json())),
      );
      const paper = await new TextureLoader().loadAsync(staticFile('textures/ga-reva-p1.png'));
      paper.colorSpace = SRGBColorSpace;
      paper.anisotropy = 8;
      const keys = ['equipment.diameter', 'equipment.height', 'equipment.head_depth', 'equipment.skirt_height', 'equipment.skirt_thickness'];
      const evidence = (ev as Evidence[]).filter((e) => keys.includes(e.path));
      const img = paper.image as { width: number; height: number };
      if (live) setData({ parts: buildParts(a, b), paper, aspect: img.width / img.height, evidence });
      continueRender(handle);
    })().catch((e) => {
      console.error(e);
      continueRender(handle);
    });
    return () => {
      live = false;
    };
  }, [handle]);
  return data;
};
