import { expect, it } from "vitest";
import type { Target } from "./api";
import { editableElements } from "./elements";
import { convertDisplay } from "./display-value";
import { toOperations } from "./form";

const target=(key:string,group="equipo"):Target=>({target:key,path:key,label:key,group,
  unit:"mm",magnitude:"length",rule:"",derived:false,datums:[],affects:[],text:false,
  current:{value:2000,unit:"mm",state:"candidate"}});

it("ofrece piezas individuales con sus campos comunes y el ID real del visor",()=>{
  const elements=editableElements([target("diameter"),target("height"),target("head_depth"),
    target("skirt_height"),target("nozzles.N1.elevation","boquilla:N1"),
    target("platforms.P1.origin.z","pieza:platforms:P1")],"vertical_vessel");
  expect(elements.find(e=>e.id==="head-top")?.targets).toEqual(["diameter","head_depth"]);
  expect(elements.find(e=>e.id==="boquilla:N1")?.semantic).toBe("nozzle:N1");
  expect(elements.find(e=>e.id==="pieza:platforms:P1")?.semantic).toBe("element:platform-P1");
});

it("parte de la base sin enviar campos intactos y conserva los cambios explícitos",()=>{
  expect(toOperations({diameter:{value:"2000.0",unit:"mm"}},[target("diameter")])).toEqual([]);
  expect(toOperations({diameter:{value:"2",unit:"m"}},[target("diameter")])).toEqual([]);
  expect(toOperations({diameter:{value:"2100",unit:"mm"}},[target("diameter")])).toHaveLength(1);
});

it("cambia la unidad de presentación conservando la dimensión y sin asumir unidades desconocidas",()=>{
  expect(convertDisplay("2000","mm","m")).toBe("2");
  expect(convertDisplay("2","m","mm")).toBe("2000");
  expect(convertDisplay("0","C","F")).toBe("32");
  expect(convertDisplay("32","F","C")).toBe("0");
  expect(convertDisplay("2","bara","bar")).toBe("");
  expect(convertDisplay("dos","mm","m")).toBe("");
});
