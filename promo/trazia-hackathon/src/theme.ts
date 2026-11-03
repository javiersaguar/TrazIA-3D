// Tokens del producto (web/src/styles/tokens.css y web/src/lib/brand.ts). Ver design-spec.md.
export const C = {
  bg: '#09090b',
  surface: '#111113',
  surfaceRaised: '#18181b',
  border: '#222226',
  text: '#f4f4f5',
  muted: '#a1a1aa',
  sky: '#2aa8f2',
  skyLight: '#5cc4ff',
  skyPale: '#95ddfc',
  logoSky: '#4cbaf9',
  logoInkLo: '#85858d',
  logoInkHi: '#f4f4f6',
  revision: '#f5a35c',
  steel: '#9aa3ad',
};
export const FONT = {
  display: '"Archivo", "Inter", sans-serif',
  sans: '"Inter", sans-serif',
  mono: '"JetBrains Mono", monospace',
};
/** Estilo de .landing-display del producto. */
export const display = (size: number): React.CSSProperties => ({
  fontFamily: FONT.display,
  fontVariationSettings: '"wdth" 72',
  fontWeight: 600,
  letterSpacing: '-0.012em',
  fontSize: size,
  lineHeight: 1.02,
  color: C.text,
});
