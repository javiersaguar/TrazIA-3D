"use client";

import { BRAND } from "@/lib/brand";

import { Line } from "@react-three/drei";
import { useMemo } from "react";
import { Vector3 } from "three";
import type { IfcModel, Vec3 } from "@/workers/ifc-protocol";
import type { PreparedProduct } from "./model-resource";
import { elementForField } from "./semantic";
import type { Annotation } from "./types";
import styles from "./viewer.module.css";
import { SceneLabel as Html } from "./stage";

function Dimension({ from, to, anchorFrom, anchorTo, annotation }: {
  from: Vec3; to: Vec3; anchorFrom: Vec3; anchorTo: Vec3; annotation: Annotation;
}) {
  const midpoint = from.map((v, i) => (v + to[i]!) / 2) as Vec3;
  const color = annotation.confidence >= .9 ? BRAND.skyPale : annotation.confidence >= .6 ? BRAND.warning : BRAND.danger;
  const vector = new Vector3(...to).sub(new Vector3(...from)).normalize().multiplyScalar(.1);
  const tick: Vec3 = Math.abs(vector.y) > .05 ? [.09, 0, .05] : [0, .09, .05];
  return <group>
    <Line points={[from, to]} color={color} lineWidth={1} />
    <Line points={[anchorFrom, from]} color={color} lineWidth={.7} dashed dashSize={.05} gapSize={.04} />
    <Line points={[anchorTo, to]} color={color} lineWidth={.7} dashed dashSize={.05} gapSize={.04} />
    {[from, to].map((point, i) => <Line key={i} points={[
      point.map((v, j) => v - tick[j]!) as Vec3, point.map((v, j) => v + tick[j]!) as Vec3,
    ]} color={color} lineWidth={1.3} />)}
    <Html position={midpoint} center style={{ pointerEvents: "none" }} zIndexRange={[8, 0]}>
      <div className={styles.dimension} style={{ color }} title={`${annotation.label}. Valor JSON. Confianza ${annotation.confidence}`}>
        {annotation.value.toLocaleString("es-ES")} {annotation.unit}
      </div>
    </Html>
  </group>;
}

export function Dimensions({ annotations, products }: { annotations: Annotation[]; products: PreparedProduct[] }) {
  return <>{annotations.filter(a => a.unit === "mm" && !a.id.startsWith("attributes.")).slice(0, 3).map((annotation, index) => {
    const id = elementForField(annotation.id), product = products.find(p => p.semanticId === id);
    if (!product) return null;
    const { min, max } = product.bounds, center = product.center;
    const offset = .45 + index * .28;
    let anchorFrom: Vec3 = [min[0], center[1], center[2]], anchorTo: Vec3 = [max[0], center[1], center[2]];
    let from: Vec3 = [min[0], max[1] + offset, center[2]], to: Vec3 = [max[0], max[1] + offset, center[2]];
    if (annotation.id === "skirt_thickness") {
      let inner = Infinity, outer = 0;
      for (const part of product.parts) for (let i = 0; i < part.positions.length; i += 3) {
        const radius = Math.hypot(part.positions[i]!, part.positions[i + 2]!);
        if (radius > 1e-5) { inner = Math.min(inner, radius); outer = Math.max(outer, radius); }
      }
      anchorFrom = [center[0] + inner, max[1], center[2]]; anchorTo = [center[0] + outer, max[1], center[2]];
      from = [anchorFrom[0], max[1] + offset, center[2]]; to = [anchorTo[0], max[1] + offset, center[2]];
    } else if (annotation.id.endsWith("elevation")) {
      anchorFrom = [center[0], 0, center[2]]; anchorTo = center;
      from = [center[0] + offset, 0, center[2]]; to = [center[0] + offset, center[1], center[2]];
    } else if (annotation.id.endsWith("diameter") && id.startsWith("nozzle:")) {
      anchorFrom = [center[0], min[1], center[2]]; anchorTo = [center[0], max[1], center[2]];
      from = [center[0] + offset, min[1], center[2]]; to = [center[0] + offset, max[1], center[2]];
    } else if (annotation.id.endsWith("projection")) {
      const shell = products.find(p => p.semanticId === "shell");
      const axis = new Vector3(center[0] - (shell?.center[0] ?? 0), 0, center[2] - (shell?.center[2] ?? 0)).normalize();
      let low = Infinity, high = -Infinity;
      for (const part of product.parts) for (let i = 0; i < part.positions.length; i += 3) {
        const dot = part.positions[i]! * axis.x + part.positions[i + 2]! * axis.z;
        low = Math.min(low, dot); high = Math.max(high, dot);
      }
      anchorFrom = [center[0] + low * axis.x, center[1], center[2] + low * axis.z];
      anchorTo = [center[0] + high * axis.x, center[1], center[2] + high * axis.z];
      from = [anchorFrom[0], center[1] + offset, anchorFrom[2]];
      to = [anchorTo[0], center[1] + offset, anchorTo[2]];
    } else if (!annotation.id.endsWith("diameter")) {
      anchorFrom = [min[0], min[1], center[2]]; anchorTo = [min[0], max[1], center[2]];
      from = [min[0] - offset, min[1], center[2]]; to = [min[0] - offset, max[1], center[2]];
    }
    return <Dimension key={annotation.id} {...{ from, to, anchorFrom, anchorTo, annotation }} />;
  })}</>;
}

export function AzimuthRing({ model }: { model: IfcModel }) {
  const shell = model.products.find(p => p.semanticId === "shell");
  const x = shell?.center[0] ?? 0, z = shell?.center[2] ?? 0, y = model.bounds.min[1] + .03;
  const radius = Math.max(Math.abs(model.bounds.max[0] - x), Math.abs(model.bounds.min[0] - x),
    Math.abs(model.bounds.max[2] - z), Math.abs(model.bounds.min[2] - z)) + .5;
  const ring = useMemo(() => Array.from({ length: 97 }, (_, i) => {
    const angle = i / 96 * Math.PI * 2;
    return [radius * Math.cos(angle), .03, -radius * Math.sin(angle)] as Vec3;
  }), [radius]);
  return <group position={[x, y - .03, z]}>
    <Line points={ring} color={BRAND.steelDark} lineWidth={1} />
    {Array.from({ length: 12 }, (_, i) => {
      const angle = i * Math.PI / 6;
      return <group key={i}>
        <Line points={[[radius * .96 * Math.cos(angle), .03, -radius * .96 * Math.sin(angle)],
          [radius * Math.cos(angle), .03, -radius * Math.sin(angle)]]} color={BRAND.textMuted} lineWidth={1} />
        <Html position={[(radius + .16) * Math.cos(angle), .03, -(radius + .16) * Math.sin(angle)]} center
          zIndexRange={[5, 0]} style={{ pointerEvents: "none", color: BRAND.textMuted, fontSize: 10 }}>{i * 30}°</Html>
      </group>;
    })}
    {model.products.filter(p => p.semanticId.startsWith("nozzle:")).map(product => {
      const angle = Math.atan2(-(product.center[2] - z), product.center[0] - x);
      const point: Vec3 = [radius * Math.cos(angle), .04, -radius * Math.sin(angle)];
      return <group key={product.globalId}>
        <Line points={[[0, .04, 0], point]} color={BRAND.skyLight} dashed dashSize={.08} gapSize={.07} lineWidth={.8} />
        <Html position={point} center zIndexRange={[6, 0]} style={{ pointerEvents: "none" }}>
          <span className={styles.label}>{product.semanticId.replace("nozzle:", "")} · {((angle * 180 / Math.PI + 360) % 360).toFixed(0)}°</span>
        </Html>
      </group>;
    })}
  </group>;
}
