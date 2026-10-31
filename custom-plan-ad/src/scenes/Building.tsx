import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, lin} from '../anim';
import {COLORS, SCENES} from '../config';
import {Headline, PhoneLayout, SceneShell, SlamLine} from '../components/Layout';
import {PhoneFrame} from '../components/PhoneFrame';
import {useCopy, useFormat} from '../i18n';

const BURST = 40;

export const Building: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square} = useFormat();
  const ar = c.dir === 'rtl';
  const p = lin(f, 0, BURST - 2, 0, 1, (x) => 1 - Math.pow(1 - x, 2));
  const done = f >= BURST - 2;
  const burst = interpolate(f, [BURST, BURST + 18], [0, 1], clamp);
  const flash = interpolate(f, [BURST, BURST + 4, SCENES.building.duration], [0, 0.85, 0.5], clamp);
  return (
    <SceneShell duration={SCENES.building.duration} enter="none" exit="none">
      <PhoneLayout
        headline={
          <Headline size={square ? 62 : 92}>
            <SlamLine delay={0} color={done ? COLORS.primary : undefined}>{done ? c.building.done : c.building.title}</SlamLine>
          </Headline>
        }
        phone={
          <PhoneFrame glow={0.18 + p * 0.5}>
            <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 50, padding: '0 50px'}}>
              <div style={{position: 'relative', width: 300, height: 300}}>
                <svg width={300} height={300} viewBox="0 0 300 300" style={{position: 'absolute', inset: 0}}>
                  <circle cx={150} cy={150} r={128} stroke={COLORS.card} strokeWidth={22} fill="none" />
                  <circle
                    cx={150} cy={150} r={128} stroke={COLORS.primary} strokeWidth={22} fill="none" strokeLinecap="round"
                    pathLength={1} strokeDasharray={1} strokeDashoffset={1 - p} transform="rotate(-90 150 150)"
                    style={{filter: `drop-shadow(0 0 12px ${COLORS.primary})`}}
                  />
                </svg>
                <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Montserrat', fontWeight: 900, fontSize: 84, direction: 'ltr'}}>
                  {Math.round(p * 100)}%
                </div>
              </div>
              <div style={{width: '100%', height: 18, borderRadius: 9, background: COLORS.card, overflow: 'hidden'}}>
                <div style={{width: `${p * 100}%`, height: '100%', background: `linear-gradient(90deg, ${COLORS.primary}, ${COLORS.secondary})`}} />
              </div>
              <div style={{fontWeight: 800, fontSize: ar ? 42 : 38, color: COLORS.muted, textAlign: 'center'}}>{c.building.title}</div>
            </div>
          </PhoneFrame>
        }
      />
      {/* green light burst */}
      <AbsoluteFill style={{pointerEvents: 'none', overflow: 'hidden'}}>
        <div
          style={{
            position: 'absolute', left: '50%', top: '55%', width: 400, height: 400, marginLeft: -200, marginTop: -200, borderRadius: '50%',
            background: `radial-gradient(circle, #ffffff 0%, ${COLORS.primary} 35%, ${COLORS.primary}00 70%)`,
            transform: `scale(${burst * 9})`, opacity: burst > 0 ? 1 - burst * 0.3 : 0,
          }}
        />
        {burst > 0 &&
          Array.from({length: 16}).map((_, i) => (
            <div
              key={i}
              style={{
                position: 'absolute', left: '50%', top: '55%', width: 2400, height: 26, marginTop: -13, transformOrigin: '0 50%',
                background: `linear-gradient(90deg, #fff, ${COLORS.primary}00)`,
                transform: `rotate(${i * 22.5 + f}deg) scaleX(${burst})`, opacity: 0.7 * (1 - burst * 0.5),
              }}
            />
          ))}
        <AbsoluteFill style={{background: COLORS.primary, opacity: flash, mixBlendMode: 'screen'}} />
      </AbsoluteFill>
    </SceneShell>
  );
};
