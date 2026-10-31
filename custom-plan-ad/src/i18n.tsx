import React, {createContext, useContext} from 'react';
import {useVideoConfig} from 'remotion';
import {COPY, Copy, Lang} from './config';

const LangCtx = createContext<Lang>('en');
export const LangProvider: React.FC<{lang: Lang; children: React.ReactNode}> = ({lang, children}) => (
  <LangCtx.Provider value={lang}>{children}</LangCtx.Provider>
);
export const useLang = () => useContext(LangCtx);
export const useCopy = (): Copy => COPY[useContext(LangCtx)];

/** Layout info: square (1:1) vs vertical (9:16) */
export const useFormat = () => {
  const {width, height} = useVideoConfig();
  const square = height <= 1350; // 1:1 and 4:5 share the compact layout (4:5 adds brand bands)
  // 4:5 renders the 1080x1080 stage centred; full-bleed effects extend by this much above/below
  const bleed = height === 1350 ? (1350 - 1080) / 2 : 0;
  return {square, width, height, bleed};
};
