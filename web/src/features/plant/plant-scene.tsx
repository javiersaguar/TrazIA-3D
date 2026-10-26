"use client";

import { Grid } from "@react-three/drei";
import type { ThreeEvent } from "@react-three/fiber";
import { Eye, LocateFixed, Play } from "lucide-react";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Color, InstancedMesh, Matrix4 } from "three";
import type { Bounds, IfcModel, Vec3 } from "@/workers/ifc-protocol";
import { useIfcModel, usePreparedModel, type PreparedProduct } from "../viewer3d/model-resource";
import { STATE_COLORS } from "../viewer3d/product-mesh";
import { SteelMaterial } from "../viewer3d/materials";
import { CameraRig, CameraTools, Legend, LoadingState, SceneCanvas, SceneLabel as Html, Studio, type CameraHandle } from "../viewer3d/stage";
import type { PlantEquipment, PlantSceneProps } from "../viewer3d/types";
import styles from "../viewer3d/viewer.module.css";

type Item = PlantEquipment & { position: Vec3; area: string };

function InstancePart({ product, part, items, selected, onSelect, onFocus }: {
  product: PreparedProduct; part: number; items: Item[]; selected: string | null;
  onSelect(tag: string): void; onFocus(tag: string): void;
}) {
  const mesh = useRef<InstancedMesh>(null);
  const color = useMemo(() => new Color(), []);
  useLayoutEffect(() => {
    if (!mesh.current) return;
    const matrix = new Matrix4();
    items.forEach((item, index) => {
      matrix.makeTranslation(item.position[0] + product.center[0], item.position[1] + product.center[1], item.position[2] + product.center[2]);
      mesh.current!.setMatrixAt(index, matrix);
      const tint = selected === item.tag ? "#b6d3fa" : item.status === "review" ? "#86aee8" : STATE_COLORS[item.status];
      mesh.current!.setColorAt(index, color.set(tint));
    });
    mesh.current.instanceMatrix.needsUpdate = true;
    if (mesh.current.instanceColor) mesh.current.instanceColor.needsUpdate = true;
    mesh.current.computeBoundingSphere();
  }, [items, product.center, selected, color]);
  const click = (event: ThreeEvent<MouseEvent>, focus = false) => {
    event.stopPropagation();
    const item = items[event.instanceId ?? -1];
    if (item) { onSelect(item.tag); if (focus) onFocus(item.tag); }
  };
  return <instancedMesh ref={mesh} args={[product.geometries[part], undefined, items.length]}
    onClick={e => click(e)} onDoubleClick={e => click(e, true)} dispose={null}>
    <SteelMaterial color="white" roughness={.38} metalness={.55} />
  </instancedMesh>;
}

function PlantInstances({ url, items, selected, onSelect, onFocus, onLoaded }: {
  url: string; items: Item[]; selected: string | null; onSelect(tag: string): void;
  onFocus(tag: string): void; onLoaded(url: string, model: IfcModel | null, error: string | null): void;
}) {
  const load = useIfcModel(url), products = usePreparedModel(load.model);
  useEffect(() => { onLoaded(url, load.model, load.error); }, [url, load.model, load.error, onLoaded]);
  if (!load.model) return null;
  const sourceTag = load.model.products.find(p => p.semanticId === "shell")?.name;
  return <>
    {products.flatMap(product => product.geometries.map((_, part) => <InstancePart key={`${product.globalId}:${part}`}
      product={product} part={part} items={items} selected={selected} onSelect={onSelect} onFocus={onFocus} />))}
    {/* Etiqueta sobre la cabeza de cada recipiente: al pie se solapaban con la fila delantera. */}
    {items.map(item => <Html key={item.tag} position={[item.position[0], load.model!.bounds.max[1] + .9, item.position[2]]} center
      zIndexRange={[8, 0]}>
      <button className={styles.button} aria-pressed={selected === item.tag} onClick={() => onSelect(item.tag)}
        title={item.tag !== sourceTag ? `${item.tag} · instancia ilustrativa` : `${item.tag} · equipo con datos`}>
        {item.tag}
      </button>
    </Html>)}
  </>;
}

export function PlantScene({ equipment, onSelect }: PlantSceneProps) {
  const [selected, setSelected] = useState<string | null>(null), [follow, setFollow] = useState(false);
  const [models, setModels] = useState<Record<string, IfcModel>>({});
  const [error, setError] = useState<string | null>(null);
  const container = useRef<HTMLDivElement>(null), camera = useRef<CameraHandle>(null);
  const areas = useMemo(() => [...new Set(equipment.map(item => `Unidad ${item.tag.match(/-(\d)/)?.[1] ?? "1"}00`))], [equipment]);
  const items = useMemo<Item[]>(() => {
    const count = new Map<string, number>();
    return equipment.map(item => {
      const area = `Unidad ${item.tag.match(/-(\d)/)?.[1] ?? "1"}00`, index = count.get(area) ?? 0;
      count.set(area, index + 1);
      return { ...item, area, position: [(areas.indexOf(area) - (areas.length - 1) / 2) * 12 + (index % 2 ? 2 : -2), 0, -2 + Math.floor(index / 2) * 4] };
    });
  }, [equipment, areas]);
  const groups = useMemo(() => [...new Set(items.map(item => item.ifcUrl))].map(url => ({ url, items: items.filter(item => item.ifcUrl === url) })), [items]);
  const bounds = useMemo<Bounds>(() => ({ min: [-(areas.length * 12) / 2, -.3, -7],
    max: [(areas.length * 12) / 2, Math.max(8, ...Object.values(models).map(m => m.bounds.max[1])), 7] }), [areas.length, models]);
  const loaded = useCallback((url: string, model: IfcModel | null, problem: string | null) => {
    if (model) setModels(previous => previous[url] === model ? previous : { ...previous, [url]: model });
    if (problem) setError(problem);
  }, []);
  const focus = (tag: string) => {
    const item = items.find(item => item.tag === tag), model = item ? models[item.ifcUrl] : undefined;
    if (!item || !model) return;
    camera.current?.fit({ min: model.bounds.min.map((v, i) => v + item.position[i]!) as Vec3,
      max: model.bounds.max.map((v, i) => v + item.position[i]!) as Vec3 });
  };
  const select = (tag: string) => { setSelected(tag); onSelect?.(tag); if (follow) focus(tag); };
  const ready = groups.length > 0 && groups.every(group => models[group.url]);
  if (!equipment.length) return <div className={styles.frame}><LoadingState label="No hay equipos. Añade un IFC al proyecto para ver la planta." /></div>;
  return <div className={styles.frame} ref={container} data-testid="plant-scene" data-phase={ready ? "ready" : error ? "error" : "loading"}>
    <SceneCanvas label="Planta isométrica de equipos sintéticos; las repeticiones son ilustrativas">
      <Studio effects={false} />
      <CameraRig bounds={bounds} handle={camera} onUserControl={() => setFollow(false)} />
      {areas.map((area, index) => <group key={area} position={[(index - (areas.length - 1) / 2) * 12, -.16, 0]}>
        <mesh position={[0, 0, 0]}><boxGeometry args={[10, .25, 10]} /><meshStandardMaterial color="#263343" roughness={.9} /></mesh>
        <Grid position={[0, .14, 0]} args={[10, 10]} cellSize={1} sectionSize={5} cellColor="#425369" sectionColor="#60768e" fadeDistance={70} />
        <Html position={[0, .25, 6.3]} center zIndexRange={[5, 0]} style={{ pointerEvents: "none" }}><span className={styles.label}>{area}</span></Html>
      </group>)}
      {groups.map(group => <PlantInstances key={group.url} {...group} selected={selected} onSelect={select} onFocus={focus} onLoaded={loaded} />)}
    </SceneCanvas>
    {!ready ? <LoadingState error={error} label="Instanciando la geometría IFC de la planta" /> : null}
    <CameraTools handle={camera} container={container} />
    <div className={styles.selectors} role="group" aria-label="Modo de cámara de la planta">
      <button className={styles.button} aria-pressed={!follow} onClick={() => { setFollow(false); camera.current?.view("iso"); }}><Eye /> Vista general</button>
      <button className={styles.button} aria-pressed={follow} onClick={() => { setFollow(true); const tag = selected ?? items[0]?.tag; if (tag) { setSelected(tag); focus(tag); } }}><LocateFixed /> Seguir equipo</button>
    </div>
    <div className={styles.badge}>Instancias sintéticas · distribución ilustrativa</div>
    <div className={styles.narration}>
      <button className={styles.button} aria-label="Recorrer el siguiente equipo" onClick={() => {
        const next = items[(items.findIndex(item => item.tag === selected) + 1) % items.length];
        if (next) { setFollow(true); setSelected(next.tag); focus(next.tag); onSelect?.(next.tag); }
      }}><Play /></button>
      <p><strong>{selected ? `${selected}${selected === "V-101" ? " · demo" : " · ilustrativo"}` : "Planta del proyecto"}</strong>
        Selecciona un tag para inspeccionarlo. Todas las instancias conservan la geometría del IFC de origen.</p>
    </div>
    <Legend />
  </div>;
}
