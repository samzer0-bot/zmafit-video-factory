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
  const square = width === height;
  return {square, width, height};
};
