# استخدم صورة Python 3.11 رسمية
FROM python:3.11-slim

# تثبيت FFmpeg و curl
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مجلد التطبيق
WORKDIR /app

# نسخ ملفات المشروع
COPY . /app

# تثبيت مكتبات Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# أمر تشغيل البوت
CMD ["python", "ana.py"]
