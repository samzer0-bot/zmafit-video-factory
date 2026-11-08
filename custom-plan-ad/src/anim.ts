import {Easing, interpolate, spring} from 'remotion';
import {FPS} from './config';

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const pop = (frame: number, delay = 0, damping = 12, stiffness = 180) =>
  spring({frame: frame - delay, fps: FPS, config: {damping, stiffness, mass: 0.6}});

export const lin = (frame: number, a: number, b: number, from = 0, to = 1, ease = Easing.out(Easing.cubic)) =>
  interpolate(frame, [a, b], [from, to], {...clamp, easing: ease});

export const fmt = (n: number) => Math.round(n).toLocaleString('en-US');
