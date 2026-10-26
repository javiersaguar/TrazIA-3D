"use client";

import { useEffect, useMemo, useState } from "react";
import { BufferAttribute, BufferGeometry } from "three";
import { MeshBVH } from "three-mesh-bvh";
import type { IfcModel, IfcProduct, WorkerReply } from "@/workers/ifc-protocol";

export type PreparedProduct = IfcProduct & { geometries: BufferGeometry[] };
type LoadState = { model: IfcModel | null; progress: number; error: string | null };
type Resource = { promise: Promise<IfcModel>; users: number; worker: Worker | null;
  timer?: ReturnType<typeof setTimeout>; ready: boolean };
const resources = new Map<string, Resource>();

function acquire(url: string): Resource {
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

export function useIfcModel(url: string): LoadState {
  const [state, setState] = useState<LoadState & { url: string }>({ url, model: null, progress: 0, error: null });
  useEffect(() => {
    let live = true;
    const resource = acquire(url);
    resource.promise.then(model => { if (live) setState({ url, model, progress: 1, error: null }); },
      error => { if (live) setState({ url, model: null, progress: 0, error: String(error.message) }); });
    return () => { live = false; release(url, resource); };
  }, [url]);
  return state.url === url ? state : { model: null, progress: 0, error: null };
}

export function usePreparedModel(model: IfcModel | null): PreparedProduct[] {
  const products = useMemo(() => model?.products.map(product => ({ ...product,
    geometries: product.parts.map(part => {
      const geometry = new BufferGeometry();
      geometry.setAttribute("position", new BufferAttribute(part.positions, 3));
      geometry.setAttribute("normal", new BufferAttribute(part.normals, 3));
      geometry.setIndex(new BufferAttribute(new Uint32Array(part.indices), 1));
      geometry.computeBoundingBox();
      geometry.computeBoundingSphere();
      return geometry;
    }),
  })) ?? [], [model]);
  useEffect(() => {
    for (const product of products) for (const geometry of product.geometries) {
      // drei conserva tipos transitivos de BVH 0.8; el raycast y el árbol usados aquí son 0.9.
      // Recursos GPU mutables, con vida y limpieza propias, fuera del estado de React.
      // eslint-disable-next-line react-hooks/immutability
      geometry.boundsTree = new MeshBVH(geometry, { targetLeafSize: 10 }) as unknown as NonNullable<BufferGeometry["boundsTree"]>;
    }
    return () => {
      for (const product of products) for (const geometry of product.geometries) {
        geometry.boundsTree = undefined;
        geometry.dispose();
      }
    };
  }, [products]);
  return products;
}
