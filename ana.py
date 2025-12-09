import subprocess
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# -------------------------------------------
# 1. إعدادات البوت والبروكسي
# -------------------------------------------
BOT_TOKEN = "8327550793:AAHaH5nAg5yQbMZwqtW00qg8PKW4A1RSwp0"

# إذا كان لديك بروكسي، ضعه هنا لإخفاء الـ IP الخاص بك
# مثال: "http://user:pass@123.45.67.89:8080"
# إذا لم يكن لديك، اتركه فارغاً "" ولكن سيظهر الـ IP الخاص بجهازك
PROXY_URL = "" 

users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_chat.id] = {"step": "await_key"}
    await update.message.reply_text(
        "👋 أهلاً بك!\n"
        "أرسل لي **Stream Key** الخاص بفيسبوك للبدء."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id not in users:
        await update.message.reply_text("أرسل /start للبدء.")
        return

    step = users[chat_id]["step"]

    # --- استلام المفتاح ---
    if step == "await_key":
        users[chat_id]["stream_key"] = text
        users[chat_id]["step"] = "await_url"
        await update.message.reply_text("✔️ تم حفظ المفتاح.\nالآن أرسل **رابط الفيديو** (M3U8 أو MP4).")
        return

    # --- استلام الرابط وبدء البث ---
    if step == "await_url":
        users[chat_id]["url"] = text
        await update.message.reply_text("⏳ جاري تجهيز الفلاتر وبدء البث...")

        video_url = users[chat_id]["url"]
        stream_key = users[chat_id]["stream_key"]
        
        # رابط السيرفر الخاص بفيسبوك
        fb_rtmp = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"

        # مسار اللوجو (تأكد أن الصورة موجودة في نفس المسار أو عدله)
        # إذا كنت تشغل الكود محلياً، ضع المسار الكامل مثل: "C:/images/watermark.png"
        watermark_path = "watermark.png" 

        # -----------------------------
        # 2. فلاتر التغيير (لتجاوز التطابق)
        # -----------------------------
        # [0:v] الفيديو الأصلي
        # eq: نزيد التباين (contrast) والتشبع (saturation) قليلاً
        # unsharp: نزيد حدة الصورة قليلاً
        # scale: نغير حجم اللوجو
        # overlay: ندمج اللوجو
        
        video_filters = (
            "eq=contrast=1.05:brightness=0.03:saturation=1.1,"  # تغيير الألوان والإضاءة
            "unsharp=3:3:1.0,"                                  # تغيير حدة الصورة (Sharpen)
            "[0:v]overlay=15:H-h-15"                            # دمج اللوجو (إذا كان موجوداً، انظر الملاحظة بالأسفل)
        )
        
        # ملاحظة: إذا أردت دمج اللوجو، نحتاج لتعقيد الفلتر قليلاً لدمج مدخلين.
        # الكود أدناه معدل ليدمج اللوجو مع تغيير الصورة.
        
        complex_filter = (
            "[0:v]eq=contrast=1.05:brightness=0.03:saturation=1.1,unsharp=3:3:1.0[v_mod];" # تعديل الفيديو وتسميته v_mod
            "[1:v]scale=80:-1[wm];"                                                         # تعديل حجم اللوجو وتسميته wm
            "[v_mod][wm]overlay=15:H-h-15"                                                  # دمج الاثنين
        )

        # أوامر الصوت: تغيير بسيط في الـ Treble وتقليل الصوت
        audio_filter = "volume=0.9,treble=g=2"

        ffmpeg_cmd = [
            "ffmpeg",
            "-re",
            "-i", video_url,
            "-i", watermark_path,  # تأكد من وجود صورة باسم watermark.png بجانب السكربت
            "-filter_complex", complex_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-maxrate", "2500k",   # تحديد سقف للبيتريت لاستقرار البث
            "-bufsize", "5000k",
            "-g", "60",            # مهم جداً لفيسبوك (Keyframe interval)
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-af", audio_filter,   # تطبيق فلتر الصوت
            "-f", "flv",
            fb_rtmp
        ]

        # -----------------------------
        # 3. إعداد البروكسي (إخفاء IP)
        # -----------------------------
        # نقوم بنسخ بيئة النظام الحالية ونضيف عليها إعدادات البروكسي
        my_env = os.environ.copy()
        if PROXY_URL:
            my_env["http_proxy"] = PROXY_URL
            my_env["https_proxy"] = PROXY_URL
            my_env["ALL_PROXY"] = PROXY_URL # لمحاولة إجبار FFmpeg على استخدامه

        try:
            # نمرر env=my_env لكي يستخدم FFmpeg البروكسي
            process = subprocess.Popen(ffmpeg_cmd, env=my_env)
            
            users[chat_id]["process"] = process
            users[chat_id]["step"] = "streaming"
            await update.message.reply_text(
                "🎥 **تم بدء البث!**\n"
                "✅ تم تطبيق فلاتر تغيير الصورة والصوت.\n"
                f"🛡️ حالة إخفاء IP: {'مفعل (عبر البروكسي)' if PROXY_URL else 'غير مفعل (IP السيرفر مكشوف)'}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ أثناء تشغيل البث: {e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in users and "process" in users[chat_id]:
        # إنهاء العملية
        users[chat_id]["process"].kill()
        users[chat_id]["step"] = "await_key"
        # حذف العملية من الذاكرة
        del users[chat_id]["process"]
        await update.message.reply_text("⛔ تم إيقاف البث بنجاح.")
    else:
        await update.message.reply_text("لا يوجد بث يعمل حالياً لإيقافه.")

# بناء التطبيق
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    print("🔹 Bot started with enhanced filters...")
    app.run_polling()
