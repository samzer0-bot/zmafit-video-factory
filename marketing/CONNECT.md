# دليل ربط المنصات — سيناريو «استراتيجية تسويق» (رقم 10119124)

افتح Make ← Scenarios ← «استراتيجية تسويق — نشر الفيديوهات القصيرة على 8 منصات». كل منصة لها وحدة (دائرة) خاصة بها: اضغط عليها ثم اتبع الخطوات أدناه.

> رابط العودة (Redirect URI) الذي تطلبه مواقع المطورين لأي اتصال OAuth 2.0 في Make:
> `https://www.integromat.com/oauth/cb/oauth2`

---

## 0. رابط الهدية (أول شيء)
1. اضغط الوحدة الأولى **Set variables**.
2. في `lead_url` الصق رابط نموذج MailerLite.
3. اضغط OK ثم Save (أيقونة القرص أسفل الشاشة).

## 1. فيسبوك وBluesky — مربوطان، لا شيء مطلوب

## 2. بنترست — إعادة ربط (دقيقة)
1. Make ← القائمة اليسرى **Connections**.
2. ابحث عن **zmafit** (Pinterest) ← **Reauthorize** ← سجّل الدخول ← Allow.
3. هذا يصلح أيضاً سيناريو «Daily Pinterest Auto-Pin» الحالي.

## 3. إنستغرام (5 دقائق)
**الشروط:** حساب إنستغرام zmafit يجب أن يكون **احترافياً** (Business أو Creator) ومربوطاً بصفحة فيسبوك ZMAFIT.
1. في تطبيق إنستغرام: الإعدادات ← نوع الحساب ← التبديل إلى حساب احترافي.
2. في صفحة فيسبوك ZMAFIT: الإعدادات ← الحسابات المرتبطة ← إنستغرام ← ربط.
3. في Make: اضغط وحدة **Instagram** ← Add ← سجّل الدخول بحساب فيسبوك الذي يدير الصفحة ← اختر الصفحة وحساب إنستغرام ← وافق على كل الصلاحيات.
4. في حقل **Page** اختر ZMAFIT ← OK ← Save.

## 4. تيك توك (20–30 دقيقة، أصعب واحد)
**أ) إنشاء التطبيق**
1. ادخل developers.tiktok.com وسجّل بحساب تيك توك zmafit.
2. Manage apps ← **Connect an app** ← اسم: ZMAFIT Publisher.
3. أضف المنتجين **Login Kit** و **Content Posting API**.
4. Scopes: فعّل `user.info.basic` و `video.upload`.
5. في Login Kit ← Redirect URI: `https://www.integromat.com/oauth/cb/oauth2`
6. انسخ **Client key** و **Client secret**.
7. التطبيق يبدأ في وضع **Sandbox**: أضف حسابك zmafit في Sandbox ← Target users. هذا يكفي للنشر على حسابك أنت. (المراجعة الكاملة من تيك توك ليست ضرورية لحسابك الخاص.)

**ب) الربط في Make**
1. اضغط وحدة تيك توك الوسطى (**Make an OAuth 2.0 request**) ← Add.
2. Flow type: **Authorization Code**.
3. Authorize URI: `https://www.tiktok.com/v2/auth/authorize/`
4. Token URI: `https://open.tiktokapis.com/v2/oauth/token/`
5. Scope: `user.info.basic,video.upload` (Scope separator: comma).
6. Client ID و Client Secret: الصق المفتاحين.
7. فعّل **Show advanced settings**، وأضف:
   - في **Authorize parameters**: `client_key` = Client key
   - في **Access token parameters**: `client_key` = Client key و `client_secret` = Client secret
8. Continue ← سجّل بتيك توك ← Authorize.

**ج) النتيجة:** كل فيديو يصل إلى **صندوق الوارد في تطبيق تيك توك** كمسودة. افتح الإشعار، أضف صوتاً رائجاً، وانشر.

## 5. X (تويتر) (15–20 دقيقة)
> **قبل البدء:** تأكد في developer.x.com من الباقة المجانية الحالية وحد النشر الشهري، لأن X يغيّر الأسعار باستمرار.
1. developer.x.com ← سجّل بحساب X الخاص بـ zmafit ← Projects & Apps ← أنشئ App.
2. User authentication settings ← Set up:
   - App permissions: **Read and write**
   - Type of App: **Web App (Confidential client)**
   - Callback URI: `https://www.integromat.com/oauth/cb/oauth2`
   - Website URL: `https://zmafit.com`
3. انسخ **OAuth 2.0 Client ID** و **Client Secret**.
4. في Make: اضغط وحدة X (**Make an OAuth 2.0 request**) ← Add:
   - Flow type: Authorization Code
   - Authorize URI: `https://x.com/i/oauth2/authorize`
   - Token URI: `https://api.x.com/2/oauth2/token`
   - Scope: `tweet.read tweet.write users.read offline.access` (Scope separator: space)
   - Client ID و Client Secret
   - في الإعدادات المتقدمة: فعّل **PKCE** إن ظهر الخيار (X يشترطه)، واختر إرسال بيانات العميل كـ **Basic authorization header**.
5. Continue ← Authorize app.
> إذا لم يظهر خيار PKCE في Make فلن يقبل X الربط. في هذه الحالة انشر على X يدوياً أو اترك الفرع، ولن يتأثر الباقي.

## 6. Threads (15 دقيقة، الرمز يُجدَّد كل 60 يوماً)
1. developers.facebook.com ← My Apps ← Create app ← اختر حالة الاستخدام **Access the Threads API**.
2. Use cases ← Threads API ← Customize ← فعّل `threads_basic` و `threads_content_publish`.
3. App roles ← Roles ← أضف حساب Threads الخاص بـ zmafit كـ **Threads Tester**.
4. في تطبيق Threads: الإعدادات ← الحساب ← أذونات المواقع (Website permissions) ← الدعوات ← **قبول**.
5. في لوحة التطبيق: Threads API ← **User Token Generator** ← Generate access token ← انسخه (صالح ساعة).
6. حوّله لرمز طويل الأمد (60 يوماً) بفتح هذا الرابط في المتصفح بعد استبدال القيم:
   `https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=APP_SECRET&access_token=SHORT_TOKEN`
   (APP_SECRET من App settings ← Basic). انسخ `access_token` من النتيجة.
7. الصقه في `threads_token` في وحدة Set variables ← Save.
8. **التجديد كل 50 يوماً تقريباً:** افتح
   `https://graph.threads.net/refresh_access_token?grant_type=th_refresh_token&access_token=CURRENT_TOKEN`
   والصق الرمز الجديد. (التحليل الأسبوعي سيذكّرك.)

## 7. Medium — على الأغلب غير ممكن
Medium أوقف إصدار مفاتيح API للتطبيقات الجديدة. جرّب: اضغط وحدة Medium ← Add؛ إن طلب Client ID/Secret لا تملكهما فاتركها. الفرع سيُتخطى دون أن يوقف الباقي.
البديل اليدوي المجاني: Medium ← Import a story ← الصق رابط مقال من zmafit.com (مرة أسبوعياً).

## 8. Quora — يدوي فقط (لا توجد واجهة نشر)
إجابتان أسبوعياً على أسئلة مثل «how to lose belly fat at home»، مع رابط الهدية في آخر الإجابة.

---

## الاختبار ثم التفعيل
1. بعد الربط اضغط **Run once** أسفل السيناريو.
2. افتح نتيجة كل وحدة: الأخضر نجح، والأحمر يعرض سبب الخطأ.
3. ملاحظة: السيناريو ينشر فقط الفيديوهات الإنجليزية القصيرة من **آخر 12 ساعة**، فشغّله بعد إنتاج المصنع لفيديو جديد (بعد 14:19 أو 21:27 بتوقيت UTC بنصف ساعة).
4. إذا كان كل شيء سليماً: فعّل مفتاح **ON** (Scheduling: كل 4 ساعات).
