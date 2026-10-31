import React from 'react';
import {AbsoluteFill, Audio, Img, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, lin, pop} from '../anim';
import {COLORS} from '../config';
import {Background} from '../components/Background';
import {Arrow} from '../components/Icons';
import {Headline, SceneShell, SlamLine} from '../components/Layout';
import {Logo} from '../components/Logo';
import {loadFonts} from '../fonts';
import {LangProvider, useFormat} from '../i18n';
import {GUIDE} from './copy';
import TL from './timeline.json';

loadFonts();

type Key = keyof typeof TL.scenes;
const SC = TL.scenes;
const BT = TL.beats;
const A4 = 1.414;

export type GuideProps = {hook: number; hasAudio: boolean; voice: boolean};

/* ---------- pieces ---------- */

const Book: React.FC<{width: number; rotY: number; rotZ?: number; glow?: number}> = ({width, rotY, rotZ = 0, glow = 0.5}) => (
  <div style={{perspective: 2400, width, height: width * A4}}>
    <div
      style={{
        width, height: width * A4, position: 'relative', transformStyle: 'preserve-3d',
        transform: `rotateY(${rotY}deg) rotateZ(${rotZ}deg)`,
        boxShadow: `0 40px 90px rgba(0,0,0,0.6), 0 0 120px rgba(34,229,132,${glow * 0.5})`, borderRadius: 10,
      }}
    >
      <Img src={staticFile('guide/page-01.png')} style={{width: '100%', height: '100%', borderRadius: 10, display: 'block'}} />
      {/* spine + page edges */}
      <div style={{position: 'absolute', left: 0, top: 0, bottom: 0, width: width * 0.04, borderRadius: '10px 0 0 10px', background: 'linear-gradient(90deg, rgba(0,0,0,0.55), rgba(255,255,255,0.08), rgba(0,0,0,0))'}} />
      <div style={{position: 'absolute', right: -10, top: 8, bottom: 8, width: 12, borderRadius: '0 6px 6px 0', background: 'repeating-linear-gradient(0deg, #f2f2ee 0 3px, #d9d9d2 3px 4px)'}} />
    </div>
  </div>
);

const FreeBurst: React.FC<{size: number; scale: number}> = ({size, scale}) => {
  const f = useCurrentFrame();
  const pts = Array.from({length: 24}, (_, i) => {
    const r = i % 2 ? size * 0.42 : size * 0.5;
    const a = (i / 24) * Math.PI * 2;
    return `${size / 2 + r * Math.cos(a)},${size / 2 + r * Math.sin(a)}`;
  }).join(' ');
  return (
    <div style={{width: size, height: size, position: 'relative', transform: `scale(${scale}) rotate(${-12 + Math.sin(f / 8) * 4}deg)`}}>
      <svg width={size} height={size} style={{position: 'absolute', inset: 0, filter: `drop-shadow(0 10px 30px ${COLORS.secondary}99)`}}>
        <polygon points={pts} fill={COLORS.secondary} />
      </svg>
      <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Montserrat', fontWeight: 900, fontSize: size * 0.26, color: COLORS.white, letterSpacing: -1}}>FREE</div>
    </div>
  );
};

/* ---------- scenes ---------- */

const NOISE_POS = [
  [0.1, 0.42, -10], [0.56, 0.46, 8], [0.16, 0.57, 6], [0.58, 0.61, -7], [0.08, 0.72, -4], [0.5, 0.76, 9],
];

const Hook: React.FC<{variant: number}> = ({variant}) => {
  const f = useCurrentFrame();
  const {square, bleed} = useFormat();
  const hook = GUIDE.hooks[Math.min(variant, GUIDE.hooks.length - 1)];
  const strike = lin(f, BT.strikeAt, BT.strikeAt + 8);
  const away = lin(f, BT.strikeAt + 12, BT.strikeAt + 26, 0, 1, (x) => x * x);
  const H = square ? 1080 : 1920;
  const flash = interpolate(f, [BT.strikeAt, BT.strikeAt + 3, BT.strikeAt + 10], [0, 0.35, 0], clamp);
  return (
    <SceneShell duration={SC.hook.duration} enter="none">
      <AbsoluteFill>
        <div style={{position: 'absolute', left: 60, right: 60, top: square ? 90 : 200, textAlign: 'center', zIndex: 2}}>
          <Headline size={square ? 82 : 100}>
            {hook.lines.map((l, i) => (
              <SlamLine key={i} delay={-9 + i * 2} color={i === hook.highlight ? COLORS.primary : undefined}>{l}</SlamLine>
            ))}
          </Headline>
        </div>
        {GUIDE.noise.map((n, i) => {
          const [x, y, r] = NOISE_POS[i];
          const p = pop(f, -6 + i * 3, 12, 200);
          const top = square ? 430 + (y - 0.42) * 1500 : y * H;
          return (
            <div
              key={n}
              style={{
                position: 'absolute', left: x * 1080 + (square ? 40 : 0), top, transform: `rotate(${r}deg) scale(${p * (1 - away * 0.4)}) translateY(${away * 600}px)`,
                opacity: 1 - away, fontFamily: 'Montserrat', fontWeight: 900, fontSize: square ? 42 : 50, color: COLORS.white,
                background: COLORS.card, border: `3px solid ${COLORS.cardBorder}`, borderRadius: 18, padding: '14px 28px', whiteSpace: 'nowrap',
              }}
            >
              {n}
              <div style={{position: 'absolute', left: 14, right: 14, top: '50%', height: 8, marginTop: -4, background: COLORS.danger, borderRadius: 4, transform: `scaleX(${strike})`, transformOrigin: 'left'}} />
            </div>
          );
        })}
        <AbsoluteFill style={{background: COLORS.danger, opacity: flash, mixBlendMode: 'screen', top: -bleed, bottom: -bleed, height: 'auto'}} />
      </AbsoluteFill>
    </SceneShell>
  );
};

const Reveal: React.FC = () => {
  const f = useCurrentFrame();
  const {square} = useFormat();
  const book = pop(f, 0, 11, 120);
  const burst = pop(f, BT.bookLand, 8, 200);
  const W = square ? 420 : 640;
  const rotY = interpolate(book, [0, 1], [70, -14]) + Math.sin(f / 18) * 3;
  return (
    <SceneShell duration={SC.reveal.duration}>
      <AbsoluteFill style={{display: 'flex', flexDirection: square ? 'row' : 'column', alignItems: 'center', justifyContent: 'center', gap: square ? 60 : 70}}>
        <div style={{textAlign: square ? 'start' : 'center', order: square ? 2 : 0, width: square ? 440 : undefined}}>
          <div style={{display: 'inline-block', fontFamily: 'Montserrat', fontWeight: 900, fontSize: 38, letterSpacing: 4, color: COLORS.bg, background: COLORS.primary, borderRadius: 40, padding: '10px 30px', marginBottom: 24, transform: `scale(${pop(f, 2, 12, 200)})`}}>
            {GUIDE.reveal.badge}
          </div>
          <Headline size={square ? 76 : 96}>
            <SlamLine delay={4}>{GUIDE.reveal.headline[0]}</SlamLine>
            <SlamLine delay={8} color={COLORS.primary}>{GUIDE.reveal.headline[1]}</SlamLine>
          </Headline>
        </div>
        <div style={{position: 'relative', transform: `translateY(${(1 - book) * 300}px) scale(${0.6 + 0.4 * book})`, opacity: Math.min(1, book * 2)}}>
          <Book width={W} rotY={rotY} glow={0.4 + 0.3 * burst} />
          <div style={{position: 'absolute', ...(square ? {left: -W * 0.14, top: -W * 0.12} : {right: -W * 0.2, top: W * 0.1})}}>
            <FreeBurst size={W * 0.42} scale={burst} />
          </div>
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};

const Inside: React.FC = () => {
  const f = useCurrentFrame();
  const {square} = useFormat();
  const pages = GUIDE.inside.pages;
  const W = square ? 430 : 600;
  const idx = Math.max(0, Math.min(pages.length - 1, Math.floor((f - BT.pageFirst) / BT.pageGap)));
  return (
    <SceneShell duration={SC.inside.duration}>
      <AbsoluteFill>
        <div style={{position: 'absolute', top: square ? 60 : 170, left: 0, right: 0, textAlign: 'center'}}>
          <Headline size={square ? 72 : 96}><SlamLine delay={0}>{GUIDE.inside.headline}</SlamLine></Headline>
        </div>
        <div style={{position: 'absolute', left: '50%', top: square ? 190 : 380, width: W, height: W * A4, marginLeft: square ? -W / 2 - 220 : -W / 2}}>
          {pages.map((p, i) => {
            const at = BT.pageFirst + i * BT.pageGap;
            const inP = pop(f, at, 13, 170);
            const behind = Math.max(0, idx - i); // how many pages are on top of this one
            const settle = lin(f, at + BT.pageGap, at + BT.pageGap + 10) * (i < idx ? 1 : 0);
            return (
              <div
                key={p.file}
                style={{
                  position: 'absolute', inset: 0, opacity: Math.min(1, inP * 1.5),
                  transform: `translateX(${(1 - inP) * 700 - settle * (40 + behind * 26)}px) rotate(${(1 - inP) * 14 - settle * (4 + behind * 2.5)}deg) scale(${1 - settle * 0.06 * behind})`,
                  boxShadow: '0 30px 70px rgba(0,0,0,0.55)', borderRadius: 10, overflow: 'hidden', zIndex: i,
                }}
              >
                <Img src={staticFile(p.file)} style={{width: '100%', height: '100%', display: 'block'}} />
              </div>
            );
          })}
        </div>
        {/* label for the current page */}
        <div
          style={{
            position: 'absolute', ...(square ? {left: 640, width: 400, top: 0, bottom: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 22} : {left: 60, right: 60, top: 380 + W * A4 + 60, display: 'flex', justifyContent: 'center'}),
          }}
        >
          {square
            ? pages.map((p, i) => {
                const on = f >= BT.pageFirst + i * BT.pageGap;
                return (
                  <div key={p.label} style={{fontWeight: 800, fontSize: 34, padding: '14px 22px', borderRadius: 20, background: on ? `${COLORS.primary}22` : COLORS.card, border: `3px solid ${on ? COLORS.primary : COLORS.cardBorder}`, color: on ? COLORS.white : COLORS.muted, transform: `scale(${i === idx ? 1.04 : 1})`}}>
                    {p.label}
                  </div>
                );
              })
            : (
              <div key={idx} style={{fontWeight: 800, fontSize: 52, color: COLORS.bg, background: COLORS.primary, borderRadius: 50, padding: '16px 44px', transform: `scale(${pop(f, BT.pageFirst + idx * BT.pageGap + 4, 12, 200)})`, whiteSpace: 'nowrap', boxShadow: `0 0 50px ${COLORS.primary}77`}}>
                {pages[idx].label}
              </div>
            )}
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};

const Cta: React.FC = () => {
  const f = useCurrentFrame();
  const {square} = useFormat();
  const typed = GUIDE.cta.email.slice(0, Math.max(0, Math.floor((f - BT.typeStart) / 1.6)));
  const caret = Math.floor(f / 8) % 2 === 0;
  const btn = pop(f, BT.typeStart + 18, 10, 200);
  const beat = (f % 15) / 15;
  const pulse = 1 + 0.04 * Math.exp(-beat * 6);
  const bounce = Math.abs(Math.sin(f / 6)) * 22;
  const S = square ? 0.72 : 1.14;
  return (
    <SceneShell duration={SC.cta.duration} exit="none">
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{transform: `scale(${S})`, display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: square ? -30 : -120}}>
          <div style={{opacity: pop(f, 0), marginBottom: 60}}><Logo size={90} /></div>
          <Headline size={square ? 100 : 86} style={{textAlign: 'center', marginBottom: 60}}>
            <SlamLine delay={2}>{GUIDE.cta.headline[0]}</SlamLine>
            <SlamLine delay={6} color={COLORS.primary}>{GUIDE.cta.headline[1]}</SlamLine>
          </Headline>
          <div style={{width: 820, height: 128, borderRadius: 30, background: '#fff', display: 'flex', alignItems: 'center', padding: '0 40px', boxSizing: 'border-box', fontFamily: 'Montserrat', fontWeight: 600, fontSize: 48, color: '#1A2330', opacity: pop(f, 10), boxShadow: '0 20px 60px rgba(0,0,0,0.5)'}}>
            <span style={{color: typed ? '#1A2330' : '#9AA5B1'}}>{typed || 'Your email'}</span>
            <span style={{width: 4, height: 56, background: COLORS.bg, marginLeft: 4, opacity: caret ? 1 : 0}} />
          </div>
          <div
            style={{
              marginTop: 36, width: 820, height: 140, borderRadius: 999, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 22,
              background: `linear-gradient(135deg, ${COLORS.primary}, #12C46C)`, color: COLORS.bg, fontWeight: 900, fontSize: 60, textTransform: 'uppercase',
              boxShadow: `0 0 ${70 * pulse}px ${COLORS.primary}AA, 0 14px 0 #0E8F4F`, transform: `scale(${(0.5 + 0.5 * btn) * pulse})`, opacity: Math.min(1, btn * 1.5), letterSpacing: -1,
            }}
          >
            {GUIDE.cta.button}
            <Arrow size={64} color={COLORS.bg} stroke={3.4} />
          </div>
          <div style={{marginTop: 70, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, opacity: btn, transform: `translateY(${bounce}px)`}}>
            <span style={{fontWeight: 800, fontSize: 44, color: COLORS.white}}>{GUIDE.cta.tap}</span>
            <svg width={70} height={70} viewBox="0 0 24 24"><path d="M12 4v15M5 12l7 7 7-7" stroke={COLORS.primary} strokeWidth={3} fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </div>
        </div>
        <div style={{position: 'absolute', left: 60, right: 60, bottom: square ? 30 : 170, textAlign: 'center', fontWeight: 600, fontSize: square ? 24 : 30, color: '#B4BFCC'}}>
          {GUIDE.cta.disclaimer}
        </div>
      </AbsoluteFill>
    </SceneShell>
  );
};

/* ---------- composition ---------- */

const S = (k: Key) => ({from: SC[k].from, durationInFrames: SC[k].duration, name: k});

export const GuideAd: React.FC<GuideProps> = ({hook, hasAudio, voice}) => {
  const f = useCurrentFrame();
  const {height} = useVideoConfig();
  const portrait = height === 1350;
  const fadeOut = interpolate(f, [TL.total - 12, TL.total], [1, 0], clamp);
  const scenes = (
    <>
      <Sequence {...S('hook')}><Hook variant={hook} /></Sequence>
      <Sequence {...S('reveal')}><Reveal /></Sequence>
      <Sequence {...S('inside')}><Inside /></Sequence>
      <Sequence {...S('cta')}><Cta /></Sequence>
    </>
  );
  return (
    <LangProvider lang="en">
      <AbsoluteFill style={{fontFamily: 'Montserrat', color: COLORS.white}}>
        <Background />
        {portrait ? (
          <>
            <div style={{position: 'absolute', left: 0, top: 135, width: 1080, height: 1080}}>{scenes}</div>
            <div style={{position: 'absolute', top: 40, left: 0, right: 0, display: 'flex', justifyContent: 'center', opacity: interpolate(f, [SC.cta.from - 6, SC.cta.from], [1, 0], clamp)}}><Logo size={56} /></div>
          </>
        ) : (
          scenes
        )}
        {hasAudio && <Audio src={staticFile('audio-guide.mp3')} volume={(fr) => Math.min(1, fr / 6) * fadeOut * (voice ? 0.38 : 1)} />}
        {voice &&
          (Object.keys(TL.vo) as Key[]).map((k) => (
            <Sequence key={k} from={SC[k].from + TL.vo[k]} name={`VO ${k}`}>
              <Audio src={staticFile(`vo/guide/${k === 'hook' ? `hook${hook}` : k}.mp3`)} />
            </Sequence>
          ))}
      </AbsoluteFill>
    </LangProvider>
  );
};

export const GUIDE_TOTAL = TL.total;
