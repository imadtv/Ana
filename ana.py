import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8327550793:AAHaH5nAg5yQbMZwqtW00qg8PKW4A1RSwp0"

# لتخزين بيانات المستخدمين
users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_chat.id] = {"step": "await_key"}
    await update.message.reply_text("👋 أرسل لي Stream Key للبث في فيسبوك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    if chat_id not in users:
        await update.message.reply_text("أرسل /start للبدء.")
        return

    step = users[chat_id]["step"]

    # استقبال Stream Key
    if step == "await_key":
        users[chat_id]["stream_key"] = text
        users[chat_id]["step"] = "await_url"
        await update.message.reply_text("✔️ تم حفظ Stream Key.\nالآن أرسل رابط M3U8 أو MP4.")
        return

    # استقبال URL الفيديو
    if step == "await_url":
        users[chat_id]["url"] = text
        await update.message.reply_text("⏳ جاري بدء البث على فيسبوك...")

        stream_key = users[chat_id]["stream_key"]
        video_url = users[chat_id]["url"]

        fb_rtmp = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"

        # FFmpeg مع صورة ووتارمارك محفوظة محلياً في Docker
        ffmpeg_cmd = [
            "ffmpeg",
            "-re",
            "-i", video_url,
            "-filter_complex",
            "movie=/app/watermark.png[wm];[0:v][wm]overlay=10:main_h-overlay_h-10",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:a", "96k",
            "-af", "volume=0.8",
            "-c:a", "aac",
            "-f", "flv",
            fb_rtmp
        ]

        try:
            process = subprocess.Popen(ffmpeg_cmd)
            users[chat_id]["process"] = process
            users[chat_id]["step"] = "streaming"
            await update.message.reply_text("🎥 تم بدء البث بنجاح!")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء بدء البث:\n{e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in users and "process" in users[chat_id]:
        users[chat_id]["process"].kill()
        users[chat_id]["step"] = "await_key"
        await update.message.reply_text("⛔ تم إيقاف البث.")
    else:
        await update.message.reply_text("لا يوجد بث شغال حالياً.")

# إنشاء البوت وتشغيله
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    print("🔹 البوت بدأ العمل...")
    app.run_polling()
