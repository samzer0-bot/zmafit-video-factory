import React from 'react';
import {Composition} from 'remotion';
import {Ad, AdProps} from './Ad';
import {FPS, TOTAL_FRAMES} from './config';

const formats = [
  {id: 'vertical', width: 1080, height: 1920},
  {id: 'square', width: 1080, height: 1080},
];

export const RemotionRoot: React.FC = () => (
  <>
    {formats.flatMap((fm) =>
      (['en', 'ar'] as const).map((lang) => (
        <Composition<any, AdProps>
          key={`${fm.id}-${lang}`}
          id={`custom-plan-${fm.id}-${lang}`}
          component={Ad}
          durationInFrames={TOTAL_FRAMES}
          fps={FPS}
          width={fm.width}
          height={fm.height}
          defaultProps={{lang, hasAudio: false}}
        />
      )),
    )}
  </>
);
