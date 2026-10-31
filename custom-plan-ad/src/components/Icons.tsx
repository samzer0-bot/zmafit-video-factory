import React from 'react';

type P = {size?: number; color?: string; stroke?: number};
const base = (size: number) => ({width: size, height: size, viewBox: '0 0 24 24', fill: 'none' as const});

export const Flame: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2c1 3.5 5 6 5 11a5 5 0 0 1-10 0c0-2.2 1-3.8 2.2-5 .3 1.6 1 2.6 2.3 3C11 8.5 11.3 5 12 2z" />
  </svg>
);
export const Dumbbell: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <path d="M6.5 6.5v11M17.5 6.5v11M3.5 9v6M20.5 9v6M6.5 12h11" />
  </svg>
);
export const Meal: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 3v7a2 2 0 0 0 2 2h0a2 2 0 0 0 2-2V3M6 12v9M17 3c-2 1.5-3 4-3 7h3v11" />
  </svg>
);
export const Cart: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 4h2l2.4 11h10.2L20 7H6.2" />
    <circle cx="9" cy="19.5" r="1.5" />
    <circle cx="17" cy="19.5" r="1.5" />
  </svg>
);
export const Swap: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 4v16M7 20l-3-3M7 20l3-3M17 20V4M17 4l-3 3M17 4l3 3" />
  </svg>
);
export const ListCheck: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 6l2 2 3-3M3 13l2 2 3-3M3 20l2 2 3-3M11 7h10M11 14h10M11 21h10" />
  </svg>
);
export const Check: React.FC<P & {progress?: number}> = ({size = 32, color = '#fff', stroke = 3, progress = 1}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 12.5l5 5L20 6.5" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - progress} />
  </svg>
);
export const Clock: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </svg>
);
export const Arrow: React.FC<P & {flip?: boolean}> = ({size = 48, color = '#fff', stroke = 3, flip}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={{transform: flip ? 'scaleX(-1)' : undefined}}>
    <path d="M4 12h15M13 6l6 6-6 6" />
  </svg>
);
export const Triangle: React.FC<{size?: number; color: string; up?: boolean}> = ({size = 20, color, up}) => (
  <svg width={size} height={size} viewBox="0 0 20 20" style={{transform: up ? undefined : 'rotate(180deg)'}}>
    <path d="M10 3l8 13H2z" fill={color} />
  </svg>
);
export const Lock: React.FC<P> = ({size = 48, color = '#fff', stroke = 2}) => (
  <svg {...base(size)} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="10" width="16" height="11" rx="2" />
    <path d="M8 10V7a4 4 0 0 1 8 0v3" />
  </svg>
);
