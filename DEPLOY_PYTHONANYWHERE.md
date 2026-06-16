# نشر مشروع APS على PythonAnywhere (مجاني — لينك ثابت للعميل)

دليل خطوة-بخطوة. اللينك النهائي هيبقى شكله: `https://USERNAME.pythonanywhere.com`
وهو **ثابت** (مابيـ expire زي ngrok) والقرص **دائم** فالصور المرفوعة بتفضل محفوظة.

> استبدل `USERNAME` باسم حسابك على PythonAnywhere في كل الخطوات.
> الريبو على GitHub: `https://github.com/mohamed21othman2003-lang/APS_NOB.git`

---

## 0) قبل ما تبدأ: تأكد إن آخر كود مرفوع على GitHub
لازم تعديلاتك الأخيرة (إصلاح الفوتر + القائمة الجانبية + إعدادات النشر) تكون مدفوعة (push) للـ GitHub، عشان السيرفر يسحبها. لو مش متأكد، قول لي وأنا أجهّز لك الـ commit.

---

## 1) اعمل حساب مجاني
- ادخل https://www.pythonanywhere.com → **Pricing & signup** → **Create a Beginner account** (مجاني).
- فعّل الإيميل وسجّل دخول.

## 2) افتح Bash console
من الـ Dashboard → تبويب **Consoles** → اضغط **Bash**. هيفتح لك سطر أوامر على السيرفر.

## 3) اسحب الكود من GitHub
في الـ Bash console اكتب:
```bash
git clone https://github.com/mohamed21othman2003-lang/APS_NOB.git
cd APS_NOB
ls            # لازم تشوف manage.py هنا
```
> لو الريبو **private**، هيطلب منك يوزر/توكن GitHub. أبسط حل مؤقت: خلّي الريبو public وقت النشر، أو قول لي أساعدك في التوكن.
> لو ظهر إن `manage.py` في مجلد جوّاني، ادخله بـ `cd` لحد ما تلاقي `manage.py`.

## 4) اعمل بيئة بايثون وثبّت المتطلبات (الخفيفة)
```bash
mkvirtualenv --python=/usr/bin/python3.11 aps
pip install -r requirements-deploy.txt
```
> لو `python3.11` مش موجود، جرّب `/usr/bin/python3.10` أو `/usr/bin/python3.12`.
> ملف `requirements-deploy.txt` خفيف ومتقدر يثبّت في ثواني (Django + Pillow بس).

## 5) جهّز قاعدة البيانات والمحتوى
عندك طريقتين — **اختار واحدة**:

**الطريقة (أ) — الأسهل: ارفع نسخة قاعدة بياناتك الحالية** (فيها كل المحتوى + حساب الدخول بتاعك)
1. على جهازك، الملف اسمه `db.sqlite3` في جذر المشروع.
2. على PythonAnywhere: تبويب **Files** → ادخل مجلد `APS_NOB` (اللي فيه `manage.py`) → زر **Upload a file** → ارفع `db.sqlite3`.
3. خلاص — السيرفر دلوقتي عنده نفس المحتوى وحساب الدخول اللي بتستخدمه.

**الطريقة (ب) — قاعدة جديدة من الصفر**
في الـ Bash console (والبيئة `aps` مفعّلة):
```bash
python manage.py migrate --settings=aps_backend.settings_local
python manage.py seed     --settings=aps_backend.settings_local   # يعبّي المحتوى الأساسي
python manage.py createsuperuser --settings=aps_backend.settings_local   # ينشئ حساب دخول
```

## 6) أنشئ تطبيق الويب
- تبويب **Web** → **Add a new web app** → **Next**.
- اختار **Manual configuration** (مش Django) → اختار **Python 3.11** (نفس اللي عملت بيه البيئة) → **Next**.

## 7) اربط البيئة (virtualenv)
في صفحة الـ Web، قسم **Virtualenv**، اكتب:
```
/home/USERNAME/.virtualenvs/aps
```

## 8) عدّل ملف الـ WSGI
في صفحة الـ Web، قسم **Code** → اضغط على لينك ملف الـ WSGI (اسمه زي `/var/www/USERNAME_pythonanywhere_com_wsgi.py`).
**امسح كل محتواه** وحُط ده (وبدّل `USERNAME`):
```python
import sys, os

path = '/home/USERNAME/APS_NOB'        # المجلد اللي فيه manage.py
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'aps_backend.settings_local'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```
احفظ (Save).
> ملاحظة: بنستخدم `settings_local` عشان يشتغل بـ SQLite (الأبسط، والقرص دائم فبيفضل محفوظ).

## 9) اربط الملفات الثابتة والصور (مهم عشان الصور تظهر)
في صفحة الـ Web، قسم **Static files**، أضف **سطرين**:

| URL        | Directory                              |
|------------|----------------------------------------|
| `/static/` | `/home/USERNAME/APS_NOB/static`        |
| `/media/`  | `/home/USERNAME/APS_NOB/media`         |

> ربط `/static/` على مجلد `static` المصدر مباشرةً بيخلّي الصور اللي بترفعها من الـ CMS تظهر فورًا (لأنها بتتكتب هناك).

تأكد إن مجلد `media` موجود (في الـ Bash console):
```bash
mkdir -p /home/USERNAME/APS_NOB/media
```

## 10) شغّل وجرّب
- ارجع أعلى صفحة الـ Web واضغط الزر الأخضر **Reload**.
- افتح: `https://USERNAME.pythonanywhere.com` → الموقع العام.
- افتح: `https://USERNAME.pythonanywhere.com/cms/` → لوحة التحكم (سجّل دخول بحسابك).
- جرّب ترفع صورة فوتر/لوجو وتحفظ → لازم تشتغل وتفضل محفوظة.

ابعت اللينك للعميل يتست عليه. 🎉

---

## لو ظهر خطأ
- صفحة الـ Web فيها لينك **Error log** — افتحه، صوّر آخر سطور الخطأ وابعتهالي.
- بعد أي تعديل على الكود/الإعدادات على السيرفر، لازم تضغط **Reload** تاني.

## تحديث الكود لاحقًا (لما أعمل أي إصلاح جديد)
في الـ Bash console:
```bash
cd ~/APS_NOB
git pull
workon aps
pip install -r requirements-deploy.txt   # لو فيه متطلبات جديدة
```
وبعدها اضغط **Reload** من تبويب Web.

## ملاحظات أمان (للتست بس)
- ده إعداد **تجريبي** (DEBUG شغّال) لتسهيل العرض للعميل. مناسب للتست المؤقت، مش للتشغيل النهائي.
- بعد ما العميل يخلص تست، يُفضّل توقف/تحذف الـ web app.
- فيه مفاتيح سرية (SECRET_KEY/كلمة سر قاعدة بيانات) داخل `settings.py` — متخليش الريبو public بشكل دائم، ولو هننشر نهائي لازم ننقلها لمتغيرات بيئة. أقدر أساعدك في ده وقت النشر النهائي.
