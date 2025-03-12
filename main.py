import os
import config # Import file config.py
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yt_dlp import YoutubeDL
from pydub import AudioSegment


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💽 Chào mừng đến với Nhat_Music Bot! 🎵\n"
        "📥 Gửi cho tôi liên kết YouTube để tải xuống và phát nhạc!\n"
        "Commands:\n"
        "/start - Bắt đầu bot\n"
        "/help - Hiển thị trợ giúp"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📥 Gửi cho tôi URL YouTube và tôi sẽ chuyển đổi nó thành âm thanh!\n"
        "🔧 Tính năng:\n"
        "- Tải xuống video YouTube dưới dạng MP3\n"
        "- Gửi các tập tin âm thanh lên đến 50MB\n"
        "- nghe nhạc mức độ cơ bản"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text

    if "youtube.com" in message_text or "youtu.be" in message_text:
        await update.message.reply_text("Đang xử lý liên kết của bạn... 🎧")
        
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': 'downloads/%(title)s.%(ext)s',
            }
            
            if not os.path.exists('downloads'):
                os.makedirs('downloads')
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(message_text, download=True)
                filename = f"downloads/{info['title']}.mp3"

                file_size = os.path.getsize(filename) / (1024 * 1024)  # Size in MB
                
                if file_size > 50:
                    audio = AudioSegment.from_mp3(filename)
                    trimmed_audio = audio[:300000]
                    trimmed_filename = f"downloads/trimmed_{info['title']}.mp3"
                    trimmed_audio.export(trimmed_filename, format="mp3")
                    filename = trimmed_filename
                
                with open(filename, 'rb') as audio:
                    await update.message.reply_audio(
                        audio=audio,
                        title=info['title'],
                        performer=info.get('uploader', 'Unknown')
                    )
                
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                except Exception as e:
                    print(f"Cleanup error: {e}")
                
        except Exception as e:
            await update.message.reply_text(f"Error: {str(e)}")
    else:
        await update.message.reply_text("❌ Vui lòng gửi liên kết YouTube hợp lệ!")

async def download_and_send_audio(update: Update, url: str):
    await update.message.reply_text("🎵 Đang tải bài hát, vui lòng chờ...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')

        file_size = os.path.getsize(filename) / (1024 * 1024)  # MB

        if file_size > 50:
            await update.message.reply_text("⚠️ File quá lớn! Đang cắt gọn...")
            
            audio = AudioSegment.from_mp3(filename)
            trimmed_audio = audio[:300000] 
            trimmed_filename = f"downloads/trimmed_{info['title']}.mp3"
            trimmed_audio.export(trimmed_filename, format="mp3")
            filename = trimmed_filename

        with open(filename, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio,
                title=info['title'],
                performer=info.get('uploader', 'Unknown')
            )

        os.remove(filename)

    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi khi tải nhạc: {str(e)}")

async def queue_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "queue" not in context.user_data:
        context.user_data["queue"] = []
    
    message_text = " ".join(context.args)

    if not message_text:
        queue = context.user_data["queue"]
        if not queue:
            await update.message.reply_text("📭 Danh sách phát trống!")
        else:
            queue_text = "\n".join([f"{i+1}. {song}" for i, song in enumerate(queue)])
            await update.message.reply_text(f"📜 Danh sách phát:\n{queue_text}")
        return

    await update.message.reply_text(f"⏳ Đang tìm kiếm: {message_text} trên YouTube...")

    ydl_opts = {"format": "bestaudio/best", "quiet": True, "default_search": "ytsearch1"}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(message_text, download=False)
        url = info['entries'][0]['url'] if 'entries' in info else info['url']
        title = info['entries'][0]['title'] if 'entries' in info else info['title']

    context.user_data["queue"].append((title, url))
    await update.message.reply_text(f"✅ Đã thêm vào danh sách phát: [{title}]({url})", parse_mode="Markdown")

    if len(context.user_data["queue"]) == 1:
        await play_next_song(update, context)

async def play_next_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    queue = context.user_data.get("queue", [])
    
    if not queue:
        await update.message.reply_text("🎵 Hết danh sách phát!")
        return
    
    title, url = queue.pop(0)  

    await update.message.reply_text(f"🎧 Đang phát: [{title}]({url})", parse_mode="Markdown")

    await download_and_send_audio(update, url)

    if queue:
        await play_next_song(update, context)

async def cleanup(filename):
    try:
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print(f"Cleanup error: {e}")

async def get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        url = context.args[0]
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get('duration', 0)
            await update.message.reply_text(f"Duration: {duration//60} min {duration%60} sec")

def main():
    # Create the Application
    application = Application.builder().token(config.TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("duration", get_duration))
    application.add_handler(CommandHandler("queue", queue_song))
    
    # Start the bot
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()