import React from 'react';
import {COLORS} from '../config';

/** ZmaFit wordmark (always LTR). */
export const Logo: React.FC<{size?: number}> = ({size = 80}) => (
  <div style={{display: 'flex', alignItems: 'center', gap: size * 0.22, direction: 'ltr'}}>
    <div
      style={{
        width: size, height: size, borderRadius: size * 0.26, background: COLORS.primary,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        boxShadow: `0 0 ${size * 0.6}px ${COLORS.primary}88`, transform: 'skewX(-8deg)',
      }}
    >
      <span style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: size * 0.68, color: COLORS.bg, lineHeight: 1}}>Z</span>
    </div>
    <span style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: size * 0.78, color: COLORS.white, letterSpacing: -1, lineHeight: 1}}>
      Zma<span style={{color: COLORS.primary}}>Fit</span>
    </span>
  </div>
);
