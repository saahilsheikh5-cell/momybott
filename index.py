import os
import telebot
import requests
import time
import threading
from flask import Flask, request

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "7638935379:AAEmLD7JHLZ36Ywh5tvmlP1F8xzrcNrym_Q")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://momybott-4.onrender.com/" + BOT_TOKEN)
CHAT_ID = int(os.getenv("CHAT_ID", "1263295916"))

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)

# === TELEGRAM HANDLERS ===
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "🤖 Bot is running on Render!")

# Example background task
def background_worker():
    while True:
        try:
            bot.send_message(CHAT_ID, "✅ Bot is alive and running!")
        except Exception as e:
            print("Error sending message:", e)
        time.sleep(60)  # every 1 minute

# === FLASK ROUTES ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot is running!", 200

# === STARTUP ===
if __name__ == "__main__":
    # Start background worker thread
    threading.Thread(target=background_worker, daemon=True).start()
    # Start Flask app
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
