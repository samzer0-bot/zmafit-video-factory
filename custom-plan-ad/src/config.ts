// =====================================================================
//  ZmaFit — "Custom 4-Week Fat-Loss Plan" ad
//  Every text, color, price and timing lives in this one file.
// =====================================================================

export const COLORS = {
  bg: '#0B0F14',
  bg2: '#111821',
  card: '#151D27',
  cardBorder: '#223040',
  primary: '#22E584', // neon green
  secondary: '#FF7A1A', // orange
  white: '#FFFFFF',
  muted: '#8A97A8',
  paper: '#ECEAE2',
  paperInk: '#3A3F46',
  danger: '#FF4D4D',
};

export const PRODUCT = {
  price: 19,
  currency: '$',
  url: 'zmafit.com/custom-plan',
  brand: 'ZmaFit',
  questions: 12,
};

export const FPS = 30;

// Scene timeline in frames (30 fps). Total = 750 frames = 25 s.
export const SCENES = {
  hook: {from: 0, duration: 90}, //       0–3 s
  questions: {from: 90, duration: 120}, // 3–7 s
  building: {from: 210, duration: 60}, //  7–9 s
  plan: {from: 270, duration: 210}, //     9–16 s
  pdf: {from: 480, duration: 90}, //      16–19 s
  price: {from: 570, duration: 90}, //    19–22 s
  cta: {from: 660, duration: 90}, //      22–25 s
};
export const TOTAL_FRAMES = 750;

// Sample numbers shown inside the mock plan UI (clearly labelled "Sample").
export const SAMPLE = {
  calories: 2050,
  protein: 150,
};

export type Lang = 'en' | 'ar';

export type Question = {q: string; options: string[]; pick: number};

export type Copy = {
  dir: 'ltr' | 'rtl';
  font: string;
  uppercase: boolean;
  hook: {lines: string[]; highlight: number};
  paper: {title: string; sub: string; rows: string[]; stamp: string};
  questions: {pre: string; post: string; progress: (n: number) => string; items: Question[]; numbers: number[]};
  building: {title: string; done: string};
  plan: {
    headline: string;
    phoneTitle: string;
    sample: string;
    kcal: string;
    protein: string;
    cards: {calories: string; workouts: string; workoutsSub: string; meals: string; mealsSub: string; variations: string; easier: string; harder: string; habits: string};
    weeks: string[];
    habits: string[];
    week2: string;
  };
  pdf: {line1: string; line2: string; chip: string};
  price: {oneTime: string; noSub: string; payWith: string; card: string};
  cta: {button: string; disclaimer: string};
};

export const COPY: Record<Lang, Copy> = {
  en: {
    dir: 'ltr',
    font: 'Montserrat',
    uppercase: true,
    hook: {lines: ['Tired of', 'generic', 'fat-loss plans?'], highlight: 1},
    paper: {
      title: 'GENERIC PLAN',
      sub: 'One size fits all',
      rows: ['Eat less, move more', 'Same workout for everyone', 'Same meals for everyone'],
      stamp: 'COPY / PASTE',
    },
    questions: {
      pre: 'Answer ',
      post: ' questions',
      progress: (n) => `Question ${n} of 12`,
      numbers: [1, 3, 6, 9, 12],
      items: [
        {q: 'Your main goal?', options: ['Lose fat', 'Tone up', 'Get fitter'], pick: 0},
        {q: 'Fitness level?', options: ['Beginner', 'Intermediate', 'Advanced'], pick: 1},
        {q: 'Your equipment?', options: ['Bodyweight', 'Dumbbells', 'Gym'], pick: 1},
        {q: 'Time per workout?', options: ['20 min', '30 min', '45+ min'], pick: 1},
        {q: 'Eating style?', options: ['Halal', 'Vegetarian', 'Low-carb'], pick: 0},
      ],
    },
    building: {title: 'Building your plan…', done: 'Plan ready!'},
    plan: {
      headline: 'Your plan includes',
      phoneTitle: 'Your 4-Week Plan',
      sample: 'Sample',
      kcal: 'kcal',
      protein: 'g protein',
      cards: {
        calories: 'Daily calories & protein',
        workouts: '4-week workouts',
        workoutsSub: 'For your time & equipment',
        meals: 'Meal plan + grocery list',
        mealsSub: 'Sample day with swaps',
        variations: 'Easier / harder variations',
        easier: 'Easier',
        harder: 'Harder',
        habits: 'Daily habits checklist',
      },
      weeks: ['W1', 'W2', 'W3', 'W4'],
      habits: ['Sleep', 'Steps', 'Water'],
      week2: 'What to change after week 2',
    },
    pdf: {line1: 'Ready in minutes', line2: 'Save as PDF', chip: 'On screen in 1–3 min'},
    price: {oneTime: 'one-time', noSub: 'No subscription', payWith: 'Pay with', card: 'Card'},
    cta: {button: 'Build your plan', disclaimer: 'General guidance, not medical advice. 18+.'},
  },
  ar: {
    dir: 'rtl',
    font: 'Cairo',
    uppercase: false,
    hook: {lines: ['سئمت من خطط', 'خسارة الدهون', 'العامة؟'], highlight: 2},
    paper: {
      title: 'خطة عامة',
      sub: 'مقاس واحد للجميع',
      rows: ['كُل أقل وتحرّك أكثر', 'نفس التمارين للجميع', 'نفس الوجبات للجميع'],
      stamp: 'نسخ ولصق',
    },
    questions: {
      pre: 'أجب عن ',
      post: ' سؤالاً',
      progress: (n) => `السؤال ${n} من 12`,
      numbers: [1, 3, 6, 9, 12],
      items: [
        {q: 'ما هدفك الأساسي؟', options: ['خسارة الدهون', 'شدّ الجسم', 'لياقة أفضل'], pick: 0},
        {q: 'مستوى لياقتك؟', options: ['مبتدئ', 'متوسط', 'متقدم'], pick: 1},
        {q: 'ما المعدات المتاحة؟', options: ['وزن الجسم', 'دمبلز', 'جيم كامل'], pick: 1},
        {q: 'وقت التمرين المتاح؟', options: ['20 دقيقة', '30 دقيقة', '+45 دقيقة'], pick: 1},
        {q: 'نظام أكلك؟', options: ['حلال', 'نباتي', 'قليل الكربوهيدرات'], pick: 0},
      ],
    },
    building: {title: 'جارٍ بناء خطتك…', done: 'خطتك جاهزة!'},
    plan: {
      headline: 'خطتك تتضمن',
      phoneTitle: 'خطة الـ4 أسابيع',
      sample: 'نموذج',
      kcal: 'سعرة',
      protein: 'غ بروتين',
      cards: {
        calories: 'السعرات والبروتين اليومي',
        workouts: 'تمارين 4 أسابيع',
        workoutsSub: 'حسب وقتك ومعداتك',
        meals: 'خطة أكل + قائمة مشتريات',
        mealsSub: 'يوم أكل نموذجي مع بدائل',
        variations: 'نسخة أسهل وأصعب',
        easier: 'أسهل',
        harder: 'أصعب',
        habits: 'قائمة العادات اليومية',
      },
      weeks: ['1', '2', '3', '4'],
      habits: ['النوم', 'الخطوات', 'الماء'],
      week2: 'ماذا تغيّر بعد الأسبوع الثاني',
    },
    pdf: {line1: 'جاهزة خلال دقائق', line2: 'احفظها PDF', chip: 'تظهر على الشاشة خلال 1–3 دقائق'},
    price: {oneTime: 'دفعة واحدة', noSub: 'بدون اشتراك', payWith: 'ادفع عبر', card: 'البطاقة'},
    cta: {button: 'ابنِ خطتك الآن', disclaimer: 'إرشادات عامة وليست نصيحة طبية. للأعمار +18.'},
  },
};
