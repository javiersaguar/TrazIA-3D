import React from 'react';
import { C, FONT } from '../theme';

/** Aviso discreto y permanente: material de demostración con datos sintéticos.
 *  Lleva una píldora oscura detrás para seguir legible sobre el papel blanco de la escena 4. */
export const SyntheticBadge: React.FC<{ opacity?: number }> = ({ opacity = 1 }) => (
  <div
    style={{
      position: 'absolute',
      right: 44,
      bottom: 34,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '9px 16px',
      borderRadius: 10,
      background: 'rgba(9,9,11,0.72)',
      fontFamily: FONT.sans,
      fontWeight: 500,
      fontSize: 26,
      color: C.muted,
      opacity: 0.9 * opacity,
      letterSpacing: '0.005em',
    }}
  >
    <span style={{ width: 9, height: 9, borderRadius: 9, background: C.revision }} />
    Demostración · datos sintéticos
  </div>
);
