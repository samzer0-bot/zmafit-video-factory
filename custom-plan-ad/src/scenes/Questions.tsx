import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {clamp, lin, pop} from '../anim';
import {COLORS, PRODUCT, SCENES} from '../config';
import {Check} from '../components/Icons';
import {Headline, PhoneLayout, SceneShell, SlamLine} from '../components/Layout';
import {PhoneFrame} from '../components/PhoneFrame';
import {useCopy, useFormat} from '../i18n';

const PER_Q = 22;
const START = 8;

const QuestionCard: React.FC<{index: number; local: number}> = ({index, local}) => {
  const c = useCopy();
  const ar = c.dir === 'rtl';
  const item = c.questions.items[index];
  const dirSign = ar ? -1 : 1;
  const enter = lin(local, 0, 6);
  const isLast = index === c.questions.items.length - 1;
  const exit = isLast ? 0 : lin(local, PER_Q - 4, PER_Q, 0, 1, (x) => x);
  const tapAt = 10;
  const picked = local >= tapAt;
  const tap = interpolate(local, [tapAt, tapAt + 8], [0, 1], clamp);
  return (
    <div style={{position: 'absolute', inset: '0 36px', opacity: enter * (1 - exit), transform: `translateX(${dirSign * ((1 - enter) * 300 - exit * 400)}px)`}}>
      <div style={{fontWeight: ar ? 900 : 800, fontSize: ar ? 66 : 60, lineHeight: 1.2, marginBottom: 56, minHeight: 170}}>{item.q}</div>
      {item.options.map((o, i) => {
        const on = picked && i === item.pick;
        const bump = on ? 1 + 0.06 * Math.sin(Math.min(1, tap) * Math.PI) : 1;
        return (
          <div
            key={o}
            style={{
              height: 150, borderRadius: 32, marginBottom: 30, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '0 34px', boxSizing: 'border-box', position: 'relative', overflow: 'hidden',
              background: on ? `${COLORS.primary}22` : COLORS.card,
              border: `4px solid ${on ? COLORS.primary : COLORS.cardBorder}`,
              transform: `scale(${bump})`,
              boxShadow: on ? `0 0 40px ${COLORS.primary}55` : 'none',
            }}
          >
            <span style={{fontWeight: 700, fontSize: ar ? 50 : 46, whiteSpace: 'nowrap'}}>{o}</span>
            <span
              style={{
                width: 56, height: 56, borderRadius: 28, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: `4px solid ${on ? COLORS.primary : COLORS.cardBorder}`, background: on ? COLORS.primary : 'transparent',
              }}
            >
              {on && <Check size={36} color={COLORS.bg} stroke={4} progress={tap} />}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export const QuestionsScreen: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const ar = c.dir === 'rtl';
  const qf = Math.max(0, f - START);
  const idx = Math.min(c.questions.items.length - 1, Math.floor(qf / PER_Q));
  const local = qf - idx * PER_Q;
  const num = c.questions.numbers[idx];
  const progress = interpolate(qf, [0, PER_Q * c.questions.items.length], [1 / 12, 1], clamp);
  return (
    <div style={{position: 'absolute', inset: 0, padding: '70px 0 0'}}>
      <div style={{padding: '0 36px', marginBottom: 90}}>
        <div style={{display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: ar ? 34 : 32, color: COLORS.muted, marginBottom: 18}}>
          <span>{c.questions.progress(num)}</span>
          <span style={{color: COLORS.primary, direction: 'ltr'}}>{Math.round(progress * 100)}%</span>
        </div>
        <div style={{height: 14, borderRadius: 7, background: COLORS.card, overflow: 'hidden'}}>
          <div style={{height: '100%', width: `${progress * 100}%`, background: `linear-gradient(90deg, ${COLORS.primary}, #7CFFB8)`, borderRadius: 7, marginInlineStart: 0}} />
        </div>
      </div>
      <div style={{position: 'relative', height: 800}}>
        <QuestionCard key={idx} index={idx} local={local} />
      </div>
    </div>
  );
};

export const Questions: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square} = useFormat();
  const phoneIn = pop(f, 0, 14, 150);
  const counter = Math.round(interpolate(f, [4, 22], [1, PRODUCT.questions], clamp));
  return (
    <SceneShell duration={SCENES.questions.duration} exit="none">
      <PhoneLayout
        phoneEnter={phoneIn}
        headline={
          <Headline size={square ? 62 : 96}>
            <SlamLine delay={0}>
              {c.questions.pre}
              <span style={{color: COLORS.primary, display: 'inline-block', minWidth: '1.3em', textAlign: 'center', direction: 'ltr'}}>{counter}</span>
            </SlamLine>
            <SlamLine delay={4}>{c.questions.post.trim()}</SlamLine>
          </Headline>
        }
        phone={
          <PhoneFrame>
            <QuestionsScreen />
          </PhoneFrame>
        }
      />
    </SceneShell>
  );
};
