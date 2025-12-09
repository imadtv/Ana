import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
)

BOT_TOKEN = "8327550793:AAHaH5nAg5yQbMZwqtW00qg8PKW4A1RSwp0"

users = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users[update.effective_chat.id] = {"step": "await_key"}
    await update.message.reply_text("👋 أرسل لي Stream Key للبث في فيسبوك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if chat_id not in users:
        await update.message.reply_text("أرسل /start للبدء.")
        return

    step = users[chat_id]["step"]

    if step == "await_key":
        users[chat_id]["stream_key"] = text
        users[chat_id]["step"] = "await_url"
        await update.message.reply_text("✔️ تم حفظ Stream Key.\nالآن أرسل رابط M3U8 أو MP4.")
        return

    if step == "await_url":
        users[chat_id]["url"] = text
        await update.message.reply_text("⏳ جاري بدء البث...")

        stream_key = users[chat_id]["stream_key"]
        video_url = users[chat_id]["url"]

        fb_rtmp = f"rtmps://live-api-s.facebook.com:443/rtmp/{stream_key}"

        ffmpeg_cmd = [
            "ffmpeg",
            "-i", video_url,
            "-filter_complex",
            "movie=https://i.top4top.io/p_3630zi02e1.jpg[wm];[0:v][wm]overlay=10:main_h-overlay_h-10",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-b:a", "96k",
            "-af", "volume=0.8",
            "-c:a", "aac",
            "-f", "flv",
            fb_rtmp
        ]

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        users[chat_id]["process"] = process
        users[chat_id]["step"] = "streaming"

        await update.message.reply_text("🎥 تم بدء البث بنجاح!")
        return

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in users and "process" in users[chat_id]:
        users[chat_id]["process"].kill()
        users[chat_id]["step"] = "await_key"
        await update.message.reply_text("⛔ تم إيقاف البث.")
    else:
        await update.message.reply_text("لا يوجد بث شغال.")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(MessageHandler(filters.TEXT, handle_message))

app.run_polling()
