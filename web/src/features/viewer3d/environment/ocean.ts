import { Group, Mesh } from "three";
import { createGulls } from "./birds";
import { MeshBuilder } from "./builder";
import { waterlineContacts } from "./contacts";
import { createFlames } from "./lights-fx";
import { propMesh } from "./materials";
import { sceneGroup, standardScene, type EnvironmentScene, type SceneContext } from "./scene";
import { buildDistantPlatform, buildSupplyVessel } from "./vessels";
import { buildWaves, floatingPose, OCEAN_WAVES, type Wave } from "./waves";
import { createWater, type VesselWake } from "./water";

/*
  Mar abierto: lámina con oleaje de Gerstner hasta el horizonte, espuma donde las patas del
  jacket cortan el agua (leída del IFC), buque de apoyo que navega despacio y cabecea con la
  misma ola que se dibuja, gaviotas alrededor de la cubierta y plataformas lejanas en la bruma
  con sus antorchas.
*/

/** Trayectoria circular de un barco: posición, rumbo y estela coherentes con el shader. */
export type VesselRoute = { cx: number; cz: number; radius: number; speed: number; angle: number };

export function routePosition(route: VesselRoute, t: number) {
  const theta = route.angle + route.speed * t;
  const x = route.cx + Math.cos(theta) * route.radius;
  const z = route.cz + Math.sin(theta) * route.radius;
  const sign = Math.sign(route.speed) || 1;
  const heading = Math.atan2(Math.cos(theta) * sign, -Math.sin(theta) * sign);
  return { x, z, heading };
}

/** Coloca un barco sobre la ola: rumbo, arfada, cabeceo y balance. */
export function poseVessel(group: Group, waves: readonly Wave[], level: number, x: number, z: number, heading: number, length: number, beam: number, t: number, response: number) {
  const pose = floatingPose(waves, x, z, heading, length, beam, t, response);
  group.position.set(x, level + pose.heave, z);
  group.rotation.set(-pose.roll, -heading, pose.pitch, "YZX");
  group.updateMatrix();
}

export function buildOcean(ctx: SceneContext): EnvironmentScene {
  const { site, palette, quality, atmosphere } = ctx;
  const high = quality === "high";
  const level = palette.waterLevel;
  const waves = buildWaves(OCEAN_WAVES);
  const wind: [number, number] = [palette.wind[0], palette.wind[1]];
  const water = createWater(atmosphere, {
    waves, level, site, quality, deep: "#062436", scatter: "#1b8a8c", current: wind,
  });

  // Buque de apoyo: círculo amplio que pasa por detrás de la plataforma en la vista inicial.
  const vessel = buildSupplyVessel();
  const route: VesselRoute = { cx: site.x - 60, cz: site.z - 90, radius: 330, speed: 3.4 / 330, angle: -2.2 - (3.4 / 330) * palette.start };
  const ship = new Group();
  ship.name = "entorno-buque-apoyo";
  ship.matrixAutoUpdate = false;
  ship.add(propMesh(vessel.builder, ctx.props, "entorno-buque-apoyo-casco"));
  const wakes: VesselWake[] = [{
    cx: route.cx, cz: route.cz, radius: route.radius, speed: route.speed, angle: route.angle,
    beam: vessel.beam, duration: 75, strength: 0.95,
  }];
  water.setVessels(wakes);

  // Plataformas lejanas en la bruma, con sus antorchas.
  const far = new MeshBuilder();
  const flares: [number, number, number][] = [];
  const placements = [[-2350, -1750, 0.6], [2600, -2300, 2.2], [-900, -3600, 1.3], ...(high ? [[3300, 900, 4.1]] : [])] as const;
  placements.forEach(([dx, dz, heading], i) => {
    flares.push(buildDistantPlatform(far, site.x + dx, site.z + dz, heading, 31 + i * 17));
  });
  const platforms = propMesh(far, ctx.props, "entorno-plataformas-lejanas");
  const flames = createFlames(atmosphere, flares.map((base, i) => ({ base, height: 11, width: 4.2, intensity: 5, seed: i * 3.1 + 0.4 })));

  const gulls = createGulls(atmosphere, {
    count: high ? 18 : 10, seed: 404, center: [site.x, site.z],
    radius: [Math.max(28, site.radius * 0.6), site.radius * 1.5], altitude: [site.maxY + 4, site.maxY + 26],
  });

  const children: Mesh[] = [water.mesh, platforms, flames, gulls];
  const group = sceneGroup("entorno-mar", [...children, ship]);
  const update = (t: number) => {
    const { x, z, heading } = routePosition(route, t);
    poseVessel(ship, waves, level, x, z, heading, vessel.length, vessel.beam, t, 0.55);
  };
  update(palette.start);
  return standardScene(group, update, {
    setProducts: products => water.setContacts(waterlineContacts(products, level)),
  });
}
