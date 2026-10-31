import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, pop} from '../anim';
import {COLORS, PRODUCT, SCENES} from '../config';
import {Check} from '../components/Icons';
import {SceneShell} from '../components/Layout';
import {CardBadge, PayPalBadge} from '../components/PaymentLogos';
import {useCopy, useFormat} from '../i18n';

export const Price: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square} = useFormat();
  const ar = c.dir === 'rtl';
  const n = Math.round(interpolate(f, [0, 16], [0, PRODUCT.price], {...clamp, easing: (x) => 1 - Math.pow(1 - x, 3)}));
  const big = pop(f, 0, 9, 200);
  const one = pop(f, 10, 13, 200);
  const noSub = pop(f, 18, 13, 200);
  const pay = pop(f, 30, 14, 180);
  const S = square ? 0.78 : 1;
  const priceStr = ar ? `${n}${PRODUCT.currency}` : `${PRODUCT.currency}${n}`;
  return (
    <SceneShell duration={SCENES.price.duration}>
      <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
        <div style={{transform: `scale(${S})`, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
          <div
            style={{
              fontFamily: 'Montserrat', fontWeight: 900, fontSize: 380, lineHeight: 1, color: COLORS.white, direction: 'ltr', letterSpacing: -10,
              textShadow: `0 0 80px ${COLORS.secondary}AA, 0 10px 0 ${COLORS.secondary}`, transform: `scale(${0.4 + 0.6 * big})`,
            }}
          >
            {priceStr}
          </div>
          <div style={{fontWeight: ar ? 900 : 800, fontSize: ar ? 92 : 84, color: COLORS.secondary, textTransform: c.uppercase ? 'uppercase' : 'none', marginTop: 10, opacity: one, transform: `translateY(${(1 - one) * 40}px)`}}>
            {c.price.oneTime}
          </div>
          <div
            style={{
              marginTop: 40, display: 'flex', alignItems: 'center', gap: 20, padding: '20px 40px', borderRadius: 60,
              background: `${COLORS.primary}1F`, border: `4px solid ${COLORS.primary}`, opacity: noSub, transform: `scale(${0.7 + 0.3 * noSub})`,
            }}
          >
            <span style={{width: 64, height: 64, borderRadius: 32, background: COLORS.primary, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <Check size={42} color={COLORS.bg} stroke={4} progress={interpolate(f, [20, 28], [0, 1], clamp)} />
            </span>
            <span style={{fontWeight: ar ? 900 : 800, fontSize: ar ? 62 : 56, whiteSpace: 'nowrap'}}>{c.price.noSub}</span>
          </div>
          <div style={{marginTop: 80, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 26, opacity: pay, transform: `translateY(${(1 - pay) * 60}px)`}}>
            <div style={{fontWeight: 700, fontSize: ar ? 40 : 36, color: COLORS.muted}}>{c.price.payWith}</div>
            <div style={{display: 'flex', gap: 30}}>
              <PayPalBadge />
              <CardBadge label={c.price.card} font={c.font} />
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};
