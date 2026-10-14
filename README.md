# المنظومة

نظام إدارة عملاء بواجهة عربية (RTL) مبني بـ Flask وSQLite.

## المزايا
- تسجيل الدخول وصلاحيات (مدير / موظف) وحماية CSRF
- لوحة تحكم، وإدارة العملاء مع البحث
- إدارة المستخدمين (للمدير فقط)

## التشغيل محليًا
```bash
pip install -r requirements.txt
ADMIN_PASSWORD='كلمة-قوية' SECRET_KEY='مفتاح-عشوائي' flask --app wsgi run
```
يُنشأ المستخدم `admin` عند أول تشغيل إذا حُدد `ADMIN_PASSWORD`.

## الاختبارات
```bash
pytest
```

## النشر (Docker + Nginx)
```bash
cp .env.example .env   # عدّل القيم
docker compose up -d --build
```
