import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp} from './anim';
import {COLORS, Lang, PRODUCT, SceneKey, SCENES, TOTAL_FRAMES, VO_OFFSET} from './config';
import {Background} from './components/Background';
import {Logo} from './components/Logo';
import {loadFonts} from './fonts';
import {LangProvider} from './i18n';
import {Building} from './scenes/Building';
import {Cta} from './scenes/Cta';
import {Hook} from './scenes/Hook';
import {Pdf} from './scenes/Pdf';
import {Plan} from './scenes/Plan';
import {Price} from './scenes/Price';
import {Questions} from './scenes/Questions';
import {TwoPlans} from './scenes/TwoPlans';

loadFonts();

export type AdProps = {
  lang: Lang;
  /** hook variant index (see COPY[lang].hooks) */
  hook: number;
  hasAudio: boolean;
  /** play the voice-over clips from public/vo/<lang>/ */
  voice: boolean;
};

const S = (k: SceneKey) => ({from: SCENES[k].from, durationInFrames: SCENES[k].duration, name: k});

const VoiceOver: React.FC<{lang: Lang; hook: number}> = ({lang, hook}) => (
  <>
    {(Object.keys(VO_OFFSET) as SceneKey[]).map((k) => {
      const file = k === 'hook' ? `hook${lang === 'en' ? hook : 0}` : k;
      return (
        <Sequence key={k} from={SCENES[k].from + (VO_OFFSET[k] ?? 0)} name={`VO ${k}`}>
          <Audio src={staticFile(`vo/${lang}/${file}.mp3`)} volume={1} />
        </Sequence>
      );
    })}
  </>
);

/** 4:5 only: thin brand bands above and below the 1080x1080 stage */
const PortraitBands: React.FC = () => {
  const f = useCurrentFrame();
  const o = interpolate(f, [SCENES.cta.from - 6, SCENES.cta.from], [1, 0], clamp);
  return (
    <AbsoluteFill style={{opacity: o}}>
      <div style={{position: 'absolute', top: 40, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
        <Logo size={56} />
      </div>
      <div style={{position: 'absolute', bottom: 44, left: 0, right: 0, textAlign: 'center', fontFamily: 'Montserrat', fontWeight: 800, fontSize: 38, color: COLORS.white, direction: 'ltr'}}>
        {PRODUCT.url.split('/')[0]}
        <span style={{color: COLORS.primary}}>/{PRODUCT.url.split('/')[1]}</span>
      </div>
    </AbsoluteFill>
  );
};

export const Ad: React.FC<AdProps> = ({lang, hook, hasAudio, voice}) => {
  const f = useCurrentFrame();
  const {height} = useVideoConfig();
  const portrait = height === 1350;
  const fadeOut = interpolate(f, [TOTAL_FRAMES - 12, TOTAL_FRAMES], [1, 0], clamp);
  const musicLevel = voice ? 0.38 : 1; // duck the beat under the voice-over
  const scenes = (
    <>
      <Sequence {...S('hook')}><Hook variant={hook} /></Sequence>
      <Sequence {...S('questions')}><Questions /></Sequence>
      <Sequence {...S('building')}><Building /></Sequence>
      <Sequence {...S('twoPlans')}><TwoPlans /></Sequence>
      <Sequence {...S('plan')}><Plan /></Sequence>
      <Sequence {...S('pdf')}><Pdf /></Sequence>
      <Sequence {...S('price')}><Price /></Sequence>
      <Sequence {...S('cta')}><Cta /></Sequence>
    </>
  );
  return (
    <LangProvider lang={lang}>
      <AbsoluteFill>
        <Background />
        {portrait ? (
          <>
            <div style={{position: 'absolute', left: 0, top: 135, width: 1080, height: 1080}}>{scenes}</div>
            <PortraitBands />
          </>
        ) : (
          scenes
        )}
        {hasAudio && <Audio src={staticFile('audio.mp3')} volume={(fr) => Math.min(1, fr / 6) * fadeOut * musicLevel} />}
        {voice && <VoiceOver lang={lang} hook={hook} />}
      </AbsoluteFill>
    </LangProvider>
  );
};
