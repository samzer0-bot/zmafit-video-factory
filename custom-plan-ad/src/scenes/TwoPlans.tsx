import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, pop} from '../anim';
import {BEATS, COLORS, SCENES} from '../config';
import {Check} from '../components/Icons';
import {Headline, SceneShell, SlamLine} from '../components/Layout';
import {useCopy, useFormat} from '../i18n';

const ROWS_START = 30;
const ROW_GAP = 7;

const Arrow: React.FC<{color: string}> = ({color}) => (
  <svg width={60} height={70} viewBox="0 0 60 70">
    <path d="M30 4v54M12 42l18 20 18-20" stroke={color} strokeWidth={8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const Column: React.FC<{
  side: 0 | 1;
  enterAt: number;
  label: string;
  answers: string[];
  plan: string[];
  accent: string;
}> = ({side, enterAt, label, answers, plan, accent}) => {
  const f = useCurrentFrame();
  const c = useCopy();
  const ar = c.dir === 'rtl';
  const p = pop(f, enterAt, 13, 180);
  // column 0 comes from the inline-start side, column 1 from the inline-end side
  const from = (side === 0 ? -1 : 1) * (ar ? -1 : 1);
  return (
    <div style={{width: 470, display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: Math.min(1, p * 1.4), transform: `translateX(${from * (1 - p) * 500}px)`}}>
      <div style={{fontWeight: 900, fontSize: ar ? 40 : 34, color: COLORS.bg, background: accent, borderRadius: 30, padding: ar ? '2px 30px 8px' : '8px 30px', marginBottom: 22, letterSpacing: ar ? 0 : 1, textTransform: c.uppercase ? 'uppercase' : 'none'}}>
        {label}
      </div>
      <div style={{width: '100%', boxSizing: 'border-box', background: COLORS.card, border: `3px solid ${COLORS.cardBorder}`, borderRadius: 32, padding: 24, display: 'flex', flexWrap: 'wrap', gap: 14, justifyContent: 'center', minHeight: 252, alignContent: 'center'}}>
        {answers.map((a) => (
          <span key={a} style={{fontWeight: 700, fontSize: ar ? 33 : 30, color: COLORS.white, background: '#ffffff12', borderRadius: 22, padding: ar ? '2px 18px 6px' : '9px 18px', whiteSpace: 'nowrap'}}>
            {a}
          </span>
        ))}
      </div>
      <div style={{margin: '18px 0', opacity: interpolate(f, [enterAt + 10, enterAt + 16], [0, 1], clamp)}}>
        <Arrow color={accent} />
      </div>
      <div style={{width: '100%', boxSizing: 'border-box', borderRadius: 32, padding: '30px 22px 10px', background: `${accent}14`, border: `4px solid ${accent}`, boxShadow: `0 0 50px ${accent}40`}}>
        {plan.map((row, k) => {
          const at = ROWS_START + k * ROW_GAP + side * 3;
          const on = interpolate(f, [at, at + 6], [0, 1], clamp);
          return (
            <div key={row} style={{display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24, opacity: 0.25 + 0.75 * on, transform: `scale(${0.94 + 0.06 * on})`}}>
              <span style={{width: 48, height: 48, borderRadius: 13, flexShrink: 0, background: on > 0 ? accent : 'transparent', border: `3px solid ${accent}`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box'}}>
                <Check size={30} color={COLORS.bg} stroke={4} progress={on} />
              </span>
              <span style={{fontWeight: 800, fontSize: ar ? 34 : 31, lineHeight: 1.25}}>{row}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const TwoPlans: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square, bleed} = useFormat();
  const ar = c.dir === 'rtl';
  const T = c.twoPlans;
  const neq = pop(f, 24, 9, 220);
  const footer = pop(f, 60, 13, 180);
  const flash = interpolate(f, [0, 14], [0.55, 0], clamp);
  const S = square ? 0.66 : 1;
  return (
    <SceneShell duration={SCENES.twoPlans.duration} enter="none">
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{width: 1080, transform: `scale(${S})`, transformOrigin: 'center center', marginTop: square ? 0 : -60, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
          <Headline size={92} style={{textAlign: 'center', marginBottom: 50}}>
            <SlamLine delay={0}>{T.headline[0]}</SlamLine>
            <SlamLine delay={4} color={COLORS.primary}>{T.headline[1]}</SlamLine>
          </Headline>
          <div style={{position: 'relative', display: 'flex', gap: 40, alignItems: 'flex-start'}}>
            <Column side={0} enterAt={BEATS.twoPlansA} label={T.personA} answers={T.answersA} plan={T.planA} accent={COLORS.secondary} />
            <Column side={1} enterAt={BEATS.twoPlansB} label={T.personB} answers={T.answersB} plan={T.planB} accent={COLORS.primary} />
            <div
              style={{
                position: 'absolute', left: '50%', top: 170, width: 96, height: 96, marginLeft: -48, borderRadius: 48,
                background: COLORS.white, color: COLORS.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'Montserrat', fontWeight: 900, fontSize: 64, lineHeight: 1, boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
                transform: `scale(${neq})`, direction: 'ltr',
              }}
            >
              <svg width={56} height={56} viewBox="0 0 56 56">
                <path d="M8 21h40M8 35h40M36 6L20 50" stroke={COLORS.bg} strokeWidth={7} strokeLinecap="round" />
              </svg>
            </div>
          </div>
          <div
            style={{
              marginTop: 50, display: 'flex', alignItems: 'center', gap: 18, padding: ar ? '10px 40px 18px' : '18px 40px', borderRadius: 60,
              background: COLORS.white, color: COLORS.bg, fontWeight: 900, fontSize: ar ? 50 : 44,
              textTransform: c.uppercase ? 'uppercase' : 'none', opacity: footer, transform: `scale(${0.6 + 0.4 * footer})`,
            }}
          >
            {T.footer}
          </div>
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{background: COLORS.primary, opacity: flash, mixBlendMode: 'screen', pointerEvents: 'none', top: -bleed, bottom: -bleed, height: 'auto'}} />
    </SceneShell>
  );
};
