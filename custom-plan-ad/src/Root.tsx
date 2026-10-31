import React from 'react';
import {Composition} from 'remotion';
import {Ad, AdProps} from './Ad';
import {FPS, TOTAL_FRAMES} from './config';

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
  </>
);
