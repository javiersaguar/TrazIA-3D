import { scenes } from "./pitch-data.js";

const select = document.getElementById("scene");
const disable = document.getElementById("disable");
const status = document.getElementById("status");
const baseline = { frame: document.getElementById("baseline"), serial: 0 };
const current = { frame: document.getElementById("current"), serial: 0 };
const panels = [baseline, current];
let selected = 1;

scenes.forEach(({ title, accent }, index) => {
  const option = document.createElement("option");
  option.value = String(index + 1);
  option.textContent = `${index + 1} · ${title} ${accent}`.trim();
  select.append(option);
});

function active(document) {
  const number = document.querySelector(".deck-stage")?.dataset.sceneIndex
    ?? document.querySelector(".slide-index")?.textContent.trim().match(/^\d+/)?.[0];
  return number ? Number(number) : null;
}

function waitFor(test, limit = 2000) {
  const end = performance.now() + limit;
  return new Promise((resolve, reject) => {
    function poll() {
      const value = test();
      if (value) resolve(value);
      else if (performance.now() >= end) reject(new Error("No se pudo sincronizar la escena."));
      else setTimeout(poll, 16);
    }
    poll();
  });
}

async function sync(panel, target) {
  const doc = panel.frame.contentDocument;
  const serial = ++panel.serial;
  panel.driving = true;
  function press(key) {
    doc.body.dispatchEvent(new doc.defaultView.KeyboardEvent("keydown", { key, bubbles: true }));
  }
  try {
    const ready = await waitFor(() => serial !== panel.serial || active(doc));
    if (serial !== panel.serial || ready === target) return;
    doc.querySelector('.play-control[aria-pressed="true"]')?.click();
    if (doc.querySelector('.deck-stage[data-rehearsing="true"]')) press("p");
    let index = active(doc);
    while (serial === panel.serial && index !== target) {
      const former = index;
      press(index < target ? "ArrowRight" : "ArrowLeft");
      await waitFor(() => serial !== panel.serial || active(doc) !== former);
      index = active(doc);
    }
    if (serial === panel.serial) status.textContent = "";
  } catch (error) {
    if (serial === panel.serial) status.textContent = error.message;
  } finally {
    if (serial === panel.serial) panel.driving = false;
  }
}

function choose(index, source) {
  if (index === selected && source) return;
  selected = index;
  select.value = String(index);
  for (const panel of panels) {
    if (panel !== source) void sync(panel, index);
  }
}

function bind(panel) {
  panel.frame.addEventListener("load", async () => {
    panel.observer?.disconnect();
    const doc = panel.frame.contentDocument;
    panel.driving = true;
    await sync(panel, selected);
    const node = doc.querySelector("[data-scene-index]") ?? doc.querySelector(".slide-index");
    if (!node) return;
    panel.observer = new MutationObserver(() => {
      const next = active(doc);
      if (next && !panel.driving) choose(next, panel);
    });
    panel.observer.observe(node, { attributes: true, characterData: true, childList: true, subtree: true });
    doc.addEventListener("keydown", (event) => {
      if (!event.isTrusted || event.key.toLowerCase() !== "r" || event.repeat || event.altKey || event.ctrlKey || event.metaKey) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      repeat();
    }, true);
  });
}

function load(panel, url) {
  panel.observer?.disconnect();
  panel.driving = true;
  panel.serial++;
  panel.frame.src = url;
}

function repeat() {
  const target = current.frame.contentWindow;
  target.document.body?.dispatchEvent(new target.KeyboardEvent("keydown", { key: "r", bubbles: true }));
  load(baseline, `/boceto/index.html?replay=${Date.now()}`);
}

select.addEventListener("change", () => choose(Number(select.value)));
disable.addEventListener("change", () => load(current, disable.checked ? "/?fx=0" : "/"));
document.getElementById("repeat").addEventListener("click", repeat);
document.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() === "r" && !event.repeat && !event.target.closest("input, select")
    && !event.altKey && !event.ctrlKey && !event.metaKey) repeat();
});

for (const panel of panels) bind(panel);
load(baseline, "/boceto/index.html");
load(current, "/");
