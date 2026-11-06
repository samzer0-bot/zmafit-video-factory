# خطة التسويق والبيع — ZMAFIT

## مسار العميل (القمع)
فيديو (يوتيوب / فيسبوك / إنستغرام / تيك توك)
→ رابط الهدية المجانية في أول سطر من الوصف وفي التعليق المثبت
→ نموذج MailerLite «ZmaFit – 30-Day Kickstart (video link)» يضيفه إلى مجموعة «Website subscribers – Free guide»
→ سلسلة «ZmaFit Welcome Series» (7 إيميلات في 15 يوماً)
→ بيع الخطة المخصصة بـ 19$ على zmafit.com/custom-plan (سيناريو Make «مولّد الخطط المخصصة» يسلّمها آلياً)

## السلسلة البريدية (تعمل الآن)
| اليوم | الإيميل | الهدف |
|---|---|---|
| 0 | Your free guide is here | تسليم دليل 30 يوم (PDF) + أول خطوة |
| 2 | 3 mistakes that stall beginners | قيمة وبناء ثقة |
| 4 | A 15-minute workout you can do today | قيمة |
| 7 | Protein and calories, made simple | قيمة وتمهيد للخطة |
| 10 | Why generic plans don't work | **عرض الخطة 19$** |
| 12 | Your questions about the custom plan | **الرد على الاعتراضات** (جديد) |
| 15 | Where will you be in 4 weeks? | **آخر تذكير** (جديد) |

## الهدية المجانية
- `marketing/lead-magnet/ZmaFit-30-Day-Kickstart.pdf` (6 صفحات) — المصدر القابل للتعديل: `kickstart-en.html`
- آخر صفحة فيها دعوة لشراء الخطة المخصصة بروابط UTM لقياس المبيعات.

## ما تبقى عليك (10 دقائق)
1. **صمّم النموذج:** MailerLite ← Forms ← Embedded ← «ZmaFit – 30-Day Kickstart (video link)» ← اختر قالباً ← اكتب العنوان «Free 30-Day Home Fat-Loss Kickstart» ← Save. انسخ رابط **Share**.
2. **فعّل الرابط في الفيديوهات:** GitHub ← Settings ← Secrets and variables ← Actions ← Variables ← أضف `LEAD_MAGNET_URL_EN` = رابط المشاركة. من هذه اللحظة كل فيديو إنجليزي جديد يحمل الرابط أول سطر في الوصف.
3. **ضع نفس الرابط في البايو:** إنستغرام وتيك توك وبنترست ويوتيوب (روابط القناة).
4. **النشر التلقائي على إنستغرام وتيك توك:** Metricool ← Settings ← API ← انسخ التوكن ← GitHub Secrets ← `METRICOOL_TOKEN`. (يتطلب باقة Metricool فيها API؛ بدون التوكن الخطوة تُتخطى ولا يتأثر المصنع.)
5. **ادمج الفرع** `ccr-c3b7b005-d3myl8` في `main` (Merge عادي وليس Squash حتى يبقى رابط الـ PDF يعمل).

## القياس كل أسبوع
- MailerLite: عدد المشتركين الجدد، نسبة الفتح (>40%)، النقر على إيميل العرض.
- PayPal / Make: عدد الخطط المباعة. الهدف الأول: 2–3% من المشتركين يشترون.
- يوتيوب: النقرات على الرابط من الوصف.
- إذا كان التسجيل ضعيفاً: غيّر عنوان النموذج أولاً. إذا كان الشراء ضعيفاً: غيّر إيميل العرض.

## المرحلة التالية
- نسخة عربية من الهدية والسلسلة لقناة Muscle Arabia (`LEAD_MAGNET_URL_AR` جاهز في الكود).
- رفع الـ PDF إلى مكتبة وسائط ووردبريس كنسخة احتياطية للرابط.
