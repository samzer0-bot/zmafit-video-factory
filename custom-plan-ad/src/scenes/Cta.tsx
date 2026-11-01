import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {pop} from '../anim';
import {COLORS, PRODUCT, SCENES} from '../config';
import {Arrow} from '../components/Icons';
import {Logo} from '../components/Logo';
import {SceneShell} from '../components/Layout';
import {useCopy, useFormat} from '../i18n';

export const Cta: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square} = useFormat();
  const ar = c.dir === 'rtl';
  const logo = pop(f, 0, 12, 180);
  const btn = pop(f, 8, 10, 200);
  const url = pop(f, 16, 14, 180);
  const beat = (f % 15) / 15;
  const pulse = 1 + 0.045 * Math.exp(-beat * 6);
  const S = square ? 0.8 : 1;
  return (
    <SceneShell duration={SCENES.cta.duration} exit="none">
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{transform: `scale(${S})`, display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: square ? -40 : -120}}>
          <div style={{opacity: logo, transform: `scale(${0.6 + 0.4 * logo})`, marginBottom: 110}}>
            <Logo size={120} />
          </div>
          <div
            style={{
              display: 'flex', alignItems: 'center', gap: 26, padding: ar ? '22px 70px 30px' : '40px 70px', borderRadius: 999,
              background: `linear-gradient(135deg, ${COLORS.primary}, #12C46C)`, color: COLORS.bg,
              boxShadow: `0 0 ${80 * pulse}px ${COLORS.primary}AA, 0 16px 0 #0E8F4F`,
              transform: `scale(${(0.5 + 0.5 * btn) * pulse})`, opacity: Math.min(1, btn * 1.5),
            }}
          >
            <span style={{fontWeight: 900, fontSize: ar ? 92 : 78, textTransform: c.uppercase ? 'uppercase' : 'none', whiteSpace: 'nowrap', letterSpacing: ar ? 0 : -1}}>
              {c.cta.button}
            </span>
            <Arrow size={78} color={COLORS.bg} stroke={3.4} flip={ar} />
          </div>
          <div
            style={{
              marginTop: 90, fontFamily: 'Montserrat', fontWeight: 800, fontSize: 60, direction: 'ltr', color: COLORS.white,
              padding: '18px 40px', borderRadius: 24, border: `3px solid ${COLORS.cardBorder}`, background: '#0B0F14CC',
              opacity: url, transform: `translateY(${(1 - url) * 40}px)`,
            }}
          >
            {PRODUCT.url.split('/')[0]}<span style={{color: COLORS.primary}}>/{PRODUCT.url.split('/')[1]}</span>
          </div>
        </div>
        <div
          style={{
            position: 'absolute', left: 60, right: 60, bottom: square ? 40 : 170, textAlign: 'center',
            fontWeight: 600, fontSize: square ? 26 : 30, color: '#B4BFCC',
          }}
        >
          {c.cta.disclaimer}
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
