import subprocess
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# -------------------------------------------
# إعدادات البوت
# -------------------------------------------
BOT_TOKEN = "8327550793:AAHaH5nAg5yQbMZwqtW00qg8PKW4A1RSwp0"

# ⚠️ تحذير: استخدام بروكسي مجاني أو بطيء هو السبب رقم 1 لتقطع البث.
# إذا كان البث يقطع، اجعل هذا المتغير فارغاً "" وجرب بدونه.
PROXY_URL = "" 

users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_chat.id] = {"step": "await_key"}
    await update.message.reply_text(
        "👋 أهلاً بك! نظام البث المستقر (Stable Stream).\n\n"
        "1️⃣ أرسل **Stream Key** الخاص بفيسبوك."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id not in users:
        await update.message.reply_text("أرسل /start للبدء.")
        return

    step = users[chat_id]["step"]

    # --- الخطوة 1: استلام المفتاح ---
    if step == "await_key":
        users[chat_id]["stream_key"] = text
        users[chat_id]["step"] = "await_url"
        await update.message.reply_text("✔️ تم حفظ المفتاح.\n2️⃣ الآن أرسل **رابط الفيديو** (M3U8 أو MP4).")
        return

    # --- الخطوة 2: استلام الرابط وبدء البث ---
    if step == "await_url":
        users[chat_id]["url"] = text
        await update.message.reply_text("🚀 جاري تهيئة السيرفر وبدء البث المستقر...")

        video_url = users[chat_id]["url"]
        stream_key = users[chat_id]["stream_key"]
        
        fb_rtmp = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"
        watermark_path = "watermark.png" 

        # -----------------------------
        # فلتر التمويه وتغيير البصمة (خفيف على المعالج)
        # -----------------------------
        # قللت القيم قليلاً لتسريع المعالجة مع الحفاظ على التغيير
        complex_filter = (
            "[0:v]eq=contrast=1.04:saturation=1.05,unsharp=3:3:0.5[v_mod];" 
            "[1:v]scale=80:-1[wm];" 
            "[v_mod][wm]overlay=15:H-h-15"
        )

        ffmpeg_cmd = [
            "ffmpeg",
            # --- أوامر الثبات وإعادة الاتصال (مهمة جداً) ---
            "-reconnect", "1",
            "-reconnect_at_eof", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-timeout", "10000000", # زيادة وقت الانتظار قبل الفشل
            "-y",
            
            "-re", # اقرأ المدخلات بالسرعة الطبيعية (حاول إزالتها إذا كان المصدر بطيئاً جداً)
            "-i", video_url,
            "-i", watermark_path,
            
            "-filter_complex", complex_filter,
            
            "-c:v", "libx264",
            "-preset", "ultrafast",  # ⚡ الأسرع والأكثر استقراراً (يمنع التقطيع)
            "-tune", "zerolatency",  # لتقليل التأخير
            
            # --- التحكم في تدفق البيانات (Bitrate Control) ---
            "-b:v", "2000k",       # متوسط البت
            "-maxrate", "2500k",   # الحد الأقصى (يمنع القفزات التي تفصل البث)
            "-bufsize", "5000k",   # حجم المخزن المؤقت
            "-pix_fmt", "yuv420p",
            "-g", "60",            # فرض كي فريم كل ثانيتين (شرط فيسبوك)
            
            "-c:a", "aac",
            "-ar", "44100",
            "-b:a", "128k",
            "-af", "volume=0.9,treble=g=1", # تعديل صوت خفيف
            
            "-f", "flv",
            fb_rtmp
        ]

        # إعداد البروكسي (استخدمه بحذر)
        my_env = os.environ.copy()
        if PROXY_URL:
            my_env["http_proxy"] = PROXY_URL
            my_env["https_proxy"] = PROXY_URL

        try:
            # تشغيل العملية
            process = subprocess.Popen(
                ffmpeg_cmd, 
                env=my_env, 
                stdout=subprocess.DEVNULL, # إخفاء المخرجات لتخفيف الضغط
                stderr=subprocess.DEVNULL
            )
            
            users[chat_id]["process"] = process
            users[chat_id]["step"] = "streaming"
            
            await update.message.reply_text(
                "🎥 **البث يعمل الآن باستقرار!**\n"
                "✅ تم تفعيل `Reconnect` لعدم انقطاع المصدر.\n"
                "✅ تم تفعيل `Ultrafast` لعدم إجهاد المعالج.\n"
                "استخدم /stop للإيقاف."
            )
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in users and "process" in users[chat_id]:
        users[chat_id]["process"].kill() # إنهاء إجباري
        users[chat_id]["process"].wait() # انتظار التأكيد
        del users[chat_id]["process"]
        users[chat_id]["step"] = "await_key"
        await update.message.reply_text("⛔ تم إيقاف البث.")
    else:
        await update.message.reply_text("لا يوجد بث حالياً.")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    print("🔹 Stable Bot started...")
    app.run_polling()
