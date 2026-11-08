import { afterEach, expect, it, vi } from "vitest";
import { draftKey, useDraftCache } from "./draft-store";

afterEach(() => { useDraftCache.setState({entries:{}}); vi.unstubAllGlobals(); });

it("conserva borradores y altas incompletas por revisión y equipo al rehidratar", async () => {
  const memory = new Map<string,string>();
  vi.stubGlobal("sessionStorage", {getItem:(k:string)=>memory.get(k)??null,
    setItem:(k:string,v:string)=>memory.set(k,v),removeItem:(k:string)=>memory.delete(k)});
  const a = draftKey("P", "V-101", "A"), b=draftKey("P", "V-101", "B");
  const other = draftKey("P", "H-201", "A");
  const update=useDraftCache.getState().update;
  update(a,"drafts",{height:{value:"7100",unit:"mm"}});
  update(a,"partForm",{action:"add",collection:"nozzles",id:"N5",values:{diameter:"120"}});
  update(b,"reason","Capacidad nueva"); update(other,"reason","Otra familia");
  const saved=memory.get("trazia-design-drafts-v1")!;
  useDraftCache.setState({entries:{}});
  memory.set("trazia-design-drafts-v1",saved);
  await useDraftCache.persist.rehydrate();
  expect(useDraftCache.getState().entries[a]?.drafts.height?.value).toBe("7100");
  expect(useDraftCache.getState().entries[a]?.partForm.values.diameter).toBe("120");
  expect(useDraftCache.getState().entries[b]?.reason).toBe("Capacidad nueva");
  expect(useDraftCache.getState().entries[other]?.reason).toBe("Otra familia");
});

it("sigue conservando en memoria si el navegador bloquea el almacenamiento", () => {
  vi.stubGlobal("sessionStorage",{setItem:()=>{throw new Error("bloqueado");}});
  expect(()=>useDraftCache.getState().update("a","request","Cambiar N3")).not.toThrow();
  expect(useDraftCache.getState().entries.a?.request).toBe("Cambiar N3");
});
