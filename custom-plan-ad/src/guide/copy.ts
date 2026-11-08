// All text for the free-guide (lead magnet) ad.
export const GUIDE = {
  title: '7-Day Fat-Loss Kickstart',
  hooks: [
    {lines: ["Don't know", 'where to start', 'with fat loss?'], highlight: 1},
    {lines: ['Keto? Fasting?', 'Endless cardio?', 'Start simpler.'], highlight: 2},
  ],
  noise: ['KETO', 'FASTING', 'NO CARBS', 'DETOX TEA', '2H CARDIO', 'JUICE CLEANSE'],
  reveal: {badge: 'FREE GUIDE', headline: ['Start strong', 'this week']},
  inside: {
    headline: "What's inside",
    pages: [
      {file: 'guide/page-03.png', label: 'Your calories & protein'},
      {file: 'guide/page-04.png', label: 'Simple meals + swaps'},
      {file: 'guide/page-05.png', label: 'Home or gym workouts'},
      {file: 'guide/page-07.png', label: '7-day checklist'},
    ],
  },
  cta: {
    headline: ['100% free.', 'Just your email.'],
    email: 'you@email.com',
    button: 'Send me the guide',
    tap: 'Tap below',
    disclaimer: 'General guidance, not medical advice. 18+.',
  },
};
