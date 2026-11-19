"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useState } from "react";
import type { Bounds } from "@/workers/ifc-protocol";
import {
  applySceneEnvironment,
  createAtmosphereUniforms,
  createLights,
  createSky,
  EnvironmentClock,
  renderSkyEnvironment,
  setAtmosphereFrame,
  setAtmosphereMotion,
} from "./environment/atmosphere";
import { EnvironmentEffects } from "./environment/effects";
import { buildEnvironment } from "./environment/index";
import { PALETTES, type EnvironmentId, type Quality } from "./environment/palettes";
import { detectQuality, FrameBudget } from "./environment/quality";
import { siteFrame } from "./environment/site";
import type { PreparedProduct } from "./model-resource";
import { useSceneActivity } from "./stage";

/*
  Entornos de los proyectos de proceso (contrato C3).

  Aporta toda la luz del escenario (sol con sombras ajustadas a la planta, luz hemisférica y
  mapa de entorno PMREM del propio cielo), el cielo, la niebla radial alrededor de la planta, el
  suelo o el agua, el atrezo animado y el posprocesado (oclusión ambiental, bloom, tono AgX,
  contorno con rayos X de la selección, SMAA). No toca ningún producto IFC ni la cámara.

  Animación: solo con `motion` y la escena activa (visible y en pantalla). Mientras anima,
  invalida un fotograma cada vez; parada, la escena queda quieta y completa en el último
  instante. Todo es determinista: el mismo instante da la misma imagen.
*/

export type ProcessEnvironmentProps = {
  id: EnvironmentId;
  motion: boolean;
  bounds: Bounds;
  products?: PreparedProduct[];
  quality?: Quality;
};

export function ProcessEnvironment({ id, motion, bounds, products, quality: requested }: ProcessEnvironmentProps) {
  const gl = useThree(state => state.gl);
  const scene = useThree(state => state.scene);
  const invalidate = useThree(state => state.invalidate);
  const active = useSceneActivity();
  const animate = motion && active;
  const [detected] = useState<Quality>(() => detectQuality(gl));
  const [downgraded, setDowngraded] = useState(false);
  const quality: Quality = requested ?? (downgraded ? "low" : detected);
  const palette = PALETTES[id];
  const boundsKey = [...bounds.min, ...bounds.max].map(v => v.toFixed(1)).join(":");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const site = useMemo(() => siteFrame(bounds), [boundsKey]);
  const [clock] = useState(() => new EnvironmentClock(palette.start));
  const atmosphere = useMemo(() => {
    const uniforms = createAtmosphereUniforms(palette, site);
    clock.sync(uniforms);
    return uniforms;
  }, [clock, palette, site]);
  const environment = useMemo(
    () => buildEnvironment({ id, palette, site, quality, atmosphere }),
    [id, palette, site, quality, atmosphere],
  );
  const sky = useMemo(() => createSky(atmosphere, "background", quality), [atmosphere, quality]);
  const lights = useMemo(() => createLights(palette, site, quality), [palette, site, quality]);
  const [budget] = useState(() => new FrameBudget());

  useEffect(() => () => environment.dispose(), [environment]);
  useEffect(() => () => {
    sky.geometry.dispose();
    (sky.material as { dispose(): void }).dispose();
  }, [sky]);
  useEffect(() => () => lights.dispose(), [lights]);
  useEffect(() => {
    environment.setProducts(products ?? []);
    invalidate();
  }, [environment, products, invalidate]);
  useEffect(() => {
    // El metal de la planta refleja este cielo (y no el estudio neutro).
    const map = renderSkyEnvironment(gl, atmosphere, quality);
    const restore = applySceneEnvironment(scene, map.texture, palette.environmentIntensity);
    invalidate();
    return () => {
      restore();
      map.dispose();
    };
  }, [gl, scene, atmosphere, quality, palette, invalidate]);
  useEffect(() => {
    setAtmosphereMotion(atmosphere, animate);
    budget.reset();
    invalidate();
  }, [animate, atmosphere, budget, invalidate]);

  useFrame((state, delta) => {
    setAtmosphereFrame(atmosphere, state.camera.far);
    if (!animate) return;
    environment.update(clock.advance(delta, atmosphere));
    if (!requested && !downgraded && budget.sample(delta)) setDowngraded(true);
    state.invalidate();
  });

  return (
    <>
      <color attach="background" args={[palette.sky.haze]} />
      <primitive object={sky} />
      <primitive object={lights.group} />
      <primitive object={environment.group} />
      <EnvironmentEffects quality={quality} exposure={palette.exposure} />
    </>
  );
}
