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
const guideMode = process.argv.includes('--guide');
const guideAudio = path.join(root, 'audio-guide.mp3');
if (fs.existsSync(guideAudio)) fs.copyFileSync(guideAudio, path.join(root, 'public', 'audio-guide.mp3'));
const hasAudio = guideMode ? fs.existsSync(guideAudio) : Boolean(audio);
console.log(hasAudio ? `Using audio: ${audio}` : 'No audio.mp3 found — rendering silent video.');

const browserExecutable =
  process.env.REMOTION_BROWSER ?? '/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell';
const chromiumOptions = {gl: 'swangle'};

const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.ts')});

const comp = async (id, props) => selectComposition({serveUrl, id, inputProps: props, browserExecutable, chromiumOptions});

const stillsMode = process.argv.includes('--stills');
const only = process.argv.find((a) => a.startsWith('--only='))?.slice(7);
const voice = !process.argv.includes('--no-voice');

// hook: index into COPY[lang].hooks (A/B variants exist for English)
const jobs = [
  {id: 'custom-plan-vertical-en', lang: 'en', hook: 0, file: 'custom-plan-vertical-en.mp4'},
  {id: 'custom-plan-vertical-en', lang: 'en', hook: 1, file: 'custom-plan-vertical-en-hook2.mp4'},
  {id: 'custom-plan-vertical-en', lang: 'en', hook: 2, file: 'custom-plan-vertical-en-hook3.mp4'},
  {id: 'custom-plan-vertical-en', lang: 'en', hook: 3, file: 'custom-plan-vertical-en-hook4.mp4'},
  {id: 'custom-plan-portrait-en', lang: 'en', hook: 0, file: 'custom-plan-portrait-en.mp4'},
  {id: 'custom-plan-square-en', lang: 'en', hook: 0, file: 'custom-plan-square-en.mp4'},
  {id: 'custom-plan-vertical-ar', lang: 'ar', hook: 0, file: 'custom-plan-vertical-ar.mp4'},
  {id: 'custom-plan-portrait-ar', lang: 'ar', hook: 0, file: 'custom-plan-portrait-ar.mp4'},
  {id: 'custom-plan-square-ar', lang: 'ar', hook: 0, file: 'custom-plan-square-ar.mp4'},
];
// Free-guide (lead magnet) ad:  node render.mjs --guide
const guideJobs = [
  {id: 'free-guide-vertical-en', hook: 0, file: 'free-guide-vertical-en.mp4'},
  {id: 'free-guide-vertical-en', hook: 1, file: 'free-guide-vertical-en-hook2.mp4'},
  {id: 'free-guide-portrait-en', hook: 0, file: 'free-guide-portrait-en.mp4'},
];
const selected = (guideMode ? guideJobs : jobs).filter((j) => !only || j.file.includes(only));
jobs.length = 0;
jobs.push(...selected);

const propsOf = (j) => (guideMode ? {hook: j.hook, hasAudio, voice} : {lang: j.lang, hook: j.hook, hasAudio, voice});

if (stillsMode) {
  // two frames per scene + last frame
  const frames = guideMode ? [5, 45, 100, 150, 200, 260, 320, 360, 420, 479] : [5, 60, 110, 160, 200, 230, 290, 330, 462, 500, 545, 600, 650, 700, 749];
  const dir = path.join(out, 'review');
  fs.mkdirSync(dir, {recursive: true});
  for (const j of jobs) {
    const composition = await comp(j.id, propsOf(j));
    const fr = j.hook > 0 ? [5, 40, 70] : frames;
    for (const frame of fr) {
      await renderStill({composition, serveUrl, frame, output: path.join(dir, `${j.file.replace('.mp4', '')}-${String(frame).padStart(3, '0')}.png`), inputProps: propsOf(j), browserExecutable, chromiumOptions});
    }
    console.log('stills done', j.file);
  }
} else {
  for (const j of jobs) {
    const composition = await comp(j.id, propsOf(j));
    await renderMedia({
      composition, serveUrl, codec: 'h264', crf: 18, pixelFormat: 'yuv420p', audioBitrate: '192k',
      outputLocation: path.join(out, j.file), inputProps: propsOf(j), browserExecutable, chromiumOptions,
      onProgress: ({progress}) => process.stdout.write(`\r${j.file} ${(progress * 100).toFixed(0)}%   `),
    });
    console.log('\n✔', j.file);
  }
  // Thumbnails: plan scene with every card visible + headline (strongest frame)
  for (const j of jobs.filter((x) => x.hook === 0 && !guideMode)) {
    const composition = await comp(j.id, propsOf(j));
    await renderStill({composition, serveUrl, frame: 462, output: path.join(out, `thumbnail-${j.file.replace('custom-plan-', '').replace('.mp4', '.png')}`), inputProps: propsOf(j), browserExecutable, chromiumOptions});
  }
  console.log('✔ thumbnails');
}
