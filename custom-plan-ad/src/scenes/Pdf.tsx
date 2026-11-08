import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, pop} from '../anim';
import {COLORS, SCENES} from '../config';
import {Clock} from '../components/Icons';
import {Headline, SceneShell, SlamLine} from '../components/Layout';
import {useCopy, useFormat} from '../i18n';

const PdfDoc: React.FC = () => (
  <div style={{width: 300, height: 380, position: 'relative', direction: 'ltr'}}>
    <svg width={300} height={380} viewBox="0 0 300 380" style={{position: 'absolute', inset: 0}}>
      <path d="M20 0h190l90 90v270a20 20 0 0 1-20 20H20A20 20 0 0 1 0 360V20A20 20 0 0 1 20 0z" fill="#F4F6F8" />
      <path d="M210 0v70a20 20 0 0 0 20 20h70z" fill="#C9D1DA" />
      {[150, 185, 220, 255].map((y, i) => <rect key={y} x={36} y={y} width={i % 2 ? 160 : 220} height={14} rx={7} fill="#D5DCE3" />)}
    </svg>
    <div style={{position: 'absolute', left: -30, bottom: 34, background: COLORS.danger, color: '#fff', fontFamily: 'Montserrat', fontWeight: 900, fontSize: 64, padding: '6px 26px', borderRadius: 16, boxShadow: '0 10px 30px rgba(0,0,0,0.4)'}}>
      PDF
    </div>
  </div>
);

export const Pdf: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square} = useFormat();
  const ar = c.dir === 'rtl';
  const drop = pop(f, 10, 9, 140);
  const tray = pop(f, 4, 14, 160);
  const chip = pop(f, 24, 14, 180);
  const squash = interpolate(drop, [0.85, 1, 1.1], [1, 1, 0.92], clamp);
  return (
    <SceneShell duration={SCENES.pdf.duration}>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: square ? 20 : 90, padding: '0 60px'}}>
        <div style={{textAlign: 'center'}}>
          <Headline size={square ? 78 : 104}>
            <SlamLine delay={0}>{c.pdf.line1}</SlamLine>
            <SlamLine delay={5} color={COLORS.primary}>{c.pdf.line2}</SlamLine>
          </Headline>
          <div
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 16, marginTop: square ? 28 : 44, padding: '18px 30px', borderRadius: 40,
              background: COLORS.card, border: `3px solid ${COLORS.cardBorder}`, fontWeight: 700, fontSize: ar ? 38 : 34,
              opacity: chip, transform: `scale(${0.8 + 0.2 * chip})`, whiteSpace: 'nowrap',
            }}
          >
            <Clock size={46} color={COLORS.secondary} />
            <span>{c.pdf.chip}</span>
          </div>
        </div>
        <div style={{width: 420 * (square ? 0.6 : 1), height: 560 * (square ? 0.6 : 1), flexShrink: 0, position: 'relative'}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: 420, height: 560, transform: square ? 'scale(0.6)' : undefined, transformOrigin: 'top left', direction: 'ltr'}}>
          <div style={{position: 'absolute', left: 60, top: 20, transform: `translateY(${(1 - drop) * -900}px) scaleY(${squash})`, transformOrigin: '50% 100%', filter: `drop-shadow(0 0 40px ${COLORS.primary}55)`}}>
            <PdfDoc />
          </div>
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 20, height: 110, opacity: tray, transform: `scaleX(${tray})`}}>
            <svg width={420} height={110} viewBox="0 0 420 110">
              <path d="M10 10v60a30 30 0 0 0 30 30h340a30 30 0 0 0 30-30V10" stroke={COLORS.primary} strokeWidth={16} fill="none" strokeLinecap="round" />
            </svg>
          </div>
        </div>
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
