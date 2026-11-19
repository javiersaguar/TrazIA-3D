"use client";

import { useEffect, useMemo, useState } from "react";
import { BufferAttribute, BufferGeometry } from "three";
import { MeshBVH } from "three-mesh-bvh";
import type { IfcModel, IfcProduct, WorkerReply } from "@/workers/ifc-protocol";
import { creasedNormals } from "./creased-normals";
import { addSurfaceUV } from "./surface-uv";

export type PreparedProduct = IfcProduct & { geometries: BufferGeometry[] };
type LoadState = { model: IfcModel | null; progress: number; error: string | null };
type Resource = { promise: Promise<IfcModel>; users: number; worker: Worker | null;
  timer?: ReturnType<typeof setTimeout>; ready: boolean };
const resources = new Map<string, Resource>();

function acquire(url: string, gzip?: string): Resource {
  let resource = resources.get(url);
  if (!resource) {
    const worker = new Worker(new URL("../../workers/ifc.worker.ts", import.meta.url), { type: "module" });
    const promise = new Promise<IfcModel>((resolve, reject) => {
      worker.onmessage = ({ data }: MessageEvent<WorkerReply>) => {
        if (data.type === "ready") {
          resource!.ready = true;
          resource!.worker = null;
          worker.terminate();
          resolve(data.model);
        } else if (data.type === "error") {
          worker.terminate();
          resource!.worker = null;
          reject(new Error(data.message));
        }
      };
      worker.onerror = () => {
        worker.terminate();
        reject(new Error("El worker IFC no pudo iniciarse. Comprueba el archivo WASM local."));
      };
    });
    resource = { promise, users: 0, worker, ready: false };
    resources.set(url, resource);
    worker.postMessage({ type: "load", url: new URL(url, window.location.href).href,
      gzipUrl: gzip ? new URL(gzip, window.location.href).href : undefined,
      wasmPath: new URL("/wasm/", window.location.href).href });
  }
  clearTimeout(resource.timer);
  resource.users++;
  return resource;
}

function release(url: string, resource: Resource) {
  resource.users--;
  if (!resource.users) {
    resource.timer = setTimeout(() => {
      if (resource.users) return;
      resource.worker?.terminate();
      resources.delete(url);
    }, 100);
  }
}

export function useIfcModel(url: string, holdPrevious = false, gzip?: string): LoadState {
  const [state, setState] = useState<LoadState & { url: string }>({ url, model: null, progress: 0, error: null });
  useEffect(() => {
    let live = true;
    const resource = acquire(url, gzip);
    resource.promise.then(model => { if (live) setState({ url, model, progress: 1, error: null }); },
      error => { if (live) setState({ url, model: null, progress: 0, error: String(error.message) }); });
    return () => { live = false; release(url, resource); };
  }, [url, gzip]);
  if (state.url === url) return state;
  // Con holdPrevious el modelo anterior sigue en pantalla hasta que el nuevo está listo.
  return holdPrevious && state.model ? { model: state.model, progress: 1, error: null } : { model: null, progress: 0, error: null };
}

/** Ángulo de pliegue del sombreado: suaviza virolas y tubos, conserva bridas y aristas de perfiles. */
export const CREASE_DEGREES = 38;
type PrepareCost = { geometryMs: number; normalsMs: number; bvhMs?: number };
const costs = new WeakMap<PreparedProduct[], PrepareCost>();
/** Coste medido de preparar las mallas (normales con pliegue y BVH), para el atributo del visor. */
export const prepareCost = (products: PreparedProduct[]) => costs.get(products);

/** Geometrías de three a partir de las mallas del worker; mide lo que cuesta cada paso. */
function prepareProducts(model: IfcModel): PreparedProduct[] {
  const start = performance.now();
  let normalsMs = 0;
  const list = model.products.map(product => ({ ...product,
    geometries: product.parts.map(part => {
      const geometry = new BufferGeometry();
      geometry.setAttribute("position", new BufferAttribute(part.positions, 3));
      // Solo sombreado: mismas posiciones e índices que el IFC, normales promediadas bajo el pliegue.
      const before = performance.now();
      const normals = creasedNormals(part.positions, part.indices, CREASE_DEGREES, part.normals);
      normalsMs += performance.now() - before;
      geometry.setAttribute("normal", new BufferAttribute(normals, 3));
      geometry.setIndex(new BufferAttribute(new Uint32Array(part.indices), 1));
      geometry.computeBoundingBox();
      addSurfaceUV(geometry);
      geometry.computeBoundingSphere();
      return geometry;
    }),
  }));
  costs.set(list, { geometryMs: performance.now() - start, normalsMs });
  return list;
}

// drei conserva tipos transitivos de BVH 0.8; el raycast y el árbol usados aquí son 0.9.
// Recursos GPU mutables, con vida y limpieza propias, fuera del estado de React.
function buildBoundsTrees(products: PreparedProduct[]) {
  const start = performance.now();
  for (const product of products) for (const geometry of product.geometries) {
    geometry.boundsTree = new MeshBVH(geometry, { targetLeafSize: 10 }) as unknown as NonNullable<BufferGeometry["boundsTree"]>;
  }
  const cost = costs.get(products);
  if (cost) cost.bvhMs = performance.now() - start;
}

function releaseGeometries(products: PreparedProduct[]) {
  for (const product of products) for (const geometry of product.geometries) {
    geometry.boundsTree = undefined;
    geometry.dispose();
  }
}

export function usePreparedModel(model: IfcModel | null): PreparedProduct[] {
  const products = useMemo(() => (model ? prepareProducts(model) : []), [model]);
  useEffect(() => {
    buildBoundsTrees(products);
    return () => releaseGeometries(products);
  }, [products]);
  return products;
}
