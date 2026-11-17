import React, { useEffect, useState } from "react";
import { AnimatePresence, m } from "motion/react";
import { asset, ease, useFx } from "./fx.jsx";
import "./design-showcase.css";

// Recortes de los GA y órbitas prerenderizadas de los IFC homónimos de demo/industriales.
const designs = [
  { tag: "BC-CY102", family: "Ciclones", name: "Batería de dos ciclones" },
  { tag: "BC-P103", family: "Bombas", name: "Bomba horizontal de engranajes" },
  { tag: "BC-AC104", family: "Aeroenfriadores", name: "Dos haces de aeroenfriamiento en paralelo" },
];

const shotMilliseconds = 3900;
const plate = (tag, extension) => asset(`media/catalogo/${tag}.${extension}`);

export function DesignShowcase({ children }) {
  const fx = useFx();
  const [shot, setShot] = useState(0);
  const design = fx ? designs[shot] : undefined;

  useEffect(() => {
    if (!fx || shot >= designs.length) return;
    const timer = window.setTimeout(() => setShot(shot + 1), shotMilliseconds);
    return () => window.clearTimeout(timer);
  }, [fx, shot]);

  return (
    <section className="design-showcase" aria-label="Diseños sintéticos del catálogo y equipo de la demostración">
      <div className="design-stage">
        <AnimatePresence initial={false}>
          {design ? (
            <m.figure className="design-shot" key={design.tag}
              initial={{ opacity: 0, transform: "translateX(3%)" }}
              animate={{ opacity: 1, transform: "translateX(0%)" }}
              exit={{ opacity: 0, transform: "translateX(-3%)" }}
              transition={{ duration: 0.38, ease }}
            >
              <div className="design-view">
                <img src={plate(design.tag, "webp")} alt="" />
                <video muted autoPlay playsInline disablePictureInPicture preload="auto"
                  poster={plate(design.tag, "webp")} src={plate(design.tag, "webm")} aria-hidden="true" />
              </div>
              <div className="design-document"><span>Catálogo sintético</span><span>{design.tag} / REV. A</span></div>
              <figcaption>{design.name}</figcaption>
            </m.figure>
          ) : (
            <m.div className="design-case" key="v101"
              initial={fx ? { opacity: 0 } : false} animate={{ opacity: 1 }}
              transition={{ duration: fx ? 0.38 : 0, ease }}
            >
              {children}
            </m.div>
          )}
        </AnimatePresence>
      </div>
      <ul className="design-index" aria-label="Familias del catálogo sintético">
        {designs.map((item) => (
          <li key={item.tag} className={item === design ? "design-index-current" : undefined}>
            <img src={plate(item.tag, "webp")} alt="" width="72" height="47" />
            <div><small>{item.tag}</small><span>{item.family}</span></div>
          </li>
        ))}
      </ul>
    </section>
  );
}
