import type { AtmosphereUniforms } from "./atmosphere";
import { buildCoast } from "./coast";
import { buildDesert } from "./desert";
import { buildIndustrial } from "./industrial";
import { createPropMaterial } from "./materials";
import { buildOcean } from "./ocean";
import type { EnvironmentId, Palette, Quality } from "./palettes";
import type { EnvironmentScene, SceneContext } from "./scene";
import type { SiteFrame } from "./site";

export { PALETTES } from "./palettes";
export type { EnvironmentId, Quality } from "./palettes";
export type { EnvironmentScene } from "./scene";

const BUILDERS: Record<EnvironmentId, (ctx: SceneContext) => EnvironmentScene> = {
  ocean: buildOcean,
  coast: buildCoast,
  desert: buildDesert,
  industrial: buildIndustrial,
};

/** Construye el entorno completo (sin luces ni cielo, que son comunes). */
export function buildEnvironment(options: {
  id: EnvironmentId;
  palette: Palette;
  site: SiteFrame;
  quality: Quality;
  atmosphere: AtmosphereUniforms;
}): EnvironmentScene {
  const props = createPropMaterial(options.atmosphere);
  const facets = createPropMaterial(options.atmosphere, { key: "facetas", flatShading: true });
  const scene = BUILDERS[options.id]({ ...options, props, facets });
  scene.group.userData.environment = options.id;
  return scene;
}
