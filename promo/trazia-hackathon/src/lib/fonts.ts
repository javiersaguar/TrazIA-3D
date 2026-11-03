import { continueRender, delayRender, staticFile } from 'remotion';

// Fuentes OFL descargadas de Google Fonts a public/fonts (Archivo con eje wdth, como la landing).
const FACES: [string, string, FontFaceDescriptors][] = [
  ['Archivo', 'fonts/Archivo.woff2', { weight: '100 900', stretch: '62% 125%' }],
  ['Inter', 'fonts/Inter.woff2', { weight: '400 700' }],
  ['JetBrains Mono', 'fonts/JetBrainsMono.woff2', { weight: '400 600' }],
];

let started = false;
export const loadFonts = () => {
  if (started || typeof document === 'undefined') return;
  started = true;
  const handle = delayRender('fuentes');
  Promise.all(
    FACES.map(async ([family, file, desc]) => {
      const face = new FontFace(family, `url(${staticFile(file)}) format("woff2")`, desc);
      await face.load();
      (document.fonts as unknown as { add(f: FontFace): void }).add(face);
    }),
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error(e);
      continueRender(handle);
    });
};
