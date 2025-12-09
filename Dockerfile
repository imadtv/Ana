FROM python:3.10-slim

# Install FFmpeg
RUN apt update && apt install -y ffmpeg

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ⬇️ Download watermark locally (يتم تخزين الصورة داخل الدوكر)
RUN apt install -y wget && \
    wget -O /app/watermark.png "https://i.top4top.io/p_3630zi02e1.jpg"

# Copy bot code
COPY . .

CMD ["python", "ana.py"]
