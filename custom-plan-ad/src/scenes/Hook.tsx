import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, lin, pop} from '../anim';
import {COLORS, SCENES} from '../config';
import {Headline, SceneShell, SlamLine} from '../components/Layout';
import {useCopy, useFormat} from '../i18n';

const TEAR_AT = 46;

// zig-zag tear line down the middle of the paper (percent coords)
const ZIG = [50, 46, 54, 47, 53, 45, 55, 48, 52, 46, 53, 50];
const zigPoints = ZIG.map((x, i) => `${x}% ${(i / (ZIG.length - 1)) * 100}%`);
const LEFT_CLIP = `polygon(0% 0%, ${zigPoints.join(', ')}, 0% 100%)`;
const RIGHT_CLIP = `polygon(100% 0%, ${zigPoints.join(', ')}, 100% 100%)`;

const Paper: React.FC = () => {
  const c = useCopy();
  const ar = c.dir === 'rtl';
  return (
    <div
      style={{
        width: 600, height: 760, background: COLORS.paper, borderRadius: 10, padding: '56px 52px', boxSizing: 'border-box',
        boxShadow: '0 40px 80px rgba(0,0,0,0.5)', fontFamily: c.font, color: COLORS.paperInk, position: 'relative',
        backgroundImage: 'repeating-linear-gradient(0deg, transparent 0 59px, #00000012 59px 61px)',
      }}
    >
      <div style={{fontWeight: 900, fontSize: ar ? 64 : 52, letterSpacing: ar ? 0 : 1, lineHeight: 1.2}}>{c.paper.title}</div>
      <div style={{fontWeight: 700, fontSize: 32, opacity: 0.6, marginTop: 6}}>{c.paper.sub}</div>
      <div style={{height: 4, background: COLORS.paperInk, opacity: 0.25, margin: '30px 0 26px'}} />
      {c.paper.rows.map((r) => (
        <div key={r} style={{display: 'flex', alignItems: 'center', gap: 18, marginBottom: 34}}>
          <div style={{width: 22, height: 22, borderRadius: 4, border: `3px solid ${COLORS.paperInk}66`, flexShrink: 0}} />
          <div style={{fontWeight: 700, fontSize: ar ? 34 : 30}}>{r}</div>
        </div>
      ))}
      {[0.9, 0.7, 0.8].map((w, i) => (
        <div key={i} style={{height: 18, width: `${w * 100}%`, background: '#00000018', borderRadius: 9, marginBottom: 22}} />
      ))}
      <div
        style={{
          position: 'absolute', bottom: 70, insetInlineEnd: 40, transform: 'rotate(-12deg)',
          border: `6px solid ${COLORS.danger}`, color: COLORS.danger, borderRadius: 14, padding: '6px 22px',
          fontWeight: 900, fontSize: ar ? 44 : 38, letterSpacing: ar ? 0 : 2, opacity: 0.85, whiteSpace: 'nowrap',
        }}
      >
        {c.paper.stamp}
      </div>
    </div>
  );
};

export const Hook: React.FC = () => {
  const f = useCurrentFrame();
  const c = useCopy();
  const {square} = useFormat();
  const drop = pop(f, 6, 13, 160);
  const shake = f > 30 && f < TEAR_AT ? Math.sin(f * 2.2) * (f - 30) * 0.35 : 0;
  const t = Math.max(0, f - TEAR_AT);
  const tear = lin(f, TEAR_AT, TEAR_AT + 30, 0, 1, (x) => x * x);
  const paperScale = square ? 0.72 : 1;
  const paperTop = square ? 330 : 860;

  const half = (side: -1 | 1, clip: string) => (
    <div
      style={{
        position: 'absolute', inset: 0, clipPath: clip,
        transform: `translate(${side * (t * 9 + tear * 60) * (square ? 0.35 : 1)}px, ${tear * 700}px) rotate(${side * tear * 28}deg)`,
        transformOrigin: side < 0 ? '50% 100%' : '50% 100%',
      }}
    >
      <Paper />
    </div>
  );

  const flash = interpolate(f, [TEAR_AT, TEAR_AT + 3, TEAR_AT + 10], [0, 0.5, 0], clamp);

  return (
    <SceneShell duration={SCENES.hook.duration} enter="none">
      <AbsoluteFill>
        <div
          style={{
            position: 'absolute', zIndex: 2, textAlign: square ? 'start' : 'center',
            ...(square ? {insetInlineStart: 70, width: 470, top: 0, bottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center'} : {left: 50, right: 50, top: 190}),
          }}
        >
          <Headline size={square ? (c.dir === 'rtl' ? 64 : 76) : 104}>
            {c.hook.lines.map((l, i) => (
              <SlamLine key={i} delay={i * 5} color={i === c.hook.highlight ? COLORS.secondary : undefined}>
                {i === c.hook.highlight ? (
                  <span style={{position: 'relative', display: 'inline-block'}}>
                    {l}
                    <span style={{position: 'absolute', left: 0, right: 0, bottom: '12%', height: 8, background: COLORS.secondary, transformOrigin: c.dir === 'rtl' ? 'right' : 'left', transform: `scaleX(${lin(f, 14, 26)})`, borderRadius: 4}} />
                  </span>
                ) : (
                  l
                )}
              </SlamLine>
            ))}
          </Headline>
        </div>
        <div
          style={{
            position: 'absolute', width: 600, height: 760,
            ...(square ? {insetInlineEnd: 40, top: paperTop - 230} : {left: 240, top: paperTop}),
            transform: `translateY(${(1 - drop) * -900}px) rotate(${(1 - drop) * -14 + 3 + shake * 0.3}deg) translateX(${shake}px) scale(${paperScale})`,
          }}
        >
          {f < TEAR_AT ? <Paper /> : (<>{half(-1, LEFT_CLIP)}{half(1, RIGHT_CLIP)}</>)}
        </div>
        <AbsoluteFill style={{background: COLORS.secondary, opacity: flash, mixBlendMode: 'screen'}} />
      </AbsoluteFill>
    </SceneShell>
  );
};
