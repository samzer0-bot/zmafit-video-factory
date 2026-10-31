import React from 'react';
import {COLORS} from '../config';

export const PHONE_W = 640;
export const PHONE_H = 1300;

/** Clean phone mock-up. Content area is (PHONE_W-36) x (PHONE_H-36) logical px. */
export const PhoneFrame: React.FC<{children: React.ReactNode; glow?: number}> = ({children, glow = 0.18}) => (
  <div
    style={{
      width: PHONE_W, height: PHONE_H, borderRadius: 90, padding: 18, boxSizing: 'border-box',
      background: 'linear-gradient(145deg, #2A323D, #12171E)',
      boxShadow: `0 0 0 3px #343E4B, 0 50px 120px rgba(0,0,0,0.65), 0 0 120px rgba(34,229,132,${glow})`,
    }}
  >
    <div style={{width: '100%', height: '100%', borderRadius: 72, background: '#0E141B', overflow: 'hidden', position: 'relative'}}>
      {/* status bar */}
      <div style={{position: 'absolute', top: 22, left: 0, right: 0, height: 40, display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 52px', direction: 'ltr', fontFamily: 'Montserrat', fontWeight: 700, fontSize: 24, color: COLORS.white, zIndex: 5}}>
        <span>9:41</span>
        <span style={{display: 'flex', gap: 8, alignItems: 'center'}}>
          <span style={{display: 'flex', gap: 3, alignItems: 'flex-end'}}>
            {[10, 15, 20, 25].map((h) => <span key={h} style={{width: 5, height: h, background: COLORS.white, borderRadius: 2}} />)}
          </span>
          <span style={{width: 40, height: 20, border: `2px solid ${COLORS.white}`, borderRadius: 6, padding: 2, boxSizing: 'border-box'}}>
            <span style={{display: 'block', width: '80%', height: '100%', background: COLORS.primary, borderRadius: 2}} />
          </span>
        </span>
      </div>
      <div style={{position: 'absolute', top: 18, left: '50%', marginLeft: -80, width: 160, height: 46, borderRadius: 30, background: '#000', zIndex: 6}} />
      <div style={{position: 'absolute', top: 90, left: 0, right: 0, bottom: 30}}>{children}</div>
      <div style={{position: 'absolute', bottom: 14, left: '50%', marginLeft: -90, width: 180, height: 7, borderRadius: 4, background: '#ffffff55'}} />
    </div>
  </div>
);
