import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {clamp} from './anim';
import {Lang, SCENES, TOTAL_FRAMES} from './config';
import {Background} from './components/Background';
import {loadFonts} from './fonts';
import {LangProvider} from './i18n';
import {Building} from './scenes/Building';
import {Cta} from './scenes/Cta';
import {Hook} from './scenes/Hook';
import {Pdf} from './scenes/Pdf';
import {Plan} from './scenes/Plan';
import {Price} from './scenes/Price';
import {Questions} from './scenes/Questions';

loadFonts();

export type AdProps = {lang: Lang; hasAudio: boolean};

export const Ad: React.FC<AdProps> = ({lang, hasAudio}) => {
  const f = useCurrentFrame();
  const fadeOut = interpolate(f, [TOTAL_FRAMES - 12, TOTAL_FRAMES], [1, 0], clamp);
  return (
    <LangProvider lang={lang}>
      <AbsoluteFill>
        <Background />
        <Sequence from={SCENES.hook.from} durationInFrames={SCENES.hook.duration} name="1 Hook"><Hook /></Sequence>
        <Sequence from={SCENES.questions.from} durationInFrames={SCENES.questions.duration} name="2 Questions"><Questions /></Sequence>
        <Sequence from={SCENES.building.from} durationInFrames={SCENES.building.duration} name="3 Building"><Building /></Sequence>
        <Sequence from={SCENES.plan.from} durationInFrames={SCENES.plan.duration} name="4 Plan"><Plan /></Sequence>
        <Sequence from={SCENES.pdf.from} durationInFrames={SCENES.pdf.duration} name="5 PDF"><Pdf /></Sequence>
        <Sequence from={SCENES.price.from} durationInFrames={SCENES.price.duration} name="6 Price"><Price /></Sequence>
        <Sequence from={SCENES.cta.from} durationInFrames={SCENES.cta.duration} name="7 CTA"><Cta /></Sequence>
        {hasAudio && <Audio src={staticFile('audio.mp3')} volume={(fr) => Math.min(1, fr / 10) * fadeOut} />}
      </AbsoluteFill>
    </LangProvider>
  );
};
