// Usage: node render.mjs            -> renders all MP4s + thumbnail into out/
//        node render.mjs --stills   -> renders review frames into out/review/
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const root = path.dirname(new URL(import.meta.url).pathname);
const out = path.join(root, 'out');
fs.mkdirSync(out, {recursive: true});

// Optional royalty-free soundtrack: put audio.mp3 next to this script (or in the repo root).
const audioCandidates = [path.join(root, 'audio.mp3'), path.join(root, '..', 'audio.mp3')];
const audio = audioCandidates.find((p) => fs.existsSync(p));
const publicAudio = path.join(root, 'public', 'audio.mp3');
if (audio) fs.copyFileSync(audio, publicAudio);
else if (fs.existsSync(publicAudio)) fs.rmSync(publicAudio);
const hasAudio = Boolean(audio);
console.log(hasAudio ? `Using audio: ${audio}` : 'No audio.mp3 found — rendering silent video.');

const browserExecutable =
  process.env.REMOTION_BROWSER ?? '/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell';
const chromiumOptions = {gl: 'swangle'};

const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts')});

const comp = async (id, lang) =>
  selectComposition({serveUrl, id, inputProps: {lang, hasAudio}, browserExecutable, chromiumOptions});

const stillsMode = process.argv.includes('--stills');
const only = process.argv.find((a) => a.startsWith('--only='))?.slice(7);

const jobs = [
  {id: 'custom-plan-vertical-en', lang: 'en', file: 'custom-plan-vertical-en.mp4'},
  {id: 'custom-plan-square-en', lang: 'en', file: 'custom-plan-square-en.mp4'},
  {id: 'custom-plan-vertical-ar', lang: 'ar', file: 'custom-plan-vertical-ar.mp4'},
  {id: 'custom-plan-square-ar', lang: 'ar', file: 'custom-plan-square-ar.mp4'},
].filter((j) => !only || j.id.includes(only));

if (stillsMode) {
  // two frames per scene + last frame
  const frames = [20, 70, 105, 175, 225, 252, 300, 460, 505, 560, 590, 650, 690, 749];
  const dir = path.join(out, 'review');
  fs.mkdirSync(dir, {recursive: true});
  for (const j of jobs) {
    const composition = await comp(j.id, j.lang);
    for (const frame of frames) {
      await renderStill({composition, serveUrl, frame, output: path.join(dir, `${j.id}-${String(frame).padStart(3, '0')}.png`), inputProps: {lang: j.lang, hasAudio}, browserExecutable, chromiumOptions});
    }
    console.log('stills done', j.id);
  }
} else {
  for (const j of jobs) {
    const composition = await comp(j.id, j.lang);
    await renderMedia({
      composition, serveUrl, codec: 'h264', crf: 18, pixelFormat: 'yuv420p',
      outputLocation: path.join(out, j.file), inputProps: {lang: j.lang, hasAudio}, browserExecutable, chromiumOptions,
      onProgress: ({progress}) => process.stdout.write(`\r${j.file} ${(progress * 100).toFixed(0)}%   `),
    });
    console.log('\n✔', j.file);
  }
  // Thumbnail: plan scene with every card visible + headline (strongest frame)
  for (const [id, lang] of [['custom-plan-vertical-en', 'en'], ['custom-plan-square-en', 'en'], ['custom-plan-vertical-ar', 'ar']]) {
    if (only && !id.includes(only)) continue;
    const composition = await comp(id, lang);
    await renderStill({composition, serveUrl, frame: 462, output: path.join(out, `thumbnail-${id.replace('custom-plan-', '')}.png`), inputProps: {lang, hasAudio}, browserExecutable, chromiumOptions});
  }
  console.log('✔ thumbnails');
}
