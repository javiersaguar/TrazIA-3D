// QA: un solo bundle y varios stills. Uso: node scripts/stills.mjs 420 520 ... [--props=props-nobgm.json]
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import path from 'path';
import fs from 'fs';

const frames = process.argv.slice(2).filter((a) => !a.startsWith('--')).map(Number);
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..');
const serveUrl = await bundle({ entryPoint: path.join(root, 'src/index.ts'), publicDir: path.join(root, 'public') });
const inputProps = { bgm: true };
const composition = await selectComposition({ serveUrl, id: 'TraziaPromo', inputProps, chromiumOptions: { gl: 'angle' } });
fs.mkdirSync(path.join(root, 'out/qa'), { recursive: true });
for (const frame of frames) {
  const output = path.join(root, `out/qa/f${frame}.png`);
  await renderStill({ serveUrl, composition, frame, output, inputProps, chromiumOptions: { gl: 'angle' }, timeoutInMilliseconds: 120000 });
  console.log('still', frame);
}
