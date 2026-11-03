import React, { useEffect, useMemo } from 'react';
import { useThree } from '@react-three/fiber';
import { useCurrentFrame } from 'remotion';
import {
  BufferGeometry,
  CanvasTexture,
  Color,
  EdgesGeometry,
  LineBasicMaterial,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  PMREMGenerator,
  Vector3,
} from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { EASE_IN, EASE_IO, clamp01, lerp, ramp } from '../../lib/anim';
import { C } from '../../theme';
import { LIFT, MORPH, OUTRO } from '../../timeline';
import { poseAt } from './camera';
import type { ModelData, Part } from './data';

/*
  Escenas 4–6 en un solo estudio. La subida plano → modelo reproduce la Signature del producto
  (web/src/features/viewer3d/signature.tsx): papel de 12 u centrado, modelo tumbado en (−3,3; 0,04; 2,6)
  con escala (0,78; 0,65; 0,025) y rotation.x −π/2; q = ease((p − 0,28) / 0,72); alambre (1 − q)·0,85, acero q;
  evidencias encendidas una a una durante el primer 32 % del avance.
  Inspirado en wireframe-draw-on: el alambre se «dibuja» por piezas de abajo arriba.
*/

const ease = EASE_IO; // cubicBezier(.65, 0, .35, 1), el mismo que la Signature
const BIG = (name: string) => name === 'V-101' || name === 'V-101/skirt';

const CameraRig: React.FC<{ offset: number }> = ({ offset }) => {
  const frame = useCurrentFrame() + offset;
  const { camera } = useThree();
  const pose = poseAt(frame);
  camera.position.set(...pose.pos);
  camera.lookAt(new Vector3(...pose.target));
  if ('fov' in camera) {
    camera.fov = pose.fov;
    camera.updateProjectionMatrix();
  }
  return null;
};

const Environment: React.FC = () => {
  const { gl, scene } = useThree();
  useEffect(() => {
    const pm = new PMREMGenerator(gl);
    const env = pm.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    scene.environmentIntensity = 1.15;
    return () => {
      env.dispose();
      pm.dispose();
    };
  }, [gl, scene]);
  return null;
};

const contactTexture = () => {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!;
  const r = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  r.addColorStop(0, 'rgba(0,0,0,0.85)');
  r.addColorStop(0.45, 'rgba(0,0,0,0.45)');
  r.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = r;
  g.fillRect(0, 0, 256, 256);
  return new CanvasTexture(c);
};

export const VesselScene: React.FC<{ data: ModelData; offset: number }> = ({ data, offset }) => {
  const frame = useCurrentFrame() + offset;
  const { parts, paper, aspect, evidence } = data;
  const height = 12 / aspect;

  const mats = useMemo(() => {
    const steel = new MeshPhysicalMaterial({ color: new Color('#cfd5dc'), metalness: 0.85, roughness: 0.3, clearcoat: 0.2, clearcoatRoughness: 0.28, transparent: true });
    const changed = steel.clone();
    const added = steel.clone();
    const wires = new Map<string, MeshBasicMaterial>();
    parts.forEach((p) => wires.set(p.id, new MeshBasicMaterial({ color: new Color(C.skyLight), wireframe: true, transparent: true, depthWrite: false })));
    const paperMat = new MeshStandardMaterial({ map: paper, emissiveMap: paper, emissive: new Color('#ffffff'), roughness: 1, metalness: 0, transparent: true });
    const ev = evidence.map(() => new MeshBasicMaterial({ color: new Color(C.skyLight), transparent: true, opacity: 0, depthWrite: false }));
    const contact = new MeshBasicMaterial({ map: contactTexture(), transparent: true, depthWrite: false, opacity: 0 });
    // Aristas limpias (umbral 20°) para el dibujado plano → modelo, en lugar del alambre de triángulos
    const lines = new Map<string, LineBasicMaterial>();
    parts.forEach((p) => lines.set(p.id, new LineBasicMaterial({ color: new Color(C.skyLight), transparent: true, depthWrite: false, opacity: 0 })));
    // Fantasma de la rev A durante la revisión: se ve a través del acero (rayos X)
    const ghost = new LineBasicMaterial({ color: new Color(C.skyLight), transparent: true, depthWrite: false, depthTest: false, opacity: 0 });
    return { steel, changed, added, wires, paperMat, ev, contact, lines, ghost };
  }, [parts, paper, evidence]);

  // Aristas por pieza: A (geometría base) y B (objetivo de morph o malla B) para el cierre
  const edges = useMemo(() => {
    const m = new Map<string, { a: EdgesGeometry; b: EdgesGeometry }>();
    parts.forEach((part) => {
      const a = new EdgesGeometry(part.geometry, 20);
      let b = a;
      if (part.geometryB) b = new EdgesGeometry(part.geometryB, 20);
      else if (part.morph) {
        const g = new BufferGeometry();
        g.setAttribute('position', part.geometry.morphAttributes.position![0]);
        b = new EdgesGeometry(g, 20);
      }
      m.set(part.id, { a, b });
    });
    return m;
  }, [parts]);
  const GHOST = (name: string) => name === 'V-101' || name === 'V-101/skirt' || name === 'V-101/top_head' || name.includes('N3');

  // ── Avance de la firma (0–1) y fases ──
  const p = clamp01((frame - LIFT.evidence) / (LIFT.end - LIFT.evidence));
  const q = ease(clamp01((p - 0.28) / 0.72));
  const morph = ramp(frame, MORPH.start, MORPH.end, EASE_IO);
  const collapse = ramp(frame, OUTRO.collapse + 4, OUTRO.collapse + 36, EASE_IN);
  const tint = ramp(frame, MORPH.start, MORPH.start + 24) * (1 - ramp(frame, OUTRO.collapse - 10, OUTRO.collapse + 10));

  // Acero: opacidad q; en el cierre vuelve a alambre antes de recogerse
  const steelOp = q * (1 - ramp(frame, OUTRO.collapse, OUTRO.collapse + 16));
  for (const m of [mats.steel, mats.changed]) {
    m.opacity = steelOp;
    m.depthWrite = steelOp > 0.99;
  }
  const orange = new Color(C.revision);
  mats.changed.emissive = orange;
  mats.changed.emissiveIntensity = 0.4 * tint;
  mats.changed.color = new Color('#cfd5dc').lerp(new Color('#f0b98c'), 0.6 * tint);
  mats.ghost.opacity = 0.55 * ramp(frame, MORPH.start, MORPH.start + 20) * (1 - ramp(frame, OUTRO.collapse - 12, OUTRO.collapse + 2));
  mats.added.emissive = orange;
  mats.added.emissiveIntensity = 0.45 * tint;
  mats.added.color = new Color('#e7b38a');
  mats.added.opacity = ramp(frame, MORPH.start + 40, MORPH.end) * steelOp;
  mats.added.depthWrite = mats.added.opacity > 0.99;

  // Alambre: se dibuja por piezas de abajo arriba (0,04–0,30 del avance) y se apaga con q
  const back = ramp(frame, OUTRO.collapse, OUTRO.collapse + 12) * (1 - collapse);
  parts.forEach((part) => {
    const w = mats.wires.get(part.id)!;
    const l = mats.lines.get(part.id)!;
    const k = clamp01(part.yMid / 7.8);
    const draw = clamp01((p - 0.04 - k * 0.2) / 0.08);
    const show = part.added ? 0 : 1;
    l.opacity = show * (draw * (1 - q) * 0.9 + back * 0.7);
    // En la revisión, solo las toberas que cambian (N3) se repasan con alambre naranja, como el modo Rayos X de la app.
    // La virola y el faldón cambian de longitud: eso lo cuentan el fantasma de la rev A y las cotas.
    w.opacity = part.changed && !part.added && !BIG(part.name) ? 0.42 * tint : 0;
    w.color = new Color(C.revision);
  });

  // Papel y evidencias (lógica de la Signature)
  const paperOut = 1 - ramp(frame, OUTRO.collapse, OUTRO.collapse + 30);
  mats.paperMat.opacity = (1 - q * 0.72) * paperOut * ramp(frame, 600, 616);
  mats.paperMat.emissiveIntensity = lerp(q, 0.42, 0.1);
  mats.paperMat.color = new Color('#ffffff').lerp(new Color('#2a2d33'), q);
  mats.ev.forEach((m, i) => {
    const n = evidence.length;
    const active = p < 0.32 && i === Math.min(n - 1, Math.floor((p / 0.32) * n));
    m.opacity = p <= 0 ? 0 : active ? 0.55 : p < 0.32 && i < (p / 0.32) * n ? 0.15 : 0.02 * (1 - q);
  });
  mats.contact.opacity = 0.75 * q * q * (1 - collapse);

  // Transformación del modelo
  const rot = (-(1 - q) * Math.PI) / 2;
  const pos: [number, number, number] = [-3.3 * (1 - q), 0.04, 2.6 * (1 - q)];
  const scl: [number, number, number] = [0.78 + 0.22 * q, 0.65 + 0.35 * q, 0.025 + 0.975 * q];
  // Recogida final hacia el centro del recipiente
  const cs = lerp(collapse, 1, 0.001);
  const cy = 3.9;

  const mesh = (part: Part) => {
    const m = part.added ? mats.added : part.changed && !BIG(part.name) ? mats.changed : mats.steel;
    const e = edges.get(part.id)!;
    const showB = part.geometryB && morph >= 1;
    const geo = showB ? part.geometryB! : part.geometry;
    const st = part.stretch && !showB ? part.stretch : null;
    const sy = st ? lerp(morph, 1, st.sy) : 1;
    const ty = st ? lerp(morph, 0, st.ty) : 0;
    const grow = part.added ? lerp(ramp(frame, MORPH.start + 40, MORPH.end, EASE_IO), 0.6, 1) : 1;
    const inner = (
      <>
        <mesh geometry={geo} material={m} morphTargetInfluences={part.morph ? [morph] : undefined} />
        <mesh geometry={geo} material={mats.wires.get(part.id)!} morphTargetInfluences={part.morph ? [morph] : undefined} />
        <lineSegments geometry={showB || (part.morph && morph >= 0.5) ? e.b : e.a} material={mats.lines.get(part.id)!} />
      </>
    );
    const ghost = !part.added && GHOST(part.name) ? <lineSegments geometry={e.a} material={mats.ghost} renderOrder={5} /> : null;
    if (part.added) {
      const [x, y, z] = part.center;
      return (
        <group key={part.id} position={[x, y, z]} scale={grow}>
          <group position={[-x, -y, -z]}>{inner}</group>
        </group>
      );
    }
    return (
      <React.Fragment key={part.id}>
        <group position={[0, ty, 0]} scale={[1, sy, 1]}>
          {inner}
        </group>
        {ghost}
      </React.Fragment>
    );
  };

  return (
    <>
      <CameraRig offset={offset} />
      <Environment />
      <color attach="background" args={[C.bg]} />
      <ambientLight intensity={0.4} color={C.text} />
      <directionalLight position={[5, 9, 7]} intensity={2.6} color="#ffffff" />
      <directionalLight position={[-6, 5, -3]} intensity={1.6} color={C.skyLight} />
      {/* Relleno del lado de revisión (N3/N4), solo mientras se muestran los cambios */}
      <directionalLight position={[-8, 6, 9]} intensity={2.4 * ramp(frame, 930, 990) * (1 - collapse)} color="#ffffff" />
      {/* Luz cenital celeste controlada para el plano heroico */}
      <spotLight position={[2.5, 16, 4]} angle={0.42} penumbra={0.85} intensity={lerp(q, 0, 900) * (1 - collapse)} color="#d6efff" distance={40} decay={2} />

      <mesh rotation-x={-Math.PI / 2} position={[0, -0.02, 0]} material={mats.paperMat} renderOrder={0}>
        <planeGeometry args={[12, height]} />
      </mesh>
      {evidence.map((e, i) => {
        const [x0, y0, x1, y1] = e.bbox;
        return (
          <mesh key={e.path} rotation-x={-Math.PI / 2} position={[(x0 + x1 - 1) * 6, -0.005, ((y0 + y1 - 1) * height) / 2]} material={mats.ev[i]} renderOrder={2}>
            <planeGeometry args={[(x1 - x0) * 12 + 0.08, (y1 - y0) * height + 0.05]} />
          </mesh>
        );
      })}
      <mesh rotation-x={-Math.PI / 2} position={[0, 0.003, 0]} material={mats.contact} renderOrder={1}>
        <planeGeometry args={[4.6, 4.6]} />
      </mesh>

      <group position={[0, cy, 0]} scale={cs}>
        <group position={[0, -cy, 0]}>
          <group rotation-x={rot} position={pos} scale={scl}>
            {parts.map(mesh)}
          </group>
        </group>
      </group>
    </>
  );
};
