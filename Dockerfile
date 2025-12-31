# Dockerfile
FROM python:3.11-slim

# تنظیم محل کار داخل کانتینر
WORKDIR /app

# جلوگیری از cache قدیمی
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# نصب وابستگی‌ها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کل پروژه داخل کانتینر
COPY . .

# دستور پیش‌فرض (داخل docker-compose override می‌کنیم)
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]
