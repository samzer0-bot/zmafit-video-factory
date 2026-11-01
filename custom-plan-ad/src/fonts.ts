import {continueRender, delayRender, staticFile} from 'remotion';

const ARABIC =
  'U+0600-06FF, U+0750-077F, U+0870-088E, U+0890-0891, U+0897-08E1, U+08E3-08FF, U+200C-200E, U+2010-2011, U+204F, U+2E41, U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC';
const LATIN =
  'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD';

const faces: {family: string; file: string; weight: number; range: string}[] = [
  ...[600, 700, 800, 900].map((w) => ({family: 'Montserrat', file: `fonts/montserrat-latin-${w}-normal.woff2`, weight: w, range: LATIN})),
  ...[500, 700, 800, 900].flatMap((w) => [
    {family: 'Cairo', file: `fonts/cairo-arabic-${w}-normal.woff2`, weight: w, range: ARABIC},
    {family: 'Cairo', file: `fonts/cairo-latin-${w}-normal.woff2`, weight: w, range: LATIN},
  ]),
];

let started = false;
export const loadFonts = () => {
  if (started || typeof document === 'undefined') return;
  started = true;
  const handle = delayRender('Loading fonts');
  Promise.all(
    faces.map((f) =>
      new FontFace(f.family, `url(${staticFile(f.file)}) format('woff2')`, {weight: String(f.weight), unicodeRange: f.range})
        .load()
        .then((loaded) => document.fonts.add(loaded)),
    ),
  )
    .then(() => continueRender(handle))
    .catch((e) => {
      console.error(e);
      continueRender(handle);
    });
};
