import React from 'react';
import {COLORS} from '../config';

const pill: React.CSSProperties = {
  height: 96, borderRadius: 24, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
  padding: '0 34px', gap: 14, boxShadow: '0 12px 40px rgba(0,0,0,0.4)', direction: 'ltr',
};

export const PayPalBadge: React.FC = () => (
  <div style={pill}>
    <span style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: 46, fontStyle: 'italic', letterSpacing: -1}}>
      <span style={{color: '#003087'}}>Pay</span>
      <span style={{color: '#009CDE'}}>Pal</span>
    </span>
  </div>
);

export const CardBadge: React.FC<{label: string; font: string}> = ({label, font}) => (
  <div style={pill}>
    <svg width="66" height="46" viewBox="0 0 66 46">
      <rect x="1" y="1" width="64" height="44" rx="7" fill="#1A2330" />
      <rect x="1" y="10" width="64" height="8" fill="#000" opacity="0.55" />
      <rect x="8" y="26" width="12" height="9" rx="2" fill={COLORS.secondary} />
      <rect x="26" y="29" width="30" height="4" rx="2" fill="#ffffff66" />
    </svg>
    <span style={{fontFamily: font, fontWeight: 800, fontSize: 40, color: '#1A2330'}}>{label}</span>
  </div>
);
