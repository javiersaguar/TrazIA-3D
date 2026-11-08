import { expect, test } from "@playwright/test";
import { resolve } from "node:path";

test("la intro completa el vuelo antes de arrancar las escenas pesadas", async ({page})=>{
  test.setTimeout(60_000);
  await page.emulateMedia({reducedMotion:"no-preference"});
  await page.addInitScript(()=>{
    const history: {phase:string|null; canvases:number;at:number}[]=[];
    Object.assign(window,{introHistory:history});
    new MutationObserver(()=>{
      const phase=document.querySelector("[data-intro-phase]")?.getAttribute("data-intro-phase")??null;
      const last=history.at(-1);
      if(phase&&last?.phase!==phase) history.push({phase,canvases:document.querySelectorAll("canvas").length,at:performance.now()});
    }).observe(document,{subtree:true,attributes:true,attributeFilter:["data-intro-phase"],childList:true});
  });
  const errors:string[]=[]; page.on("pageerror",e=>errors.push(e.message));
  await page.goto("/");
  const root=page.locator("[data-intro-phase]");
  await expect(root).toHaveAttribute("data-intro-phase","assembling");
  await expect(page.locator("canvas")).toHaveCount(0);
  await expect(root).toHaveAttribute("data-intro-phase","flying",{timeout:10_000});
  await expect(page.locator("canvas")).toHaveCount(0);
  // Las animaciones activas del vuelo son solo dos transformaciones, sin layoutId.
  const flying=await page.locator('[data-intro-logo-part="mark"]').evaluate(node=>({
    frames:node.getAnimations().map(a=>(a.effect as KeyframeEffect).getKeyframes().map(f=>f.transform)),
    changingLayout:node.hasAttribute("data-projection-id"),
  }));
  expect(flying.frames).toHaveLength(1);expect(flying.changingLayout).toBe(false);
  await expect(root).toHaveAttribute("data-intro-phase","ready");
  await expect(page.locator('[data-intro-target="mark"]')).toBeVisible();
  await expect(page.locator('[data-equipment-kind] canvas')).toBeVisible({timeout:40_000});
  const history=await page.evaluate(()=>Reflect.get(window,"introHistory")) as {phase:string;canvases:number;at:number}[];
  expect(history.map(x=>x.phase)).toEqual(["assembling","flying","ready"]);
  expect(history.filter(x=>x.phase!=="ready").every(x=>x.canvases===0)).toBe(true);
  await page.screenshot({path:resolve("../docs/evidencias/intro-fluida/entrada-final.png")});
  expect(errors).toEqual([]);
});

test("se puede saltar con teclado y redimensionar durante el vuelo",async({page})=>{
  await page.goto("/");
  const root=page.locator("[data-intro-phase]");
  await expect(page.getByRole("button",{name:/Saltar intro/})).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(root).toHaveAttribute("data-intro-phase","flying");
  await page.setViewportSize({width:390,height:844});
  await expect(root).toHaveAttribute("data-intro-phase","ready");
  const mark=await page.locator('[data-intro-target="mark"]').boundingBox();
  expect(mark!.x).toBeGreaterThanOrEqual(0); expect(mark!.x+mark!.width).toBeLessThan(390);
});

test("movimiento reducido salta la intro y no la repite al cambiar el ajuste",async({page})=>{
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("/");
  const root=page.locator("[data-intro-phase]");
  await expect(root).toHaveAttribute("data-intro-phase","ready");
  await expect(page.getByRole("button",{name:/Saltar intro/})).not.toBeVisible();
  await page.emulateMedia({reducedMotion:"no-preference"});
  await expect(root).toHaveAttribute("data-intro-phase","ready");
});


test("el diálogo diferido abre, cierra y devuelve el foco al botón",async({page})=>{
  await page.emulateMedia({reducedMotion:"reduce"});
  await page.goto("/");
  const button=page.getByRole("button",{name:/Ver el recorrido de la demo/});
  await button.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(button).toBeFocused();
});
