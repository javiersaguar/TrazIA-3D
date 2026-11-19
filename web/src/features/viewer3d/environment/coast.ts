import { Group } from "three";
import { createGulls } from "./birds";
import { MeshBuilder } from "./builder";
import { waterlineContacts } from "./contacts";
import { propMesh } from "./materials";
import { poseVessel, routePosition, type VesselRoute } from "./ocean";
import { sceneGroup, standardScene, type SceneContext } from "./scene";
import { createTerrain } from "./terrain";
import { buildLngCarrier, buildTug } from "./vessels";
import { buildWaves, COAST_WAVES } from "./waves";
import { createWater } from "./water";

const shoreOffset = (z: number) => Math.min(2, Math.abs(z) * .04) * Math.sin(z * .016);
const shoreHeight = (distance: number) => Math.max(-11, Math.min(-.14, -.14 + distance * .36));

export function buildCoast({ site, palette, quality, atmosphere, props, facets }: SceneContext) {
  const pier = site.minY > -4 && site.minY < -1.5;
  const edge = pier ? -19 : site.x - site.halfX - 9;
  const level = palette.waterLevel;
  const waves = buildWaves(COAST_WAVES);
  const shore = `
    float shoreDistance(vec2 p) {
      float z = p.y - ${site.z.toFixed(3)};
      return p.x - ${edge.toFixed(3)} - min(2., abs(z) * .04) * sin(z * .016);
    }
    float seabed(vec2 p) { return clamp(-.14 + shoreDistance(p) * .36, -11., -.14); }
    float shelter(vec2 p) { return mix(.14,1.,smoothstep(18.,116.,-shoreDistance(p))); }
  `;
  const water = createWater(atmosphere, {
    waves, level, site, quality, deep: "#0a3247", scatter: "#3e8a8e", shallow: "#549098",
    current: [palette.wind[0], palette.wind[1]], shore,
  });
  const ground = createTerrain({
    site, quality, atmosphere, name: "costa",
    height: (x, z) => shoreHeight(x - edge - shoreOffset(z - site.z)),
    glsl: `${shore}
      float terrainHeight(vec2 p) { return seabed(p); }
      void terrainSurface(vec3 world, inout vec3 n, inout vec3 albedo, inout float rough) {
        float d = shoreDistance(world.xz);
        float grain = 0.5 + 0.5 * sin(world.x * 2.24 + cos(world.z * 3.6));
        albedo = mix(vec3(.27,.24,.18), vec3(.185,.203,.207), smoothstep(2.,16.,d)) * (.78+.22*grain);
        rough = .88;
      }`,
  });
  const coast = new MeshBuilder();
  for (let i = -24; i <= 24; i++) {
    const z = site.z + i * 4.1;
    if (Math.abs(z - site.z) < 13) continue;
    coast.color(i % 2 === 0 ? "#635e55" : "#827969", .96)
      .box(edge + shoreOffset(z - site.z) - .9, -.4, z, 2.2, 1.33, 3.8);
  }
  const jetty = new Group();
  const carrier = buildLngCarrier();
  jetty.matrixAutoUpdate = false;
  jetty.add(propMesh(carrier.builder, props, "entorno-buque-gnl"));
  const tugDesign = buildTug();
  const tug = new Group();
  tug.matrixAutoUpdate = false;
  tug.add(propMesh(tugDesign.builder, props, "entorno-remolcador"));
  const route: VesselRoute = { cx: edge - 123, cz: site.z - 48, radius: 62, speed: .034, angle: -1.8 };
  water.setVessels([{ ...route, beam: tugDesign.beam, duration: 34, strength: .9 }]);
  const gulls = createGulls(atmosphere, {
    count: quality === "high" ? 12 : 6, seed: 9863, center: [edge - 55, site.z],
    radius: [22, 120], altitude: [13, 37],
  });
  const group = sceneGroup("entorno-costa", [
    ground, water.mesh, propMesh(coast, facets, "entorno-escollera"), jetty, tug, gulls,
  ]);
  const update = (time: number) => {
    poseVessel(jetty, waves, level, edge - 44, site.z - 45, 1.57, carrier.length, carrier.beam, time, .26);
    const p = routePosition(route, time);
    poseVessel(tug, waves, level, p.x, p.z, p.heading, tugDesign.length, tugDesign.beam, time, .43);
  };
  update(palette.start);
  return standardScene(group, update, {
    setProducts: products => water.setContacts(waterlineContacts(products, level)),
  });
}
