import { AdditiveBlending, Color, DoubleSide, MeshPhysicalMaterial, ShaderMaterial } from "three";
import { BRAND } from "@/lib/brand";
import type { Finish } from "../showcase3d/equipment-geometry";
import { brushedTextures } from "../viewer3d/brushed-textures";

export const scanProgress = (value: number) => Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
export const scanHeight = (min: number, max: number, value: number) => min + (max - min) * scanProgress(value);

export function createHologram(minY: number, maxY: number) {
  return new ShaderMaterial({
    transparent: true, depthWrite: false, side: DoubleSide, blending: AdditiveBlending,
    uniforms: { uColor: { value: new Color(BRAND.hologram) }, uTime: { value: 0 },
      uProgress: { value: 0 }, uMin: { value: minY }, uMax: { value: maxY } },
    vertexShader: `
      varying vec3 vWorld; varying vec3 vNormal; varying vec3 vView;
      void main() {
        vec4 p = vec4(position, 1.); vec3 n = normal;
        #ifdef USE_INSTANCING
          p = instanceMatrix * p; n = mat3(instanceMatrix) * n;
        #endif
        vec4 world = modelMatrix * p; vec4 view = viewMatrix * world;
        vWorld = world.xyz; vNormal = normalize(normalMatrix * n); vView = -view.xyz;
        gl_Position = projectionMatrix * view;
      }`,
    fragmentShader: `
      uniform vec3 uColor; uniform float uTime; uniform float uProgress; uniform float uMin; uniform float uMax;
      varying vec3 vWorld; varying vec3 vNormal; varying vec3 vView;
      void main() {
        float fresnel = pow(1. - abs(dot(normalize(vNormal), normalize(vView))), 2.);
        vec3 grid = abs(fract(vWorld * 5. - .5) - .5) / max(fwidth(vWorld * 5.), vec3(.001));
        float line = 1. - min(min(grid.x, grid.y), grid.z);
        float scan = pow(.5 + .5 * sin(vWorld.y * 90. - uTime * 2.5), 18.);
        float alpha = .06 + fresnel * .65 + max(0., line) * .12 + scan * .12;
        float threshold = mix(uMin, uMax, uProgress);
        if (uProgress > .999) discard;
        if (uProgress > .001) alpha *= smoothstep(threshold - .04, threshold + .04, vWorld.y);
        gl_FragColor = vec4(uColor * (1. + fresnel), alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }`,
  });
}

export function createRevealSurface(minY: number, maxY: number, finish: Finish = "steel") {
  const colors = { steel: BRAND.steel, paint: BRAND.paint, machined: BRAND.steel, bolts: BRAND.steelDark };
  const uniforms = {
    uReveal: { value: 0 }, uMinY: { value: minY }, uMaxY: { value: maxY },
    uEdge: { value: new Color(BRAND.skyLight) },
  };
  const material = new MeshPhysicalMaterial({ color: colors[finish], metalness: finish === "paint" ? .5 : .85,
    roughness: finish === "paint" ? .55 : finish === "machined" ? .2 : .34, clearcoat: .2,
    ...brushedTextures() });
  material.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = "varying float vRevealY;\n" + shader.vertexShader;
    shader.vertexShader = shader.vertexShader.replace("#include <begin_vertex>", `
      #include <begin_vertex>
      vec4 revealPosition = vec4(transformed, 1.);
      #ifdef USE_INSTANCING
        revealPosition = instanceMatrix * revealPosition;
      #endif
      vRevealY = (modelMatrix * revealPosition).y;
    `);
    shader.fragmentShader = `uniform float uReveal; uniform float uMinY; uniform float uMaxY;
      uniform vec3 uEdge; varying float vRevealY;\n` + shader.fragmentShader;
    shader.fragmentShader = shader.fragmentShader.replace("#include <clipping_planes_fragment>", `
      #include <clipping_planes_fragment>
      float revealThreshold = mix(uMinY, uMaxY, uReveal);
      if (uReveal < .0001 || (uReveal < .9999 && vRevealY > revealThreshold)) discard;
    `).replace("#include <emissivemap_fragment>", `
      #include <emissivemap_fragment>
      float edgeWidth = max(.04, (uMaxY - uMinY) * .018);
      float revealEdge = uReveal > .9999 ? 0. : 1. - smoothstep(0., edgeWidth, abs(vRevealY - revealThreshold));
      totalEmissiveRadiance += uEdge * revealEdge * 2.8;
    `);
  };
  material.customProgramCacheKey = () => "trazia-reveal-v1";
  return { material, uniforms };
}
