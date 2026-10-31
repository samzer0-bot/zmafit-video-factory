import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, fmt, lin, pop} from '../anim';
import {COLORS, SAMPLE, SCENES} from '../config';
import {Cart, Check, Dumbbell, Flame, ListCheck, Meal, Swap, Triangle} from '../components/Icons';
import {Headline, PhoneLayout, SceneShell, SlamLine} from '../components/Layout';
import {PhoneFrame} from '../components/PhoneFrame';
import {useCopy, useFormat} from '../i18n';

const GAP = 34;
const FIRST = 12;
const at = (i: number) => FIRST + i * GAP;

const CardRow: React.FC<{i: number; icon: React.ReactNode; accent: string; title: string; children?: React.ReactNode}> = ({i, icon, accent, title, children}) => {
  const f = useCurrentFrame();
  const c = useCopy();
  const ar = c.dir === 'rtl';
  const p = pop(f, at(i), 13, 200);
  const active = f >= at(i) && f < at(i + 1);
  return (
    <div
      style={{
        height: 170, borderRadius: 30, background: COLORS.card, marginBottom: 18, padding: '0 20px', boxSizing: 'border-box',
        display: 'flex', alignItems: 'center', gap: 18,
        border: `3px solid ${active ? accent : COLORS.cardBorder}`,
        boxShadow: active ? `0 0 36px ${accent}55` : 'none',
        opacity: Math.min(1, p * 1.4),
        transform: `translateX(${(ar ? -1 : 1) * (1 - p) * 420}px) scale(${0.9 + 0.1 * p})`,
      }}
    >
      <div style={{width: 78, height: 78, borderRadius: 22, background: `${accent}22`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0}}>
        {icon}
      </div>
      <div style={{flex: 1, minWidth: 0}}>
        <div style={{fontWeight: 800, fontSize: ar ? 34 : 31, lineHeight: 1.2, marginBottom: 12, whiteSpace: 'nowrap'}}>{title}</div>
        {children}
      </div>
    </div>
  );
};

const Pill: React.FC<{children: React.ReactNode; color: string; on?: number; style?: React.CSSProperties}> = ({children, color, on = 1, style}) => {
  const c = useCopy();
  return (
    <span
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6, height: 46, padding: '0 12px', borderRadius: 23, boxSizing: 'border-box',
        fontWeight: 700, fontSize: c.dir === 'rtl' ? 24 : 21, whiteSpace: 'nowrap',
        background: on > 0.5 ? `${color}2A` : '#ffffff0D', color: on > 0.5 ? color : COLORS.muted,
        border: `2px solid ${on > 0.5 ? color : 'transparent'}`, transform: `scale(${0.9 + 0.1 * on})`, ...style,
      }}
    >
      {children}
    </span>
  );
};

const Sub: React.FC<{children: React.ReactNode}> = ({children}) => {
  const c = useCopy();
  return <div style={{fontWeight: 600, fontSize: c.dir === 'rtl' ? 26 : 24, color: COLORS.muted, whiteSpace: 'nowrap'}}>{children}</div>;
};

export const PlanScreen: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const ar = c.dir === 'rtl';
  const P = c.plan;
  const count = lin(f, at(0) + 4, at(0) + 30, 0, 1, (x) => 1 - Math.pow(1 - x, 3));
  const week2 = pop(f, at(5) - 4, 14, 180);
  return (
    <div style={{position: 'absolute', inset: 0, padding: '22px 30px 0'}}>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 26, padding: '0 6px'}}>
        <div style={{fontWeight: 900, fontSize: ar ? 42 : 38, whiteSpace: 'nowrap'}}>{P.phoneTitle}</div>
        <span style={{fontWeight: 700, fontSize: ar ? 24 : 22, color: COLORS.secondary, border: `2px solid ${COLORS.secondary}`, borderRadius: 16, padding: '4px 14px'}}>{P.sample}</span>
      </div>

      <CardRow i={0} accent={COLORS.secondary} title={P.cards.calories} icon={<Flame size={54} color={COLORS.secondary} />}>
        <div style={{display: 'flex', gap: 10, alignItems: 'baseline', whiteSpace: 'nowrap'}}>
          <span style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: 36, color: COLORS.secondary, direction: 'ltr', display: 'inline-block', minWidth: 104}}>{fmt(SAMPLE.calories * count)}</span>
          <span style={{fontWeight: 600, fontSize: ar ? 23 : 21, color: COLORS.muted}}>{P.kcal}</span>
          <span style={{fontFamily: 'Montserrat', fontWeight: 900, fontSize: 36, color: COLORS.primary, direction: 'ltr', display: 'inline-block', minWidth: 64}}>{fmt(SAMPLE.protein * count)}</span>
          <span style={{fontWeight: 600, fontSize: ar ? 23 : 21, color: COLORS.muted}}>{P.protein}</span>
        </div>
      </CardRow>

      <CardRow i={1} accent={COLORS.primary} title={P.cards.workouts} icon={<Dumbbell size={56} color={COLORS.primary} />}>
        <div style={{display: 'flex', gap: 10}}>
          {P.weeks.map((w, k) => (
            
            <Pill key={w} color={COLORS.primary} on={interpolate(f, [at(1) + 6 + k * 5, at(1) + 9 + k * 5], [0, 1], clamp)} style={{padding: '0 16px'}}>{w}</Pill>
          ))}
        </div>
      </CardRow>

      <CardRow i={2} accent={COLORS.secondary} title={P.cards.meals} icon={<Meal size={54} color={COLORS.secondary} />}>
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <Cart size={30} color={COLORS.muted} />
          <Sub>{P.cards.mealsSub}</Sub>
        </div>
      </CardRow>

      <CardRow i={3} accent={COLORS.primary} title={P.cards.variations} icon={<Swap size={54} color={COLORS.primary} />}>
        <div style={{display: 'flex', gap: 12}}>
          <Pill color={COLORS.primary} on={interpolate(f, [at(3) + 6, at(3) + 9], [0, 1], clamp)}><Triangle size={18} color={COLORS.primary} />{P.cards.easier}</Pill>
          <Pill color={COLORS.secondary} on={interpolate(f, [at(3) + 12, at(3) + 15], [0, 1], clamp)}><Triangle size={18} up color={COLORS.secondary} />{P.cards.harder}</Pill>
        </div>
      </CardRow>

      <CardRow i={4} accent={COLORS.primary} title={P.cards.habits} icon={<ListCheck size={54} color={COLORS.primary} />}>
        <div style={{display: 'flex', gap: 8}}>
          {P.habits.map((h, k) => {
            const on = interpolate(f, [at(4) + 6 + k * 6, at(4) + 12 + k * 6], [0, 1], clamp);
            return (
              <Pill key={h} color={COLORS.primary} on={on}>
                <span style={{width: 24, height: 24, borderRadius: 7, background: on > 0 ? COLORS.primary : 'transparent', border: `2px solid ${on > 0 ? COLORS.primary : COLORS.muted}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box'}}>
                  <Check size={18} color={COLORS.bg} stroke={4} progress={on} />
                </span>
                {h}
              </Pill>
            );
          })}
        </div>
      </CardRow>

      <div
        style={{
          marginTop: 6, height: 74, borderRadius: 22, border: `2px dashed ${COLORS.secondary}`, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
          fontWeight: 700, fontSize: ar ? 28 : 25, color: COLORS.secondary, opacity: week2, transform: `scale(${0.85 + 0.15 * week2})`, whiteSpace: 'nowrap',
        }}
      >
        + {P.week2}
      </div>
    </div>
  );
};

export const Plan: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square} = useFormat();
  const flash = interpolate(f, [0, 14], [0.5, 0], clamp);
  return (
    <SceneShell duration={SCENES.plan.duration} enter="none">
      <PhoneLayout
        headline={
          <Headline size={square ? 62 : 96}>
            <SlamLine delay={2}>{c.plan.headline}</SlamLine>
          </Headline>
        }
        phone={
          <PhoneFrame glow={0.3}>
            <PlanScreen />
          </PhoneFrame>
        }
      />
      <AbsoluteFill style={{background: COLORS.primary, opacity: flash, mixBlendMode: 'screen', pointerEvents: 'none'}} />
    </SceneShell>
  );
};
