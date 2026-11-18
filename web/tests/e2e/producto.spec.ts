import { expect, test } from "@playwright/test";

test("los proyectos de proceso conservan el entorno y aplican cambios IFC por pieza", async ({ page, request }) => {
  test.setTimeout(90_000);
  await page.goto("/documentos?vista=proyectos");
  const cards = page.getByRole("region", { name: "Proyectos 3D de petróleo y gas" });
  await expect(cards.getByRole("link")).toHaveCount(4);
  await cards.getByRole("link", { name: /Plataforma marina de producción/ }).click();
  const viewer = page.getByTestId("ifc-viewer");
  await expect(viewer).toHaveAttribute("data-ifc-url", /SIM-MAR-A\.ifc$/, { timeout: 30_000 });
  await expect(viewer).toHaveAttribute("data-scenario", "ocean");
  await page.getByLabel("Entorno del visor").selectOption("desert");
  await expect(viewer).toHaveAttribute("data-scenario", "desert");
  await expect(viewer).toHaveAttribute("data-ifc-url", /SIM-MAR-A\.ifc$/);
  await page.reload();
  await expect(viewer).toHaveAttribute("data-scenario", "desert");
  await page.getByRole("checkbox", { name: /Ampliar la virola/ }).check();
  await expect(viewer).toHaveAttribute("data-ifc-url", /Ensayo-10\.ifc$/, { timeout: 30_000 });
  await page.getByRole("checkbox", { name: /Elevar el tramo/ }).check();
  await expect(viewer).toHaveAttribute("data-ifc-url", /SIM-MAR-B\.ifc$/, { timeout: 30_000 });
  const drawing = await page.getByRole("link", { name: "PDF de V-110", exact: true }).getAttribute("href");
  expect(drawing).toMatch(/GAD_V-110_revB\.pdf$/);
  expect((await request.get(drawing!)).headers()["content-type"]).toContain("application/pdf");
  const zip = await page.getByRole("link", { name: "Descargar dossier ZIP" }).getAttribute("href");
  expect(zip).toMatch(/dossier-B\.zip$/);
  expect((await request.get(zip!)).ok()).toBe(true);
});

test("navegación de producto agrupada y ajustes en el pie", async ({page})=>{
 await page.goto("/documentos");
 const nav=page.getByRole("navigation",{name:"Navegación principal"});
 await expect(nav.getByRole("link",{name:"Modelo",exact:true})).toBeVisible();
 for(const name of ["Auditoría","Familias","Proyectos","Estudio","Informes","Revisión","Cambios","Ajustes"])
  await expect(nav.getByRole("link",{name,exact:true})).toHaveCount(0);
 await expect(nav.locator(".uppercase")).toHaveCount(0);
 await page.getByRole("link",{name:"Ajustes",exact:true}).click();
 await page.getByRole("radio",{name:"Claro",exact:true}).click();
 await expect(page.locator("html")).toHaveAttribute("data-theme","light");
 await expect(page.getByText("Javier Saguar Antona",{exact:true})).toBeVisible();
});

test("familias, proyectos y archivos sobreviven a recargar",async({page})=>{
 await page.goto("/documentos");
 await page.getByRole("button",{name:"Nueva familia",exact:true}).click();
 await page.getByRole("form",{name:"Nueva familia"}).getByLabel("Nombre").fill("Separadores del piloto");
 await page.getByRole("button",{name:"Guardar",exact:true}).click();
 await page.getByRole("button",{name:"Nuevo proyecto",exact:true}).click();
 await page.getByRole("form",{name:"Nuevo proyecto"}).getByLabel("Nombre").fill("Proyecto piloto");
 await page.getByRole("button",{name:"Guardar",exact:true}).click();
 await page.getByRole("button",{name:"Añadir diseño",exact:true}).click();
 const form=page.getByRole("form",{name:"Añadir diseño"});
 await form.getByLabel("Nombre").fill("V-202");
 await form.getByLabel("Familia",{exact:true}).selectOption({label:"Separadores del piloto"});
 await form.getByLabel("Proyecto",{exact:true}).selectOption({label:"Proyecto piloto"});
 await form.getByLabel("Documento",{exact:true}).setInputFiles({name:"GAD_V202.pdf",mimeType:"application/pdf",buffer:Buffer.from("synthetic test document")});
 await page.getByRole("button",{name:"Guardar",exact:true}).click();
 await expect(page.getByText("V-202",{exact:true})).toBeVisible();
 await page.reload();
 await expect(page.getByText("V-202",{exact:true})).toBeVisible();
 const download=page.waitForEvent("download");
 await page.getByRole("button",{name:"GAD_V202.pdf",exact:true}).click();
 expect((await download).suggestedFilename()).toBe("GAD_V202.pdf");
});

test("portada muestra estudio actual, métricas accesibles y foco tras scroll",async({page})=>{
 await page.goto("/");
 const skip=page.getByRole("button",{name:/Saltar intro/});if(await skip.isVisible())await skip.click();
 await page.locator("#estrategias").scrollIntoViewIfNeeded();
 await expect(page.getByText(/Estudio 7/)).toBeVisible();
 for(const name of ["Visión + 3D","Datos + reglas","RAG","Híbrido"]){
  const row=page.getByRole("button",{name:new RegExp(name.replace(/[+]/g,"\\+"))});
  await row.hover();await expect(row).toHaveAttribute("aria-expanded","true");
  await row.click();await expect(row).toHaveAttribute("aria-expanded","true");
 }
 await page.mouse.move(700,350);
 await expect(page.getByTestId("landing-spotlight")).toHaveCSS("position","fixed");
 await expect(page.getByRole("button",{name:/giro de cámara 360/})).toHaveCount(0);
});

test("revisión, cambios y geometría comparten una sola ruta",async({page})=>{
 await page.emulateMedia({reducedMotion:"reduce"});
 await page.goto("/modelo");
 await expect(page.getByRole("heading",{name:"Modelo",exact:true})).toBeVisible();
 await page.getByRole("radio",{name:"Cambios",exact:true}).click();
 await expect(page).toHaveURL(/vista=cambios/);
 await expect(page.getByTestId("revision-morph")).toBeVisible();
 await page.getByRole("radio",{name:"Modelo 3D",exact:true}).click();
 await expect(page.getByTestId("model-workspace")).toBeVisible();
 await page.getByRole("radio",{name:"Revisión",exact:true}).click();
 await expect(page).toHaveURL(/vista=revision/);
});

test("la cámara del holograma permanece fija durante la transición y el arrastre",async({page})=>{
 await page.emulateMedia({reducedMotion:"no-preference"});
 await page.goto("/");
 const skip=page.getByRole("button",{name:/Saltar intro/});if(await skip.isVisible())await skip.click();
 await page.getByRole("heading",{name:"Del holograma al modelo",exact:true}).scrollIntoViewIfNeeded();
 const scene=page.locator('[data-source="procedural"]');
 await scene.scrollIntoViewIfNeeded();
 const canvas=scene.locator("canvas").first();
 await expect(canvas).toHaveAttribute("data-camera-position",/.+/);
 await page.waitForTimeout(1200);
 const before=await canvas.getAttribute("data-camera-position");
 await page.waitForTimeout(1200);
 expect(await canvas.getAttribute("data-camera-position")).toBe(before);
 const box=await canvas.boundingBox();expect(box).not.toBeNull();
 await page.mouse.move(box!.x+box!.width*.45,box!.y+box!.height*.5);await page.mouse.down();
 await page.mouse.move(box!.x+box!.width*.7,box!.y+box!.height*.5,{steps:8});await page.mouse.up();
 await page.waitForTimeout(500);
 expect(await canvas.getAttribute("data-camera-position")).toBe(before);
});

test("movimiento reducido muestra también los trazos de pasos fuera de pantalla",async({page})=>{
 await page.emulateMedia({reducedMotion:"reduce"});
 await page.goto("/",{waitUntil:"networkidle"});
 const revisions=page.getByRole("img",{name:"Dos revisiones y una variación de altura",exact:true});
 await expect(revisions.locator("path").first()).toHaveCSS("opacity","1");
});

test("Documentos reúne documentos, proyectos y familias y acepta soltar archivos",async({page})=>{
 await page.goto("/documentos");
 await expect(page.getByText("Suelta aquí los planos GA y las hojas de datos")).toBeVisible();
 await page.getByLabel("Familia de destino").selectOption({label:"Intercambiadores"});
 await page.getByTestId("document-dropzone").evaluate(zone=>{
  const dt=new DataTransfer();dt.items.add(new File(["synthetic"],"GAD_E-210_revA.pdf",{type:"application/pdf"}));
  zone.dispatchEvent(new DragEvent("drop",{dataTransfer:dt,bubbles:true,cancelable:true}));
 });
 await expect(page.getByRole("button",{name:"GAD_E-210_revA.pdf",exact:true})).toBeVisible();
 await expect(page.getByLabel("Familia de GAD_E-210_revA")).toHaveValue("exchanger");
 await page.getByRole("button",{name:"elígelos en tu equipo"}).waitFor();
 await page.getByLabel("Elegir documentos").setInputFiles({name:"DS_P-501_revA.pdf",mimeType:"application/pdf",buffer:Buffer.from("synthetic")});
 await expect(page.getByRole("button",{name:"DS_P-501_revA.pdf",exact:true})).toBeVisible();
 await page.getByRole("radio",{name:"Proyectos",exact:true}).click();
 await expect(page).toHaveURL(/vista=proyectos/);
 await expect(page.getByText("Unidad de hidrotratamiento",{exact:true})).toBeVisible();
 await page.getByRole("navigation",{name:"Familias de documentos"}).getByRole("button",{name:/Tanques/}).click();
 await expect(page.getByText("Terminal de GNL",{exact:true})).toBeVisible();
 await expect(page.getByText("Unidad de hidrotratamiento",{exact:true})).toHaveCount(0);
 await page.goto("/familias");
 await expect(page).toHaveURL(/vista=familias/);
 await expect(page.getByRole("heading",{name:"Recipientes verticales",level:3})).toBeVisible();
 await expect(page.getByText("22 campos de revisión")).toBeVisible();
});

test("la biblioteca de bocetos añade los PDF sin desplazar documentos ya guardados", async ({ page }) => {
  await page.addInitScript(() => {
    const key = "trazia.catalogue.v1";
    if (localStorage.getItem(key)) return;
    localStorage.setItem(key, JSON.stringify({
      version: 4,
      state: {
        families: [{ id: "custom", name: "Familia propia" }, { id: "pump", name: "Bombas" }],
        projects: [{ id: "custom-project", name: "Proyecto propio" }],
        designs: [{ id: "custom-design", name: "Mi diseño", family: "custom", project: "custom-project" }],
      },
    }));
  });
  await page.goto("/documentos");
  const links = page.getByRole("link", { name: /Abrir PDF de BC-/ });
  await expect(links).toHaveCount(72);
  await expect(page.getByText("Mi diseño", { exact: true })).toBeVisible();
  await page.reload();
  await expect(links).toHaveCount(72);
  await expect(page.getByLabel("Familia de Mi diseño")).toHaveValue("custom");

  await page.getByRole("radio", { name: "Proyectos", exact: true }).click();
  await page.getByRole("button", { name: /Biblioteca de bocetos/ }).click();
  await expect(links).toHaveCount(72);
  await expect(page.getByText("Mi diseño", { exact: true })).toHaveCount(0);
  await page.getByRole("navigation", { name: "Familias de documentos" }).getByRole("button", { name: /Bombas/ }).click();
  await expect(links).toHaveCount(4);
  for (const link of await links.all()) {
    const url = await link.getAttribute("href");
    expect(url).toMatch(/^\/demo\/(?:bocetos\/BOC_BC-P10[12]_revA|industriales\/BC-P10[34]-A)\.pdf$/);
    const pdf = await page.request.get(url!);
    expect(pdf.ok()).toBe(true);
    expect(pdf.headers()["content-type"]).toContain("application/pdf");
    expect((await pdf.body()).subarray(0, 5).toString()).toBe("%PDF-");
  }
});

test("las 18 fichas de familia muestran sus cuatro diseños sin cambiar de pestaña", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/documentos?vista=familias");
  const galleries = page.locator("details").filter({ has: page.locator("ul[aria-label^='Diseños de ']") });
  await expect(galleries).toHaveCount(18);
  for (const gallery of await galleries.all()) {
    await gallery.locator("summary").click();
    const links = gallery.getByRole("link", { name: /Abrir PDF de BC-/ });
    await expect(links).toHaveCount(4);
    await expect(links.last()).toBeVisible();
    await gallery.locator("summary").click();
  }
  await expect(page).toHaveURL(/vista=familias/);
});

test("los separadores ciclónicos se abren como modelos IFC conceptuales", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/documentos?vista=familias");
  const family = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: "Separadores ciclónicos" }) });
  await expect(family.getByText("Conceptual 3D")).toBeVisible();
  await family.getByText("Ver 4 diseños", { exact: true }).click();
  await expect(family.getByRole("link", { name: /Abrir PDF de BC-CY/ })).toHaveCount(4);
  const trigger = family.getByRole("button", { name: "Ver 3D de BC-CY104" });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "Ciclón con tolva de recogida" });
  const viewer = dialog.getByTestId("ifc-viewer");
  await expect(viewer).toHaveAttribute("data-phase", "ready", { timeout: 25_000 });
  await expect(viewer).toHaveAttribute("data-products", "7");
  await expect(viewer).toHaveAttribute("data-provenance", "Datos sintéticos");
  await expect(viewer.locator("canvas")).toBeVisible();
  const download = dialog.getByRole("link", { name: "Descargar IFC" });
  await expect(download).toHaveAttribute("href", "/demo/industriales/BC-CY104-A.ifc");
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test("Modelo conserva el holograma, la galería y la pantalla completa con F",async({page})=>{
 await page.emulateMedia({reducedMotion:"reduce"});
 await page.goto("/modelo?vista=3d");
 await expect(page.getByRole("heading",{name:"Del holograma al modelo",exact:true})).toBeVisible();
 await expect(page.getByRole("heading",{name:"Familias ilustrativas",exact:true})).toBeVisible();
 const hologram=page.getByTestId("model-hologram");
 await hologram.scrollIntoViewIfNeeded();
 await expect(hologram.locator("canvas").first()).toBeVisible({timeout:20_000});
 await hologram.hover();
 await page.keyboard.press("f");
 await expect.poll(()=>page.evaluate(()=>(document.fullscreenElement as HTMLElement|null)?.dataset.testid??null),{timeout:10_000}).toBe("model-hologram");
 await expect(hologram.getByRole("button",{name:/Salir de pantalla completa/})).toBeVisible();
 await page.keyboard.press("f");
 await expect.poll(()=>page.evaluate(()=>document.fullscreenElement)).toBeNull();
 await page.goto("/modelo?vista=revision");
 await expect(page.getByText(/Cada valor con su evidencia en el plano/)).toBeVisible();
});

test("la barra lateral lleva al Laboratorio 3D, sin Del plano al modelo ni texto de atajo en Buscar",async({page})=>{
 await page.goto("/proyecto");
 const nav=page.getByRole("navigation",{name:"Navegación principal"});
 await expect(nav.getByRole("link",{name:"Del plano al modelo",exact:true})).toHaveCount(0);
 await expect(page.getByRole("button",{name:"Buscar",exact:true})).toHaveText("Buscar");
 await nav.getByRole("link",{name:"Laboratorio 3D",exact:true}).click();
 await expect(page.getByRole("heading",{level:1,name:"Laboratorio 3D"})).toBeVisible();
 await page.goto("/lab/firma");
 await expect(page).toHaveURL(/\/#del-plano$/);
});

test("en la portada, Del plano al modelo avanza con el scroll",async({page})=>{
 await page.emulateMedia({reducedMotion:"no-preference"});
 await page.goto("/");
 const skip=page.getByRole("button",{name:/Saltar intro/});if(await skip.isVisible())await skip.click();
 const section=page.locator("#del-plano");
 const scrollTo=(f:number)=>section.evaluate((el,f)=>window.scrollTo(0,(el as HTMLElement).offsetTop+(el.clientHeight-innerHeight)*f),f);
 await scrollTo(0);
 const signature=page.getByTestId("landing-signature").getByTestId("signature");
 await expect(signature).toHaveAttribute("data-phase","ready",{timeout:30_000});
 await expect(signature).toHaveAttribute("data-step","0");
 await expect(signature.getByRole("button",{name:/Reproducir firma/})).toHaveCount(0);
 await scrollTo(.5);
 await expect(signature).toHaveAttribute("data-step","1");
 await scrollTo(.98);
 await expect(signature).toHaveAttribute("data-step","2");
 await expect(page.getByRole("heading",{name:"Modelo DRAFT listo para revisar"}).locator("xpath=ancestor::li")).toHaveAttribute("aria-current","step");
});

test("Modelo › Diseños regenera el IFC en directo al cambiar medidas y piezas",async({page})=>{
 await page.goto("/modelo?vista=disenos&diseno=BC-AC101");
 await expect(page.getByRole("navigation",{name:"Catálogo de diseños"}).getByRole("listitem")).toHaveCount(72);
 const status=page.getByTestId("design-ifc-status");
 await expect(status).toHaveText("IFC publicado · 8 piezas",{timeout:30_000});
 const alto=page.getByRole("spinbutton",{name:"Alto",exact:true});
 await alto.fill("4800");
 await alto.press("Enter");
 await expect(status).toHaveAttribute("data-state","ready",{timeout:30_000});
 await expect(status).toContainText(/IFC regenerado en \d+ ms · 8 piezas/);
 await expect(page.getByText("Ancho 8200 mm · Fondo 3300 mm · Alto 4800 mm")).toBeVisible();
 await page.getByRole("button",{name:"Ocultar Colector",exact:true}).click();
 await expect(status).toContainText(/IFC regenerado en \d+ ms · 7 piezas/);
 await expect(page.getByRole("link",{name:/Descargar IFC/})).toHaveAttribute("download","BC-AC101-A-editado.ifc");
 await page.reload();
 await expect(page.getByRole("spinbutton",{name:"Alto",exact:true})).toHaveValue("4800");
 await page.getByRole("button",{name:"Restablecer",exact:true}).click();
 await expect(status).toHaveText("IFC publicado · 8 piezas");
});

test("/reiniciar vacía lo guardado en el navegador y vuelve a Documentos",async({page})=>{
 await page.goto("/documentos");
 await page.getByRole("button",{name:"Nueva familia",exact:true}).click();
 await page.getByRole("form",{name:"Nueva familia"}).getByLabel("Nombre").fill("Familia para reiniciar");
 await page.getByRole("button",{name:"Guardar",exact:true}).click();
 await expect(page.getByText("Familia para reiniciar").first()).toBeVisible();
 await page.goto("/modelo?vista=disenos&diseno=BC-AC101");
 await page.getByRole("spinbutton",{name:"Alto",exact:true}).fill("4800");
 await page.getByRole("spinbutton",{name:"Alto",exact:true}).press("Enter");
 await page.goto("/reiniciar?destino=/documentos");
 await expect(page.getByRole("status")).toContainText("Demo reiniciada");
 await page.waitForURL("**/documentos");
 await expect(page.getByText("Familia para reiniciar")).toHaveCount(0);
 expect(await page.evaluate(()=>window.localStorage.getItem("trazia-design-edits"))).toBeNull();
});
