import React from 'react';
import {Composition} from 'remotion';
import {Ad, AdProps} from './Ad';
import {FPS, TOTAL_FRAMES} from './config';
import {GUIDE_TOTAL, GuideAd, GuideProps} from './guide/GuideAd';

export const FORMATS = [
  {id: 'vertical', width: 1080, height: 1920}, // TikTok / Reels / Shorts
  {id: 'portrait', width: 1080, height: 1350}, // 4:5 Instagram / Facebook feed
  {id: 'square', width: 1080, height: 1080}, //   1:1 Facebook
];

export const RemotionRoot: React.FC = () => (
  <>
    {FORMATS.flatMap((fm) =>
      (['en', 'ar'] as const).map((lang) => (
        <Composition<any, AdProps>
          key={`${fm.id}-${lang}`}
          id={`custom-plan-${fm.id}-${lang}`}
          component={Ad}
          durationInFrames={TOTAL_FRAMES}
          fps={FPS}
          width={fm.width}
          height={fm.height}
          defaultProps={{lang, hook: 0, hasAudio: false, voice: false}}
        />
      )),
    )}
    {/* Free-guide (lead magnet) ad — English only */}
    {FORMATS.map((fm) => (
      <Composition<any, GuideProps>
        key={`guide-${fm.id}`}
        id={`free-guide-${fm.id}-en`}
        component={GuideAd}
        durationInFrames={GUIDE_TOTAL}
        fps={FPS}
        width={fm.width}
        height={fm.height}
        defaultProps={{hook: 0, hasAudio: false, voice: false}}
      />
    ))}
  </>
);
