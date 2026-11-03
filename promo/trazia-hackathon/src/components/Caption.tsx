import { useF } from '../lib/frame';
import React from 'react';
import { useCurrentFrame } from 'remotion';
import { EASE_IN, EASE_OUT, ramp } from '../lib/anim';
import { display } from '../theme';

/** Rótulo: palabras que suben desde la línea base (24 f, escalonado 3 f) y salen con fundido. */
export const Caption: React.FC<{
  text: string;
  from: number;
  to: number;
  size?: number;
  align?: 'left' | 'center';
  style?: React.CSSProperties;
}> = ({ text, from, to, size = 84, align = 'left', style }) => {
  const f = useF();
  if (f < from - 1 || f > to + 1) return null;
  const out = 1 - ramp(f, to - 14, to, EASE_IN);
  const words = text.split(' ');
  return (
    <div
      style={{
        position: 'absolute',
        ...(align === 'left' ? { left: 120, bottom: 112, textAlign: 'left' } : { left: 0, right: 0, textAlign: 'center' }),
        maxWidth: align === 'left' ? 1300 : undefined,
        opacity: out,
        ...display(size),
        ...style,
      }}
    >
      {words.map((w, i) => {
        const p = ramp(f, from + i * 3, from + i * 3 + 24, EASE_OUT);
        return (
          <span key={i} style={{ display: 'inline-block', overflow: 'hidden', verticalAlign: 'bottom', paddingBottom: '0.08em' }}>
            <span style={{ display: 'inline-block', transform: `translateY(${(1 - p) * 0.9}em)`, opacity: p }}>
              {w}
              {i < words.length - 1 ? '\u00a0' : ''}
            </span>
          </span>
        );
      })}
    </div>
  );
};
