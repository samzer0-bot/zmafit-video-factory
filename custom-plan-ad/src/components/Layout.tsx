import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, pop} from '../anim';
import {COLORS} from '../config';
import {useCopy, useFormat} from '../i18n';
import {PHONE_H, PHONE_W} from './PhoneFrame';

/** Wraps a scene: sets direction/font and handles enter/exit transitions. */
export const SceneShell: React.FC<{
  duration: number;
  children: React.ReactNode;
  enter?: 'zoom' | 'none';
  exit?: 'zoom' | 'none';
}> = ({duration, children, enter = 'zoom', exit = 'zoom'}) => {
  const f = useCurrentFrame();
  const c = useCopy();
  const inP = enter === 'zoom' ? interpolate(f, [0, 8], [0, 1], clamp) : 1;
  const outP = exit === 'zoom' ? interpolate(f, [duration - 6, duration], [0, 1], clamp) : 0;
  return (
    <AbsoluteFill
      style={{
        direction: c.dir,
        fontFamily: c.font,
        color: COLORS.white,
        opacity: inP * (1 - outP),
        transform: `scale(${(0.92 + 0.08 * inP) * (1 + 0.08 * outP)})`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

/** Big bold headline text block. */
export const Headline: React.FC<{children: React.ReactNode; size?: number; style?: React.CSSProperties}> = ({children, size = 92, style}) => {
  const c = useCopy();
  const ar = c.dir === 'rtl';
  return (
    <div
      style={{
        fontFamily: c.font,
        fontWeight: ar ? 900 : 800,
        fontSize: ar ? size * 1.08 : size,
        lineHeight: ar ? 1.3 : 1.05,
        letterSpacing: ar ? 0 : -1.5,
        textTransform: c.uppercase ? 'uppercase' : 'none',
        color: COLORS.white,
        textShadow: '0 6px 30px rgba(0,0,0,0.5)',
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Animated line that slams in. */
export const SlamLine: React.FC<{delay: number; children: React.ReactNode; color?: string; style?: React.CSSProperties}> = ({delay, children, color, style}) => {
  const f = useCurrentFrame();
  const p = pop(f, delay, 11, 220);
  return (
    <div style={{display: 'block', color, opacity: Math.min(1, p * 1.5), transform: `translateY(${(1 - p) * 60}px) scale(${0.7 + 0.3 * p})`, ...style}}>
      {children}
    </div>
  );
};

export const PHONE_SCALE = {vertical: 0.9, square: 0.72};

/**
 * Headline + phone layout.
 * vertical: headline on top, phone below. square: headline beside phone (flips automatically in RTL).
 */
export const PhoneLayout: React.FC<{
  headline: React.ReactNode;
  phone: React.ReactNode;
  phoneEnter?: number; // 0..1 slide-up progress
}> = ({headline, phone, phoneEnter = 1}) => {
  const {square} = useFormat();
  const s = square ? PHONE_SCALE.square : PHONE_SCALE.vertical;
  const pw = PHONE_W * s;
  const ph = PHONE_H * s;
  const slide = (1 - phoneEnter) * 900;
  if (square) {
    return (
      <AbsoluteFill>
        <div style={{position: 'absolute', insetInlineStart: 64, width: 1080 - pw - 64 * 2 - 40, top: 0, bottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', textAlign: 'start'}}>
          {headline}
        </div>
        <div style={{position: 'absolute', insetInlineEnd: 64, top: (1080 - ph) / 2 + slide, width: pw, height: ph}}>
          <div style={{transform: `scale(${s})`, transformOrigin: 'top left', width: PHONE_W, height: PHONE_H, position: 'absolute', left: 0, top: 0}}>{phone}</div>
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 60, right: 60, top: 120, height: 320, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center'}}>
        {headline}
      </div>
      <div style={{position: 'absolute', left: (1080 - pw) / 2, top: 470 + slide, width: pw, height: ph}}>
        <div style={{transform: `scale(${s})`, transformOrigin: 'top left', width: PHONE_W, height: PHONE_H, position: 'absolute', left: 0, top: 0}}>{phone}</div>
      </div>
    </AbsoluteFill>
  );
};
