import { MeshBuilder } from "./builder";
import { createBeacons } from "./lights-fx";
import { propMesh } from "./materials";
import { createParticles } from "./particles";
import { sceneGroup, standardScene, type SceneContext } from "./scene";
import { createTerrain } from "./terrain";

export function buildIndustrial({ site, quality, atmosphere, props }: SceneContext) {
  const ground = createTerrain({
    site, quality, atmosphere, height: () => -.18, name: "industria",
    glsl: `
      float terrainHeight(vec2 p) { return -.18; }
      void terrainSurface(vec3 world, inout vec3 n, inout vec3 albedo, inout float rough) {
        vec2 site = world.xz - vec2(${site.x.toFixed(3)}, ${site.z.toFixed(3)});
        float grain = .5+.5*sin(world.x*8.1 + 2.*sin(world.z*2.3));
        float aisle = 1. - smoothstep(3.7,4.1,abs(mod(site.x+35.,70.)-35.));
        aisle = max(aisle, 1. - smoothstep(3.8,4.2,abs(site.y + 39.)));
        albedo = mix(vec3(.213,.188,.155),vec3(.094,.104,.114),aisle)*(.81+.19*grain);
        rough = .92;
      }`,
  });
  const yard = new MeshBuilder();
  const steam: [number, number, number][] = [];
  const high = quality === "high";
  const count = high ? 6 : 4;
  for (let i = 0; i < count; i++) {
    const x = site.x - 125 + i * 44;
    const z = site.z - site.halfZ - 32 - (i % 2) * 14;
    const radius = 8.6 + (i % 3) * 2;
    const height = 12 + i % 3 * 3;
    yard.color("#626c70", .92).box(x, -.05, z, radius * 2.5, .26, radius * 2.5);
    yard.color(i % 2 ? "#a8a397" : "#adaeb1", .48, .18)
      .lathe([x, 0, z], [[radius,0],[radius,height - .6],[radius*.83,height],[radius*.14,height+.36],[0,height+.36]], 24);
    for (let level = 2; level < height; level += 3.2) {
      yard.color("#637178", .65, .22)
        .cylinder([x,level-.05,z],[x,level+.06,z],radius+.035,radius+.035,24,false);
    }
    if (i % 2 === 0) {
      const sx = x + radius + 5, sz = z - 4, top = height + 21;
      yard.color("#64727b", .63, .32).cylinder([sx,0,sz], [sx,top,sz], 1.09,.65,12);
      for (const stripe of [top - 2, top - 5]) {
        yard.color("#8f5148").cylinder([sx,stripe,sz], [sx,stripe+1.2,sz],.73,.71,12,false);
      }
      steam.push([sx, top+.05, sz]);
    }
  }
  const rackZ = site.z - site.halfZ - 21;
  for (let x = site.x - 140; x <= site.x + (high ? 145 : 46); x += 15) {
    for (const z of [rackZ-1.7, rackZ+1.7]) {
      yard.color("#465663", .77).box(x, 3.8, z, .32, 7.6, .32);
      yard.cylinder([x, 1, z],[x+7.5,7.5,z],.073,.073,5,false);
    }
    yard.box(x, 7.3,rackZ,.21,.34,3.9);
    for (const [offset, color] of [[-1.25,"#ae9a61"],[0,"#79868a"],[1.2,"#69828a"]] as const) {
      yard.color(color,.51,.19).cylinder([x,7.68,rackZ+offset],[x+15,7.68,rackZ+offset],.19,.19,8,false);
    }
  }
  const vapor = createParticles(atmosphere, {
    mode: "steam", origins: steam, count: high ? 74 : 42, seed: 172, life: 18,
    rise: 1.15, spread: .46, size: [1.65, 7.1], opacity: .27, drift: .72,
    color: "#f4eee4", shade: "#9ba7b0",
  });
  const lights = createBeacons(atmosphere, steam.map(([x,y,z], i) => ({
    position: [x+.64,y-.85,z], color: "#ff8363", phase: (i*.6)%1, size: .25,
    intensity: 1.2, period: 2.1, duty: .25,
  })));
  return standardScene(sceneGroup("entorno-industria", [
    ground, propMesh(yard, props, "entorno-unidades-vecinas"), vapor, lights,
  ]));
}
