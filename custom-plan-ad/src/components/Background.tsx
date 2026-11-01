import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS} from '../config';

/** Dark sporty background: moving grid, speed stripes and glows pulsing on a 120 BPM beat. */
export const Background: React.FC = () => {
  const f = useCurrentFrame();
  const beat = (f % 15) / 15; // 15 frames = 1 beat @120 BPM
  const pulse = 1 + 0.06 * Math.exp(-beat * 5);
  return (
    <AbsoluteFill style={{background: COLORS.bg, overflow: 'hidden'}}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${COLORS.white}08 2px, transparent 2px), linear-gradient(90deg, ${COLORS.white}08 2px, transparent 2px)`,
          backgroundSize: '90px 90px',
          backgroundPosition: `0px ${(f * 2) % 90}px`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(-55deg, transparent 0 140px, ${COLORS.primary}0A 140px 150px, transparent 150px 300px)`,
          backgroundPosition: `${(f * 6) % 600}px 0px`,
        }}
      />
      <div
        style={{
          position: 'absolute', width: 1100, height: 1100, borderRadius: '50%',
          left: -400 + Math.sin(f / 40) * 80, top: -300 + Math.cos(f / 50) * 60,
          background: `radial-gradient(circle, ${COLORS.primary}33 0%, transparent 65%)`,
          transform: `scale(${pulse})`,
        }}
      />
      <div
        style={{
          position: 'absolute', width: 1000, height: 1000, borderRadius: '50%',
          right: -420 + Math.cos(f / 45) * 70, bottom: -380 + Math.sin(f / 35) * 70,
          background: `radial-gradient(circle, ${COLORS.secondary}2A 0%, transparent 65%)`,
          transform: `scale(${pulse})`,
        }}
      />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.55) 100%)'}} />
    </AbsoluteFill>
  );
};
