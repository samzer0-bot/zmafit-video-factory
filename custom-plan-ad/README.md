# إعلان "Custom 4-Week Fat-Loss Plan" — Remotion

فيديو إعلاني قصير (25 ثانية، 30 إطار/ث) لمنتج ZmaFit على https://zmafit.com/custom-plan

## المخرجات (`out/`)
| الملف | المقاس | اللغة |
|---|---|---|
| `custom-plan-vertical-en.mp4` | 1080×1920 (TikTok / Reels / Shorts) | English |
| `custom-plan-square-en.mp4` | 1080×1080 (Facebook) | English |
| `custom-plan-vertical-ar.mp4` | 1080×1920 | العربية (RTL، خط Cairo) |
| `custom-plan-square-ar.mp4` | 1080×1080 | العربية (نسخة إضافية) |
| `thumbnail-*.png` | صور مصغّرة من إطار الخطة (كل البطاقات ظاهرة) | |

## التعديل
- **كل النصوص والألوان والسعر والرابط وتوقيت المشاهد** موجودة في `src/config.ts`.
- كل مشهد في ملف مستقل داخل `src/scenes/`:
  `Hook` → `Questions` → `Building` → `Plan` → `Pdf` → `Price` → `Cta`.
- مكوّنات مشتركة في `src/components/` (إطار الهاتف، الأيقونات، الشعار، الخلفية، شعارات الدفع).

## الصوت
لا توجد موسيقى افتراضياً. ضع ملف `audio.mp3` (خالٍ من الحقوق) في هذا المجلد أو في جذر المستودع
وأعد التصدير، وسيُضاف تلقائياً مع تلاشٍ في آخر نصف ثانية.

## التشغيل
```bash
npm install
npm run studio          # معاينة وتعديل في المتصفح
node render.mjs         # تصدير كل الفيديوهات + الصور المصغّرة
node render.mjs --stills          # إطارات مراجعة من كل مشهد في out/review/
node render.mjs --only=vertical-en  # تصدير نسخة واحدة
```
الخطوط (Montserrat ExtraBold وCairo، رخصة OFL) مضمّنة محلياً في `public/fonts/`.
يستخدم السكربت Chrome Headless Shell من `/opt/pw-browsers`، ويمكن تغييره بالمتغير `REMOTION_BROWSER`.
