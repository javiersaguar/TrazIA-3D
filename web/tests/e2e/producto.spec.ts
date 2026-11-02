import { expect, test } from "@playwright/test";

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

test("el laboratorio está en la barra lateral y Del plano al modelo tiene pantalla completa",async({page})=>{
 await page.goto("/proyecto");
 const nav=page.getByRole("navigation",{name:"Navegación principal"});
 await nav.getByRole("link",{name:"Del plano al modelo",exact:true}).click();
 await expect(page).toHaveURL(/\/lab\/firma/);
 await page.getByTestId("signature-frame").getByRole("button",{name:"Pantalla completa",exact:true}).first().click();
 await expect.poll(()=>page.evaluate(()=>(document.fullscreenElement as HTMLElement|null)?.dataset.testid??null)).toBe("signature-frame");
 await page.keyboard.press("f");
 await expect.poll(()=>page.evaluate(()=>document.fullscreenElement)).toBeNull();
 await nav.getByRole("link",{name:"Laboratorio 3D",exact:true}).click();
 await expect(page.getByRole("heading",{level:1,name:"Laboratorio 3D"})).toBeVisible();
});
