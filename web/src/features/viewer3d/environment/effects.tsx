"use client";

import { useThree } from "@react-three/fiber";
import {
  Bloom,
  EffectComposer,
  N8AO,
  Outline,
  SMAA,
  ToneMapping,
  Vignette,
} from "@react-three/postprocessing";
import { useCallback, useEffect } from "react";
import { HalfFloatType } from "three";
import { BRAND } from "@/lib/brand";
import type { Quality } from "./palettes";

/*
  Posprocesado de los escenarios.

  - Oclusión ambiental N8AO a media resolución (solo en calidad alta). Las piezas IFC usan
    materiales transparentes con escritura de profundidad: se desactiva el modo "consciente de
    transparencias" de N8AO, que volvería a pintar la escena dos veces por fotograma.
  - Bloom con umbral alto: solo brillan llamas, balizas, el disco solar y sus destellos en el agua.
  - Tono AgX en el compositor (el compositor apaga el del renderer) y exposición por entorno.
  - Contorno con rayos X ligado a la <Selection> del visor: la silueta de lo seleccionado se ve
    a través de lo que la tape.
  - SMAA y una viñeta suave.

  Las constantes numéricas son las de `postprocessing` (no es dependencia directa de la web):
  BlendFunction.ALPHA = 1, KernelSize.VERY_SMALL = 0, ToneMappingMode.AGX = 7.
*/
const ALPHA_BLEND = 1;
const VERY_SMALL_KERNEL = 0;
const AGX = 7;

type AoPass = { configuration: { transparencyAware: boolean } };

export function EnvironmentEffects({ quality, exposure }: { quality: Quality; exposure: number }) {
  const get = useThree(state => state.get);
  const invalidate = useThree(state => state.invalidate);
  const configureAo = useCallback((pass: AoPass | null) => {
    if (pass) pass.configuration.transparencyAware = false;
  }, []);
  useEffect(() => {
    const { gl } = get();
    const previous = gl.toneMappingExposure;
    gl.toneMappingExposure = exposure;
    invalidate();
    return () => { gl.toneMappingExposure = previous; };
  }, [exposure, get, invalidate]);
  const high = quality === "high";
  return (
    <EffectComposer multisampling={0} autoClear={false} frameBufferType={HalfFloatType}>
      {high ? (
        <N8AO ref={configureAo} halfRes quality="medium" aoRadius={2.6} distanceFalloff={0.55} intensity={2.1}
          aoSamples={12} denoiseSamples={6} denoiseRadius={10} color="#0b0d10" />
      ) : <></>}
      <Bloom mipmapBlur luminanceThreshold={2.2} luminanceSmoothing={0.45} intensity={high ? 0.85 : 0.6}
        radius={0.66} levels={high ? 7 : 5} />
      <ToneMapping mode={AGX} />
      <Outline xRay blur edgeStrength={5} kernelSize={VERY_SMALL_KERNEL}
        blendFunction={ALPHA_BLEND} visibleEdgeColor={BRAND.skyPale} hiddenEdgeColor={BRAND.sky}
        resolutionScale={high ? 0.75 : 0.5} />
      <SMAA />
      {high ? <Vignette offset={0.34} darkness={0.34} /> : <></>}
    </EffectComposer>
  );
}
