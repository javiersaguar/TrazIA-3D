import {
  AmbientLight, DirectionalLight, Group, InstancedMesh, Mesh, MeshPhysicalMaterial,
  OrthographicCamera, PMREMGenerator, Scene, Vector3, WebGLRenderer, AgXToneMapping,
} from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { BRAND } from "@/lib/brand";
import { equipmentGeometry, retainEquipment, type EquipmentKind, type Finish } from "./equipment-geometry";

const images = new Map<EquipmentKind, Promise<string>>();
let queue = Promise.resolve();

/** Miniaturas estáticas de geometría 3D real; cada render libera su contexto WebGL. */
export function equipmentThumbnail(kind: EquipmentKind): Promise<string> {
  const cached = images.get(kind);
  if (cached) return cached;
  const result = new Promise<string>((resolve, reject) => {
    queue = queue.then(() => new Promise<void>(done => requestAnimationFrame(() => {
      let renderer: WebGLRenderer | undefined;
      const model = equipmentGeometry(kind), release = retainEquipment(kind);
      const resources: { dispose(): void }[] = [];
      try {
        renderer = new WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
        renderer.setSize(240, 240); renderer.setPixelRatio(1);
        renderer.toneMapping = AgXToneMapping; renderer.toneMappingExposure = 1.2;
        const scene = new Scene(), group = new Group();
        const room = new RoomEnvironment(), pmrem = new PMREMGenerator(renderer);
        const env = pmrem.fromScene(room, .04);
        scene.environment = env.texture; scene.environmentIntensity = .9;
        resources.push(room, pmrem, env);
        const colors: Record<Finish, string> = { steel: BRAND.steel, paint: BRAND.paint, machined: BRAND.logoGraphite, bolts: BRAND.steelDark };
        const materials = Object.fromEntries(Object.entries(colors).map(([finish, color]) => {
          const material = new MeshPhysicalMaterial({ color, metalness: .85, roughness: .3, clearcoat: .2 });
          resources.push(material); return [finish, material];
        })) as Record<Finish, MeshPhysicalMaterial>;
        for (const batch of model.batches) group.add(new Mesh(batch.geometry, materials[batch.finish]));
        const bolts = new InstancedMesh(model.boltGeometry, materials.bolts, model.bolts.length);
        model.bolts.forEach((matrix, i) => bolts.setMatrixAt(i, matrix));
        bolts.instanceMatrix.needsUpdate = true; group.add(bolts); resources.push(bolts);
        const center = model.bounds.getCenter(new Vector3()), size = model.bounds.getSize(new Vector3());
        group.position.sub(center); scene.add(group);
        scene.add(new AmbientLight(BRAND.text, .5));
        const light = new DirectionalLight(BRAND.text, 3); light.position.set(4, 8, 5); scene.add(light);
        const extent = Math.max(size.x, size.y, size.z) * .68;
        const camera = new OrthographicCamera(-extent, extent, extent, -extent, .01, 100);
        camera.position.set(9, 5, 10); camera.lookAt(0, 0, 0); camera.updateProjectionMatrix();
        renderer.render(scene, camera);
        resolve(renderer.domElement.toDataURL("image/png"));
      } catch (error) { images.delete(kind); reject(error); }
      finally { resources.forEach(r => r.dispose()); renderer?.dispose(); renderer?.forceContextLoss(); release(); done(); }
    })));
  });
  images.set(kind, result);
  return result;
}
